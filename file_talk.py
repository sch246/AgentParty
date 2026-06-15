# =====================================================================
# file 模式：用"读写 md 文件"的方式和 AI 聊天。
#
# 核心约定：
#   1. 文件开头是 YAML frontmatter（两道 --- 夹起来），提供
#      base_url / api_key / model / name。无 frontmatter 静默跳过。
#   2. 正文用 `<role>: ` 分割角色（system / user / 显示名）。
#   3. 第一个 `<role>: ` 之前的内容被丢弃。
#   4. 检测到文件以双换行 `\n\n` 结尾时触发一次聊天。
#   5. 思考仅打印到控制台/日志（不写入文件）；正文仅追加到文件。
# =====================================================================
import os

from openai import OpenAI

from config import resolve_config
from core import request_llm, stream_events, terminal_color_print
from chat_formatter import ChatFormatter
from pipeline import apply_ux_rules, execute_semantic_actions


def display_name(meta):
    """取显示名：frontmatter 有 name 就用 name，否则回退到 model。"""
    return meta.get("name") or meta["model"]


def consume_to_file(raw_events, path, name, model, enable_log=False):
    """File 版消费者：正文写文件，非正文按需打控制台或写日志。

    name / model 来自配置（不是 API 返回名），确保显示名与调用名解耦。
    """
    log_path = os.path.splitext(path)[0] + ".log"

    def output_meta(text="", color="white", end="\n"):
        """互斥输出：enable_log → 写日志文件，否则 → 打控制台。"""
        if enable_log:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(text + end)
        else:
            terminal_color_print(text, color, end=end)

    def append_md(text):
        with open(path, "a", encoding="utf-8") as f:
            f.write(text)

    handlers = {
        "header": lambda _: (
            output_meta(ChatFormatter.format_role_header_console(name, model), "cyan"),
            append_md(ChatFormatter.format_role_header_file(name)),
        ),
        "ui_newline": lambda _: output_meta(),
        "thinking": lambda text: output_meta(text, "yellow", end=""),
        "content": lambda text: append_md(text),
        "usage": lambda u: (
            output_meta(
                f"输入: {u['prompt']}, 输出: {u['completion']}, 总: {u['total']}",
                "gray",
            ),
            output_meta(
                f"思考: {u['reasoning']}, 缓存命中: {u['cache_hit']},"
                f" 缓存未命中: {u['cache_miss']}",
                "gray",
            ),
        ),
        "error": lambda e: output_meta(str(e), "red"),
    }

    ux_stream = apply_ux_rules(raw_events)
    execute_semantic_actions(ux_stream, handlers)

    # 对话结束，写入下一轮输入锚点
    append_md(ChatFormatter.format_next_user_prompt())


def handler(path):
    """处理一次文件触发：读→解析→调 LLM→消费→写锚点。"""
    with open(path, encoding="utf-8") as f:
        text = f.read()

    if not text.endswith("\n\n"):
        return

    meta, messages = ChatFormatter.parse_file(text)
    if meta is None:
        return

    config = resolve_config(meta)

    if not messages:
        return

    client = OpenAI(api_key=config["api_key"], base_url=config["base_url"])
    response = request_llm(client, config["model"], messages)
    consume_to_file(
        stream_events(response),
        path,
        display_name(config),
        config["model"],
        enable_log=config["log"],
    )


def file_talk():
    from watch_file import NonBlockingWatcher

    config = resolve_config()
    watch_path = config.get("watch_path", ".")

    watcher = NonBlockingWatcher()
    watcher.set_handler(handler)
    watcher.loop(watch_path)


if __name__ == "__main__":
    file_talk()
