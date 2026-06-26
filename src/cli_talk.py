# =====================================================================
# cli 模式：在终端里和 AI 聊天。
#
# 直接消费 stream_events → 全部上色打到控制台。
# 支持工具执行：检测 do 块 → 执行 → 打印结果到控制台。
# 配置走 resolve_config()：.config.json → 手输补缺。
# =====================================================================
import signal
import sys
from openai import OpenAI

from src.config import resolve_config
from src.core import request_llm, stream_events, terminal_color_print, meta_output
from src.tool_executor import has_do_block, parse_do_blocks, execute_blocks


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
                state = "idle"
            print()  # 额外空行，分隔 content 和 usage
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
    # 优雅退出处理
    def shutdown(sig, frame):
        """Ctrl+C 优雅退出"""
        print("\n\n再见喵~ (｡◕‿◕｡)")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # 1. messages 是聊天历史大抽屉，开头先塞一句 system 人设。
    messages = [{"role": "system", "content": "你是一只猫娘"}]

    # 2. 加载 tools.md 作为系统提示词（如果存在）
    try:
        from pathlib import Path
        tools_path = Path("tools.md")
        if tools_path.exists():
            tools_content = tools_path.read_text(encoding="utf-8")
            messages.append({"role": "system", "content": tools_content})
    except Exception:
        pass  # 文件不存在或读取失败，静默忽略

    # 3. 死循环：一轮一轮地聊，不中断。
    while True:
        # 每次循环读取配置（实时生效）
        config = resolve_config()
        client = OpenAI(api_key=config["api_key"], base_url=config["base_url"])
        model = config["model"]
        max_tool_rounds = config.get("max_tool_rounds", 10)
        # 提醒轮到你说话了
        terminal_color_print("user: ", "cyan", end="")
        request_text = input()

        # 把你说的话扔进历史抽屉最后面
        messages += [{"role": "user", "content": request_text}]

        # 工具调用循环
        tool_rounds = 0
        while tool_rounds <= max_tool_rounds:
            # 打包整个抽屉发给 AI，流式打印回复并记下完整正文
            response = request_llm(client, model, messages)
            response_text = consume_to_terminal(response, model)

            # 把 AI 的回复也存进抽屉
            messages += [{"role": "assistant", "content": response_text}]

            # 检查是否有工具调用
            if not has_do_block(response_text):
                break  # 没有工具，结束这轮对话

            # 解析并执行工具
            blocks = parse_do_blocks(response_text)
            if not blocks:
                break

            print()  # 空行分隔
            terminal_color_print(f"[执行 {len(blocks)} 个工具...]", "cyan")

            # 执行工具并打印结果到控制台
            tool_outputs = []
            for block_type, code, params in blocks:
                print()
                terminal_color_print(f"--- do {block_type} ---", "yellow")

                # 执行工具（使用临时 log 避免污染文件）
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False, encoding='utf-8') as tmp:
                    tmp_log = tmp.name

                results = execute_blocks([(block_type, code, params)], messages, tmp_log)

                # 读取并打印结果
                with open(tmp_log, 'r', encoding='utf-8') as f:
                    output = f.read()
                terminal_color_print(output, "white")

                # 收集输出供 AI 查看
                tool_outputs.append(f"[do {block_type} 输出]\n{output}")

                # 清理临时文件
                import os
                os.unlink(tmp_log)

            # 将工具输出作为 system 消息发送给 AI
            combined_output = "\n\n".join(tool_outputs)
            messages += [{"role": "system", "content": combined_output}]

            tool_rounds += 1
            if tool_rounds >= max_tool_rounds:
                print()
                terminal_color_print(f"[达到工具调用上限 {max_tool_rounds} 次]", "yellow")
                break


if __name__ == "__main__":
    cli_talk()
