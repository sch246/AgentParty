# =====================================================================
# cli 模式：在终端里和 AI 聊天。
#
# 消费 ux_reducer 的语义动作流 → 全部上色打到控制台。
# 配置走 resolve_config()：.config.json → 手输补缺。
# =====================================================================
from openai import OpenAI

from config import resolve_config
from core import request_llm, stream_events, terminal_color_print
from pipeline import apply_ux_rules, execute_semantic_actions


def consume_to_terminal(raw_events, user_model):
    """CLI 版消费者：所有语义动作都上色打到控制台。

    返回拼接后的完整正文（供 CLI 维护 messages 历史）。
    """
    handlers = {
        "header": lambda _: terminal_color_print(
            f"{user_model}: ", "cyan", end=""
        ),
        "ui_newline": lambda _: print(),
        "thinking": lambda text: terminal_color_print(text, "yellow", end=""),
        "content": lambda text: terminal_color_print(text, "green", end=""),
        "usage": lambda u: (
            terminal_color_print(
                f"输入: {u['prompt']}, 输出: {u['completion']}, 总: {u['total']}",
                "gray",
            ),
            terminal_color_print(
                f"思考: {u['reasoning']}, 缓存命中: {u['cache_hit']},"
                f" 缓存未命中: {u['cache_miss']}",
                "gray",
            ),
        ),
        "error": lambda e: terminal_color_print(str(e), "red"),
    }

    ux_stream = apply_ux_rules(raw_events)
    return execute_semantic_actions(ux_stream, handlers)


def cli_talk():
    # 0. 解析配置：CLI 不传 sources，优先级只有 .config.json → 手输补缺。
    config = resolve_config()
    client = OpenAI(api_key=config["api_key"], base_url=config["base_url"])
    model = config["model"]

    # 1. messages 是聊天历史大抽屉，开头先塞一句 system 人设。
    messages = [{"role": "system", "content": "你是一只猫娘"}]

    # 2. 死循环：一轮一轮地聊，不中断。
    while True:
        # 提醒轮到你说话了
        terminal_color_print("user: ", "cyan", end="")
        request_text = input()

        # 把你说的话扔进历史抽屉最后面
        messages += [{"role": "user", "content": request_text}]

        # 打包整个抽屉发给 AI，流式打印回复并记下完整正文
        response = request_llm(client, model, messages)
        response_text = consume_to_terminal(stream_events(response), model)

        # 把 AI 的回复也存进抽屉，这样下一轮它能看到自己说过啥（有记忆）
        messages += [{"role": "assistant", "content": response_text}]


if __name__ == "__main__":
    cli_talk()
