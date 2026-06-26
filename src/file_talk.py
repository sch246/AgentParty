# =====================================================================
# file 模式 v3 — 队列拉取式架构
#
# 设计理念：
# 1. 文件 = 终端：多个 AI 可以并行工作，每个占用一个文件
# 2. 所见即所得：编辑文件即改变上下文，无隐藏状态
# 3. 触发机制：双换行 = 人工/脚本都能触发，最大化兼容性和自动化
# 4. 引用系统（@file）：避免重复粘贴，保持配置和结果分离
# 5. 虚拟缓冲区：零预设检测用户修改（不关心改了什么，只比较是否一致）
#
# 架构：
# 每文件一个 FileHandler：队列 + 线程 + 虚拟缓冲区
# 触发 → 入队 → 拉取处理 → 工具回调入队（不递归）
# =====================================================================
import hashlib
import os
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from queue import Queue, Empty

from openai import OpenAI
import openai

from src.markdown_parser import parse_file
from src.config import resolve_config
from src.core import request_llm, stream_events, terminal_color_print
from src.tool_executor import execute_blocks, has_do_block, parse_do_blocks


class FileHandler:
    """单文件处理器：队列 + 虚拟缓冲区 + 可中断"""

    def __init__(self, path):
        self.path = path
        self.queue = Queue()
        self.running = False
        self.virtual = ""
        self._hash = None  # 大文件时用哈希比较（避免频繁的大字符串比较）
        self.lock = threading.Lock()  # watchdog 防抖锁
        self.tool_rounds = 0  # 工具调用计数器

    def trigger(self, source):
        """统一入口：user/tool"""
        if not self.lock.acquire(blocking=False):
            self._debug(f"触发被忽略（{source}）- 正在运行")
            return  # 正在运行，忽略触发

        self._debug(f"触发成功（{source}）- 入队")
        self.queue.put(source)

        if not self.running:
            threading.Thread(target=self._consume_loop, daemon=True).start()

    def _consume_loop(self):
        """拉取式主循环"""
        self.running = True
        try:
            while True:
                try:
                    source = self.queue.get(timeout=0.5)
                    self._process_once(source)
                except Empty:
                    break  # 队列空，自然退出
                except InterruptedError as e:
                    terminal_color_print(f"{self.path}: {e}", "red")
                    break
                # 可恢复错误：文件 IO 临时失败
                except (OSError, IOError) as e:
                    self._handle_recoverable_error(e, "文件读写失败")
                    break
                # 致命错误：立即停止
                except (
                    openai.AuthenticationError,  # API key 错误
                    ValueError,                   # 解析失败
                    KeyError,                     # 配置缺失
                    UnicodeDecodeError           # 编码问题（需人工修复）
                ) as e:
                    self._handle_fatal_error(e)
                    break
                # 未知错误：保守处理，视为致命
                except Exception as e:
                    self._handle_fatal_error(e, unknown=True)
                    break
        finally:
            self.running = False
            self.tool_rounds = 0  # 重置计数器
            self.lock.release()

    def _process_once(self, source):
        """单次处理：LLM → 工具 → 入队"""
        self._debug(f"开始处理（{source}）")

        # 1. 同步虚拟缓冲区（带重试，处理文件被锁定的情况）
        import time
        for attempt in range(3):
            try:
                self.virtual = Path(self.path).read_text(encoding="utf-8")
                break
            except (OSError, IOError, PermissionError) as e:
                if attempt < 2:
                    self._debug(f"文件读取失败（尝试 {attempt + 1}/3）: {e}")
                    time.sleep(0.1)  # 等待 100ms
                else:
                    self._handle_recoverable_error(e, "文件读写失败")
                    return  # 放弃本次处理

        # 2. 解析以获取配置
        meta, messages = parse_file(self.virtual)
        if not messages:
            self._debug("解析失败或无消息")
            return

        # 3. 实时读取配置
        config = resolve_config(meta)

        # 4. 立即消耗触发状态
        display_name = config.get("name") or config.get("model", "assistant")
        if source == "user":
            self._append(f"## {display_name}\n    ")
            self.tool_rounds = 0  # 用户触发时重置计数器
        elif source == "tool":
            self._append(f"\n## {display_name}\n    ")  # 工具触发需要角色标记
            self.tool_rounds += 1  # 工具触发时递增计数器

        client = OpenAI(
            api_key=config["api_key"], base_url=config["base_url"]
        )
        model = config["model"]
        enable_log = config.get("log", False)
        log_path = os.path.splitext(self.path)[0] + ".log"

        # 5. LLM 流式写入（带重试）
        self._debug(f"调用 LLM: {model}")
        raw = self._call_llm_with_retry(client, model, messages, log_path, enable_log, config)
        self._debug(f"LLM 返回 {len(raw)} 字符")

        # 6. 检查工具
        if not has_do_block(raw):
            self._debug("无 do 块，写锚点退出")
            self._append("\n\n## user\n    ")
            return  # 完成

        blocks = parse_do_blocks(raw)
        if not blocks:
            self._debug("do 块解析失败，写锚点退出")
            self._append("\n\n## user\n    ")
            return

        self._debug(f"检测到 {len(blocks)} 个 do 块")

        # 7. 执行工具 + 回引
        results = execute_blocks(blocks, messages, log_path)
        for _, start, end in results:
            self._append(f"\n@file {log_path}:{start}-{end}")
        self._debug(f"工具执行完成，回引 {len(results)} 个结果")

        # 8. 检查工具调用次数限制
        max_rounds = config.get("max_tool_rounds", 10)
        if self.tool_rounds >= max_rounds:
            self._debug(f"达到工具调用上限 ({max_rounds} 次)")
            terminal_color_print(
                f"{self.path}: 达到工具调用上限 ({max_rounds} 次)，停止执行",
                "yellow"
            )
            self._append("\n\n## user\n    ")
            return

        # 9. 重新入队（不递归！）
        self._debug("工具触发重新入队")
        self.queue.put("tool")

    def _stream_write(self, response, log_path, enable_log):
        """流式写入：thinking → log/控制台，content → 文件"""

        def meta_out(text, color, end="\n"):
            if enable_log:
                with open(log_path, "a", encoding="utf-8") as lf:
                    lf.write(text + end)
            else:
                terminal_color_print(text, color, end=end)

        raw = ""

        for kind, payload in stream_events(response):
            # 中断检测
            if self._user_modified():
                raise InterruptedError("用户修改了文件")

            if kind == "content" and isinstance(payload, str):
                raw += payload
                # 流式格式转换：处理内部换行
                formatted = payload.replace("\n", "\n    ")
                self._append(formatted)

            elif kind == "thinking" and isinstance(payload, str):
                meta_out(payload, "yellow", end="")

            elif kind == "usage" and isinstance(payload, dict):
                meta_out(
                    f"\n输入: {payload['prompt']}, 输出: {payload['completion']}, "
                    f"总: {payload['total']}",
                    "gray",
                )

            elif kind == "role" and isinstance(payload, str):
                meta_out(f"{payload}: ", "cyan", end="")

        return raw

    def _append(self, text):
        """写文件 + 同步虚拟缓冲区和哈希"""
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(text)
        self.virtual += text
        self._hash = None  # 内容变化时清空哈希缓存

    def _user_modified(self):
        """零预设中断检测：实际 ≠ 预期

        大文件（>100KB）时用哈希比较，避免频繁的大字符串比较
        """
        actual = Path(self.path).read_text(encoding="utf-8")

        # 大于 100KB 时用哈希
        if len(actual) > 100_000:
            actual_hash = hashlib.sha256(actual.encode()).hexdigest()
            if self._hash is None:
                self._hash = hashlib.sha256(self.virtual.encode()).hexdigest()
            return actual_hash != self._hash

        return actual != self.virtual

    def _debug(self, msg):
        """系统日志：追踪运行状态，便于 debug"""
        # 实时读取 debug 配置
        try:
            meta, _ = parse_file(self.virtual)
            config = resolve_config(meta)
            if config.get("debug", False):
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                print(f"[{timestamp}] {self.path}: {msg}")
        except:
            pass  # 解析失败时静默忽略（避免 debug 函数本身报错）

    def _call_llm_with_retry(self, client, model, messages, log_path, enable_log, config):
        """LLM 调用（带重试）：可恢复错误自动重试，致命错误直接抛出"""
        max_retries = config.get("max_retries", 3)
        retry_delay = config.get("retry_delay", 2.0)

        for attempt in range(max_retries):
            try:
                response = request_llm(client, model, messages)
                return self._stream_write(response, log_path, enable_log)

            # 可恢复错误：网络问题、限流
            except (openai.APIConnectionError, openai.RateLimitError) as e:
                if attempt < max_retries - 1:
                    # 指数退避：2秒 → 4秒 → 8秒
                    delay = retry_delay * (2 ** attempt)
                    self._debug(f"API 调用失败（{type(e).__name__}），{delay}秒后重试 ({attempt + 1}/{max_retries})")
                    self._write_retry_hint(attempt + 1, max_retries, str(e))
                    time.sleep(delay)
                else:
                    # 最后一次重试失败，抛出异常
                    self._debug(f"API 调用失败，已达最大重试次数")
                    raise

            # 致命错误：直接抛出，由 _consume_loop 处理
            # AuthenticationError / APIError / 其他异常都会在这里抛出

        # 理论上不会到这里（循环内已处理所有情况）
        raise RuntimeError("LLM 调用重试逻辑异常")

    def _write_retry_hint(self, attempt, max_attempts, error_msg):
        """写入重试提示到文件"""
        hint = f"\n[系统提示：API 调用失败 ({error_msg})，正在重试 {attempt}/{max_attempts}...]\n    "
        self._append(hint)

    def _handle_recoverable_error(self, error, error_type):
        """处理可恢复错误：记录日志 + 写入文件提示"""
        self._debug(f"可恢复错误 - {error_type}: {error}")
        terminal_color_print(f"{self.path}: {error_type} - {error}", "yellow")
        try:
            self._append(f"\n\n[系统错误：{error_type}，会话已暂停]\n## user\n    ")
        except:
            pass  # 如果连写文件都失败了，只能放弃

    def _handle_fatal_error(self, error, unknown=False):
        """处理致命错误：详细日志 + 写入文件 + 终端提示"""
        error_type = type(error).__name__
        if unknown:
            self._debug(f"未知错误（视为致命）- {error_type}: {error}")
            terminal_color_print(
                f"{self.path}: 未知错误 ({error_type}) - {error}",
                "red"
            )
        else:
            self._debug(f"致命错误 - {error_type}: {error}")
            terminal_color_print(f"{self.path}: 致命错误 ({error_type}) - {error}", "red")

        try:
            self._append(
                f"\n\n[系统错误：{error_type} - {error}\n"
                f"会话已停止，请检查配置或文件后重新触发]\n## user\n    "
            )
        except:
            pass  # 如果连写文件都失败了，只能放弃


# 全局管理器
handlers = {}


def handler(md_path):
    """watchdog 回调入口"""
    # 检查触发条件
    with open(md_path, encoding="utf-8") as f:
        if not f.read().endswith("\n\n"):
            return

    # 初始化或获取 handler（不再传 config）
    if md_path not in handlers:
        handlers[md_path] = FileHandler(md_path)

    # 触发处理
    handlers[md_path].trigger("user")


def file_talk():
    from src.watch_file import NonBlockingWatcher

    def shutdown(sig, frame):
        """优雅关闭：Ctrl+C 时停止所有任务"""
        print("\n正在停止所有任务...")
        for h in handlers.values():
            h.running = False  # 标记停止，_consume_loop 会自然退出
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    config = resolve_config()
    watch_path = config.get("watch_path", ".")

    watcher = NonBlockingWatcher()
    watcher.set_handler(handler)
    watcher.loop(watch_path)


if __name__ == "__main__":
    file_talk()
