# =====================================================================
# cli 模式：在终端里和 AI 聊天。
#
# 直接消费 stream_events → 全部上色打到控制台。
# 配置走 resolve_config()：.config.json → 手输补缺。
# =====================================================================
from openai import OpenAI

from config import resolve_config
from core import request_llm, stream_events, terminal_color_print, meta_output


def consume_to_terminal(response, user_model):
    """CLI 版消费者：直接循环 stream_events，内联状态机

    为什么废弃 pipeline.py：
    - apply_ux_rules 的状态机逻辑很简单（只是插入空行）
    - 内联后代码更直接，易于理解和维护
    - 与 File 模式架构统一（都直接消费 stream_events）

    状态机逻辑：
    - idle → thinking: 打印空行
    - thinking → speaking: 打印空行
    - 其他切换：打印空行

    返回：完整正文字符串（供 CLI 维护 messages 历史）
    """
    full_content = ""
    state = "idle"  # idle | thinking | speaking

    for kind, payload in stream_events(response):
        if kind == "role":
            meta_output(f"{user_model}: ", "cyan", end="")

        elif kind == "thinking":
            if state != "thinking":
                print()  # ui_newline：状态切换时插入空行
                state = "thinking"
            meta_output(payload, "yellow", end="")

        elif kind == "content":
            if state == "thinking":
                print()  # ui_newline
                state = "speaking"
            full_content += payload
            terminal_color_print(payload, "green", end="")

        elif kind == "usage":
            if state == "thinking":
                print()  # ui_newline
            meta_output(
                f"输入: {payload['prompt']}, 输出: {payload['completion']}, "
                f"总: {payload['total']}",
                "gray",
            )
            meta_output(
                f"思考: {payload['reasoning']}, 缓存命中: {payload['cache_hit']}, "
                f"缓存未命中: {payload['cache_miss']}",
                "gray",
            )

        elif kind == "error":
            print()  # ui_newline
            meta_output(str(payload), "red")

    return full_content


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
        response_text = consume_to_terminal(response, model)

        # 把 AI 的回复也存进抽屉，这样下一轮它能看到自己说过啥（有记忆）
        messages += [{"role": "assistant", "content": response_text}]


if __name__ == "__main__":
    cli_talk()
