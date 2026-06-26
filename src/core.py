# =====================================================================
# 共享内核：和 AI 打电话 + 把流式响应翻译成“语义事件” + 终端彩色打印。
#
# cli 模式和 file 模式都依赖这里，但各自怎么消费事件、写哪里，由它们自己决定。
# 颜色只活在“打控制台”这一步（_terminal_color_print），不背路由职责。
# =====================================================================
from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import Choice, ChoiceDelta
from openai.types.completion_usage import CompletionTokensDetails, CompletionUsage


# =====================================================================
# 怎么给 AI 打电话：client 和 model 都从配置来，所以作为参数传进来。
# =====================================================================
def request_llm(client, model, messages):
    return client.chat.completions.create(
        model=model,  # 告诉客服我们要找哪个型号的AI接电话
        messages=messages,  # 把我们想说的话递过去
        stream=True,  # 像打字机一样一个字一个字蹦出来，而不是等几分钟后一次性发一长串
        reasoning_effort="high",  # 让 AI 多动点脑子
        extra_body={"thinking": {"type": "enabled"}},  # 让 AI 把思考过程也发给我们看
    )


# =====================================================================
# 把 AI 的流式响应翻译成“语义事件”
#
# stream_events 不管怎么显示、也不管写文件，只负责把一堆零碎的快递包裹
# 分类，后 yield 出一个统一的二元组 (类型, 内容)：
#   ("role",     model_name)   AI 开始说话，带 API 返回的模型名
#   ("thinking", text)         思考内容片段
#   ("content",  text)         正式回复片段
#   ("usage",    dict)         账单（token 统计）
#   ("error",    obj)          不认识的包裹
#
# 谁来消费这些事件、怎么显示/写哪里，由调用方决定（cli 一种、file 一种）。
# =====================================================================
def stream_events(response):
    for delta in response:
        match delta:
            # 第一种包裹：AI 开始回话，带着模型名
            case ChatCompletionChunk(
                choices=[Choice(delta=ChoiceDelta(role="assistant"))], model=model_name
            ):
                yield ("role", model_name)

            # 第二种包裹：思考内容
            case ChatCompletionChunk(
                choices=[
                    Choice(
                        delta=ChoiceDelta(
                            content=None, reasoning_content=reasoning_content
                        )
                    )
                ]
            ):
                yield ("thinking", reasoning_content)

            # 第三种包裹：正式回复
            case ChatCompletionChunk(
                choices=[
                    Choice(delta=ChoiceDelta(content=content, reasoning_content=None))
                ]
            ):
                if content is not None:
                    yield ("content", content)

            # 第四种包裹：不认识的奇怪包裹
            case el:
                yield ("error", el)

        # 看看包裹底部有没有贴着“账单”
        match delta.usage:
            case CompletionUsage(
                completion_tokens=completion_tokens,
                prompt_tokens=prompt_tokens,
                total_tokens=total_tokens,
                completion_tokens_details=CompletionTokensDetails(
                    reasoning_tokens=reasoning_tokens
                ),
                prompt_cache_hit_tokens=prompt_cache_hit_tokens,
                prompt_cache_miss_tokens=prompt_cache_miss_tokens,
            ):
                yield (
                    "usage",
                    {
                        "prompt": prompt_tokens,
                        "completion": completion_tokens,
                        "total": total_tokens,
                        "reasoning": reasoning_tokens,
                        "cache_hit": prompt_cache_hit_tokens,
                        "cache_miss": prompt_cache_miss_tokens,
                    },
                )


# =====================================================================
# 终端彩色打印：把颜色名翻译成 ANSI 转义码后打到控制台。
# =====================================================================
COLOR_DICT = {
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "purple": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "gray": "\033[90m",
}
RESET = "\033[0m"  # 变色完毕后用它把颜色洗掉，不然整个屏幕都会被染色


def terminal_color_print(text, color, end="\n"):
    """把 text 用指定颜色打到控制台。找不到颜色就不上色。"""
    if text is None or text == "":
        print(end=end)
        return
    color_code = COLOR_DICT.get(color.lower(), "")
    print(f"{color_code}{text}{RESET}", end=end)


def meta_output(text: str, color: str, end="\n", log_path=None):
    """元信息输出工具：thinking/usage/role 的统一输出

    为什么独立：
    - CLI 和 File 的 meta 信息（thinking/usage/role）处理完全相同
    - 唯一差异是输出目标（控制台 vs log 文件）
    - 提取此函数避免两处重复相同逻辑

    参数：
    - text: 输出内容
    - color: 颜色名（用于控制台）
    - end: 结尾字符（默认换行）
    - log_path: None = 控制台，str = 写日志文件
    """
    if log_path:
        with open(log_path, "a", encoding="utf-8") as lf:
            lf.write(text + end)
    else:
        terminal_color_print(text, color, end=end)
