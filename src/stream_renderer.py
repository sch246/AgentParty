# =====================================================================
# 流式渲染器：LLM 响应 → 缩进写文件
#
# 职责：
# 1. 消费 LLM 流式响应（content/thinking/usage 事件）
# 2. 将 content 按 4 空格缩进写入 md 文件
# 3. 将 thinking/usage 写入 log 或打印到控制台
#
# 为什么独立：
# - 与解析逻辑分离（解析是输入，渲染是输出）
# - 封装流式处理细节（换行符处理、缓冲逻辑）
# - 便于切换输出目标（文件/stdout/网络流）
# =====================================================================
from src.format_schema import ROLE_MARKER, INDENT
from src.core import stream_events, terminal_color_print


def write_response(response, md_path, name, log_path, enable_log):
    """流式消费 LLM 响应：缩进写 md，thinking 写 log/控制台

    参数：
    - response: OpenAI streaming response 对象
    - md_path: markdown 文件路径（追加模式）
    - name: 显示名称（写入 ## name）
    - log_path: 日志文件路径
    - enable_log: 是否写日志（False 时打印到控制台）

    返回：
    - raw: AI 原始文本（无缩进），供后续解析工具调用
    """

    def meta_out(text, color, end="\n"):
        """元信息输出：thinking/usage 不写 md，只记录或打印

        为什么分离：
        - thinking 是临时思考过程，不是最终回复
        - usage 是统计信息，不属于对话内容
        """
        if enable_log:
            with open(log_path, "a", encoding="utf-8") as lf:
                lf.write(text + end)
        else:
            terminal_color_print(text, color, end=end)

    raw = ""
    pending = ""

    with open(md_path, "a", encoding="utf-8") as f:
        # 写入角色标记：顶格 ## name
        f.write(f"{ROLE_MARKER} {name}\n")

        for kind, payload in stream_events(response):
            # content 事件：逐行缓冲，加缩进写文件
            if kind == "content" and isinstance(payload, str):
                raw += payload
                pending += payload

                # 逐行处理：保证每行都有缩进
                while "\n" in pending:
                    line, pending = pending.split("\n", 1)
                    f.write(f"{INDENT}{line}\n")

            # thinking 事件：打印或写 log（黄色，不换行）
            elif kind == "thinking" and isinstance(payload, str):
                meta_out(payload, "yellow", end="")

            # usage 事件：token 统计（灰色，换行）
            elif kind == "usage" and isinstance(payload, dict):
                meta_out(
                    f"\n输入: {payload['prompt']}, 输出: {payload['completion']}, "
                    f"总: {payload['total']}",
                    "gray",
                )

            # role 事件：显示当前角色（青色，不换行）
            elif kind == "role" and isinstance(payload, str):
                meta_out(f"{payload}: ", "cyan", end="")

        # Flush 最后的不完整行（没有换行符的结尾）
        if pending:
            f.write(f"{INDENT}{pending}")

    return raw


def write_anchor(md_path):
    """写入锚点：## user\n    （等待用户输入）

    为什么需要锚点：
    - 触发机制依赖双换行符 (\n\n)
    - 预留 4 空格缩进，用户可以直接开始输入
    - 视觉提示：对话到此结束，轮到用户了
    """
    with open(md_path, "a", encoding="utf-8") as f:
        f.write(f"\n\n{ROLE_MARKER} user\n{INDENT}")
