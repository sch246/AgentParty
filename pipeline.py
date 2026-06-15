# =====================================================================
# 流式管道：raw API events → 语义 action 流 → 副作用执行。
# 状态机（apply_ux_rules）+ 执行器（execute_semantic_actions）= 一条管道。
# 不碰 I/O 细节、不依赖任何模式——handlers 路由表由调用方注入。
# =====================================================================


def apply_ux_rules(raw_event_stream):
    """纯 UX 状态机：raw events → 语义 action 流。

    action 词汇表（纯语义，不关心目的地）：
      "header"     — AI 开始说话，payload = API 返回的 model_name
      "ui_newline" — 排版信号：thinking/idle 状态切换时插入
      "thinking"   — 思考文本片段
      "content"    — 正式回复片段
      "usage"      — token 账单
      "error"      — 异常事件
    """
    state = "idle"  # idle | thinking | speaking

    for kind, payload in raw_event_stream:
        if kind == "role":
            yield ("header", payload)

        elif kind == "thinking":
            if state != "thinking":
                state = "thinking"
                yield ("ui_newline", None)
            yield ("thinking", payload)

        elif kind == "content":
            if state == "thinking":
                state = "speaking"
                yield ("ui_newline", None)
            yield ("content", payload)

        elif kind == "usage":
            if state == "thinking":
                state = "speaking"
            yield ("ui_newline", None)
            yield ("usage", payload)

        elif kind == "error":
            yield ("ui_newline", None)
            yield ("error", payload)


def execute_semantic_actions(semantic_stream, handlers: dict):
    """命令式外壳：查路由表执行副作用，累加正文后返回。

    handlers: {action_type: callable(payload)}，由调用方注入。
    返回完整正文（供 CLI 维护 messages 历史；File 模式可忽略）。
    """
    full_content = ""

    for action, payload in semantic_stream:
        if action == "content" and payload:
            full_content += payload

        handler_fn = handlers.get(action)
        if handler_fn:
            handler_fn(payload)

    return full_content
