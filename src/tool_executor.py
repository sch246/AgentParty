# =====================================================================
# 工具执行器
#
# 设计理念：
# 1. do python/sh 块：AI 可以调用本地工具
# 2. 输出追加 log：结果通过 @file 回引到上下文
# 3. 沙盒命名空间：注入 messages/readfile，可通过 extra_ns 扩展
#
# parse_do_blocks: 从 AI 原始回复提取 do python / do sh 块
# execute_blocks:  沙盒执行 → 输出追加 log → 返回行号范围
# =====================================================================
import io
import re
import os
import subprocess
import sys
from pathlib import Path


def parse_do_blocks(text: str):
    """提取 do py / do sh 块 → [(type, code, params)]。code 已 strip 一层缩进。

    支持：do py, do python（向后兼容）, do sh
    语法：do <type> [key=value ...]
    例如：do py timeout=60 cwd=/tmp
    """
    blocks = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        # 匹配：do <type> [参数...]
        m = re.match(r"^do\s+(py|python|sh)(?:\s+(.+))?\s*$", lines[i])
        if m:
            block_type = m.group(1)
            # 规范化：python → py
            if block_type == "python":
                block_type = "py"

            # 解析参数
            params = {}
            if m.group(2):
                params = _parse_params(m.group(2))

            # 收集代码
            code_lines = []
            i += 1
            while i < len(lines):
                if re.match(r"^end\s*$", lines[i]):
                    break
                code_lines.append(_strip_one_indent(lines[i]))
                i += 1

            blocks.append((block_type, "\n".join(code_lines), params))
        i += 1
    return blocks


def has_do_block(text: str) -> bool:
    """检测文本是否包含 do 块（支持参数）"""
    return bool(re.search(r"^do\s+(py|python|sh)(?:\s+\S+)*\s*$", text, re.MULTILINE))


def execute_blocks(blocks, messages, log_path, extra_ns=None):
    """串行执行 do 块，输出追加 log_path。
    返回 [(type, start_line, end_line)]。
    blocks: [(type, code, params)] 的列表
    extra_ns 合并进沙盒命名空间（可覆盖 message/readfile 或追加新函数）。
    """
    results = []
    with open(log_path, "a", encoding="utf-8") as log:
        for item in blocks:
            # 向后兼容：支持旧格式 (type, code) 和新格式 (type, code, params)
            if len(item) == 2:
                block_type, code = item
                params = {}
            else:
                block_type, code, params = item

            before = _count_lines(log_path)
            log.write(f"\n--- do {block_type}")
            if params:
                log.write(f" {_format_params(params)}")
            log.write(" ---\n")
            log.flush()

            output = _run(block_type, code, messages, extra_ns, params)
            log.write(output)
            if not output.endswith("\n"):
                log.write("\n")
            log.flush()

            after = _count_lines(log_path)
            results.append((block_type, before + 1, after))
    return results


# ---------------------------------------------------------------------------
def _run(block_type, code, messages, extra_ns, params):
    ns = _build_namespace(messages, extra_ns)
    if block_type == "sh":
        return _run_sh(code, params)
    # block_type 已经规范化为 "py"
    return _run_python(code, ns, params)


def _build_namespace(messages, extra_ns):
    """构建沙盒命名空间。extra_ns 可覆盖/追加。"""
    ns = {
        "messages": messages,
        "readfile": _read_fn(),
    }
    if extra_ns:
        ns.update(extra_ns)
    return ns


# ---- sh ----------------------------------------------------------------
def _run_sh(code, params):
    """执行 shell 命令，支持 timeout 和 cwd 参数"""
    timeout = params.get('timeout')
    cwd = params.get('cwd')

    try:
        r = subprocess.run(
            code,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd
        )
        out = r.stdout
        if r.stderr:
            out += r.stderr
        return out
    except subprocess.TimeoutExpired:
        return f"[do sh 超时: {timeout}秒]\n"
    except Exception as exc:
        return f"[do sh 异常: {exc}]"


# ---- python ------------------------------------------------------------
def _run_python(code, ns, params):
    """执行 Python 代码，支持 timeout 参数"""
    timeout = params.get('timeout')

    if timeout is None:
        # 无 timeout，直接执行
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            exec(code, ns)
            return buf.getvalue()
        except Exception as exc:
            return f"[do py 异常: {exc}]\n{buf.getvalue()}"
        finally:
            sys.stdout = old

    # 有 timeout，使用线程 + 超时控制
    import threading
    result = {'output': '', 'error': None}

    def target():
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            exec(code, ns)
            result['output'] = buf.getvalue()
        except Exception as exc:
            result['error'] = exc
            result['output'] = buf.getvalue()
        finally:
            sys.stdout = old

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        return f"[do py 超时: {timeout}秒]\n{result['output']}"

    if result['error']:
        return f"[do py 异常: {result['error']}]\n{result['output']}"

    return result['output']


def _read_fn():
    def read(path):
        try:
            if os.path.isfile(path):
                return Path(path).read_text(encoding="utf-8")
            elif os.path.isdir(path):
                return _plist_dir(path)
        except Exception as exc:
            return f"[read({path}) 失败: {exc}]"

    return read


# ---- util --------------------------------------------------------------
def _parse_params(param_str: str) -> dict:
    """解析参数字符串 'timeout=60 cwd=/tmp' → {'timeout': 60, 'cwd': '/tmp'}"""
    params = {}
    for pair in param_str.split():
        if '=' in pair:
            key, value = pair.split('=', 1)
            # 类型转换
            params[key] = _convert_param_value(key, value)
    return params


def _convert_param_value(key: str, value: str):
    """根据 key 转换参数类型"""
    if key == 'timeout':
        try:
            return int(value)
        except ValueError:
            return value  # 保持字符串，让运行时报错
    # 其他参数保持字符串
    return value


def _format_params(params: dict) -> str:
    """格式化参数用于日志显示 {'timeout': 60} → 'timeout=60'"""
    return ' '.join(f"{k}={v}" for k, v in params.items())


def _strip_one_indent(line):
    if line.startswith("    "):
        return line[4:]
    if line.startswith("\t"):
        return line[1:]
    return line


def _count_lines(path):
    try:
        with open(path, encoding="utf-8") as f:
            return sum(1 for _ in f)
    except FileNotFoundError:
        return 0

def _plist_dir(path):
    return '\n'.join(f'> {d}' if os.path.isdir(os.path.join(path, d)) else d
                     for d in os.listdir(path))
