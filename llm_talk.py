# =====================================================================
# 第一部分：借工具
# Python 最强大的地方在于“白嫖”。这几行意思是：我们把别人写好的、
# 用来连接人工智能的工具包拿过来用。对于新手来说，这部分“当做咒语照抄”就行。
# =====================================================================
import re

import yaml
from openai import OpenAI
from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import ChoiceDelta, Choice
from openai.types.completion_usage import CompletionUsage, CompletionTokensDetails

from config import resolve_config


# =====================================================================
# 第三部分：教电脑学会一个新动作：【怎么给AI打电话】
# client 和 model 都从配置来（不再写死），所以要作为参数传进来。
# =====================================================================
def request_llm(client, model, messages):
    return client.chat.completions.create(
        model=model,  # 告诉客服我们要找哪个型号的AI接电话
        messages=messages,  # 把我们想说的话递过去
        stream=True,  # 这个非常关键！意思是“像打字机一样一个字一个字蹦出来”，而不是等几分钟后一次性发一长串
        reasoning_effort="high",  # 让 AI 多动点脑子
        extra_body={
            "thinking": {"type": "enabled"}
        },  # 强行让 AI 把它的“心理活动（思考过程）”也发给我们看
    )


# =====================================================================
# 第四部分：把 AI 的流式响应翻译成“语义事件”
#
# stream_events 不管怎么显示、也不管写文件，只负责把一堆零碎的
# 快递包裹分类，后 yield 出一个统一的二元组 (类型, 内容)：
#   ("role",     model_name)   AI 开始说话，带 API 返回的模型名
#   ("thinking", text)         思考内容片段
#   ("content",  text)         正式回复片段
#   ("usage",    dict)         账单（token 统计）
#   ("error",    obj)          不认识的包裹
#
# 谁来消费这些事件、怎么显示/写哪里，由调用方决定（cli 一种、file 一种）。
# 这样颜色就只活在“打控制台”那一步，不再背路由职责。
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


cli_thinking = False


def color_print(text, color, end="\n"):
    global cli_thinking
    if color == "yellow" and not cli_thinking:
        cli_thinking = True
        print()
    elif color != "yellow" and cli_thinking:
        cli_thinking = False
        print()

    # 字典（长得像大括号 {}）：就像一本汉英词典。
    # 左边是颜色的名字，右边是电脑终端才能看懂的“颜色魔法代码”。
    color_dict = {
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "purple": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
        "gray": "\033[90m",
    }

    reset = "\033[0m"  # 变色完毕后，必须用这个代码把颜色洗掉，不然整个屏幕都会被染色

    # 去上面的词典里查颜色代码。如果找不到，就默认什么颜色都不加（返回 ""）
    color_code = color_dict.get(color.lower(), "")

    # f"..." 是一种超级方便的文字拼接魔法，把颜色代码、文字、洗掉颜色的代码串在一起打印。
    # end=end 是为了控制打字机效果，告诉电脑“打印完这批字先不要换行”。
    print(f"{color_code}{text}{reset}", end=end)


def consume_to_terminal(events):
    """cli 消费者：把所有事件都上色打到控制台，返回完整正文。"""
    response_text = ""
    for kind, payload in events:
        match (kind, payload):
            case ("role", model_name):
                color_print(f"{model_name}: ", "cyan", end="")
            case ("thinking", text):
                color_print(text, "yellow", end="")
            case ("content", text):
                color_print(text, "green", end="")
                response_text += text
            case ("usage", u):
                print()
                color_print(
                    f"输入: {u['prompt']}, 输出: {u['completion']}, 总: {u['total']}",
                    "gray",
                )
                color_print(
                    f"思考: {u['reasoning']}, 缓存命中: {u['cache_hit']}, 缓存未命中: {u['cache_miss']}",
                    "gray",
                )
            case ("error", el):
                print()
                color_print(el, "red")
    return response_text


def cli_talk():
    # 0. 解析配置：CLI 不传 sources，优先级只有 .config.json → 手输补缺。
    config = resolve_config()
    client = OpenAI(api_key=config["api_key"], base_url=config["base_url"])
    model = config["model"]

    # 1. 创建一个叫 messages 的“列表”（长得像方括号 []）。
    # 列表就像是一个大抽屉，里面按顺序装着我们聊天的历史记录。
    # 最开始，抽屉里只有一句话：偷偷给AI设定一个“猫娘”的身份。
    messages = [{"role": "system", "content": "你是一只猫娘"}]

    # 2. while True: 是一个“死循环”。
    # 意思是不管发生什么，一遍又一遍地重复下面的事情，这样我们就可以一直聊天不中断。
    while True:
        # 提醒轮到你说话了
        color_print("user: ", color="cyan", end="")

        # input() 就是在屏幕上停住，等你用键盘打字，打完按回车。
        # 你的话会被存进 request_text 这个盒子里。
        request_text = input()

        # 将你说的话，装进一个特定的格式里，扔进 messages（历史记录大抽屉）的最后面。
        messages += [{"role": "user", "content": request_text}]

        # 把整个抽屉（包括人设、之前的聊天、你刚说的话）打包发给AI！
        response = request_llm(client, model, messages)

        # 让机器人在屏幕上“打字机”式地把回复打印出来，并把完整的回复记下来。
        response_text = consume_to_terminal(stream_events(response))

        # 最关键的一步：有了记忆！
        # 把 AI 刚刚说的话，也扔进 messages 大抽屉里。
        # 这样下一轮聊天时，AI 就能看到自己上回说了啥，从而不会精神分裂。
        messages += [{"role": "assistant", "content": response_text}]


# =====================================================================
# 第六部分：file_talk —— 用“读写 md 文件”的方式和 AI 聊天
#
# 核心约定：
#   1. 文件开头是 YAML frontmatter（两道 --- 夹起来），提供
#      base_url / api_key / model 三个参数。没有 frontmatter 的文件静默跳过。
#   2. 正文用 `<role>: ` 分割角色（system / user / 模型名）。
#   3. 第一个 `<role>: ` 之前的内容被丢弃（预期行为）。
#   4. 检测到文件以双换行 `\n\n` 结尾时触发一次聊天。
#   5. 思考仅打印到控制台（根本不进文件）；正文仅追加到文件。
#      —— 因为思考不入文件，body 里只有正文，无需缩进检测。
# =====================================================================


def parse_frontmatter(text):
    """拆分 YAML frontmatter 和正文。

    文件必须以 `---\n` 开头，中间是 YAML，再用一行 `---` 结束。
    返回 (meta字典, body文本)；不符合格式返回 (None, None)。
    """
    # “带特定标记”= 以 frontmatter 开头。不以 --- 开头的一律跳过。
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if not m:
        return None, None
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None, None
    if not isinstance(meta, dict):
        return None, None
    return meta, m.group(2)


def parse_text_to_dialogue(text, roles):
    """把正文拆成 [{role, content}, ...]。

    roles: 角色名列表，例如 ['system', 'user', 'deepseek-v4-flash']。
    第一个 `<role>: ` 之前的内容被丢弃（current_role 为 None 时不记录）。
    本函数只负责拆分，不处理缩进/思考（交给 strip_thinking）。
    """
    # 角色头形如 `role: ` （冲号后跟一个空格或换行）。
    # 用捆绑的分组保留分隔符，后面用 m.group('role') 取出角色名。
    alt = "|".join(re.escape(r) for r in roles)
    pattern = r"(?P<sep>(?P<role>" + alt + r"):[ \n])"
    parts = re.split(pattern, text)

    # re.split 带命名组时会把 sep 和 role 两个组都充进结果里。
    # 结构：[前缀, sep, role, content, sep, role, content, ...]
    # 我们用状态机扫描：遇到一个合法 role 就开一个新段。
    dialogues = []
    i = 0
    while i < len(parts):
        tok = parts[i]
        if tok in roles:
            # parts[i] 是 role 名，parts[i-1] 是完整 sep，parts[i+1] 是 content
            content = parts[i + 1] if i + 1 < len(parts) else ""
            dialogues.append({"role": tok, "content": content})
            i += 2
        else:
            i += 1
    return dialogues


def display_name(meta):
    """取显示名：frontmatter 有 name 就用 name，否则回退到 model。

    显示名同时是文件角色头、也是下一轮解析的 key，所以要稳定、用户可控。
    """
    return meta.get("name") or meta["model"]


def build_messages(meta, body):
    """把正文转成 OpenAI 格式的 messages。显示名角色映射为 assistant。

    思考内容从不写入文件，所以 body 里每个角色的 content 就是纯正文，
    只需 strip 掉分割造成的前后空白即可。角色头用显示名（name），
    不是 model——这样显示名与调用名解耦，也避开了 API 返回名与配置名不一致的问题。
    """
    name = display_name(meta)
    raw = parse_text_to_dialogue(body, ["system", "user", name])
    messages = []
    for d in raw:
        role = d["role"]
        content = d["content"].strip()
        if not content:
            continue
        api_role = role if role in ("system", "user") else "assistant"
        messages.append({"role": api_role, "content": content})
    return messages


def consume_to_file(events, path, name, model):
    """file 消费者：

    - 角色头 / 正文 → 追加写文件。角色头用显示名 name（不是 API 返回名）。
    - 思考 / 账单 / 报错 → 打到控制台。控制台抬头显示 name(model) 方便定位。
    颜色只出现在“打控制台”这一步，不再背路由职责。
    """
    thinking = False  # 控制台思考/正文切换时插空行用

    def append(s):
        with open(path, "a", encoding="utf-8") as f:
            f.write(s)

    for kind, payload in events:
        match (kind, payload):
            case ("role", _api_name):
                # 控制台抬头：name(model)；文件里只写 name
                _terminal_color_print(f"\n{name}({model}):", "cyan")
                append(f"{name}: ")
            case ("thinking", text):
                if not thinking:
                    thinking = True
                _terminal_color_print(text, "yellow", end="")
            case ("content", text):
                if thinking:
                    thinking = False
                    print()
                append(text)
            case ("usage", u):
                if thinking:
                    thinking = False
                print()
                _terminal_color_print(
                    f"输入: {u['prompt']}, 输出: {u['completion']}, 总: {u['total']}",
                    "gray",
                )
                _terminal_color_print(
                    f"思考: {u['reasoning']}, 缓存命中: {u['cache_hit']}, 缓存未命中: {u['cache_miss']}",
                    "gray",
                )
            case ("error", el):
                print()
                _terminal_color_print(el, "red")


def _terminal_color_print(text, color, end="\n"):
    """纯控制台彩色打印（不带 cli_thinking 全局状态的版本）。"""
    color_dict = {
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "purple": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
        "gray": "\033[90m",
    }
    reset = "\033[0m"
    color_code = color_dict.get(color.lower(), "")
    print(f"{color_code}{text}{reset}", end=end)


def handler(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()

    # 只有以双换行结尾时才触发（表示 user 输入完毕）。
    # 我们自己写入后以 `\n\nuser: ` 结尾，不会重复触发。
    if not text.endswith("\n\n"):
        return

    meta, body = parse_frontmatter(text)
    # 无 frontmatter → 静默跳过（“带标记”= 以 frontmatter 开头）。
    # 至于 api_key/base_url/model 缺不缺，交给 resolve_config 补（config 或手输）。
    if meta is None:
        return

    # file 版优先级：frontmatter（source）> .config.json > 手输补缺。
    config = resolve_config(meta)

    # 解析历史时，角色名用显示名（meta 优先，回退到 resolve 后的 model）。
    messages = build_messages(config, body)
    if not messages:
        return

    client = OpenAI(api_key=config["api_key"], base_url=config["base_url"])
    response = client.chat.completions.create(
        model=config["model"],
        messages=messages,
        stream=True,
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )

    # 因为文件已以 `\n\n` 结尾，直接追加 `<name>: ` 再接正文，排版合理。
    consume_to_file(
        stream_events(response), path, display_name(config), config["model"]
    )

    # 模型输出完成，末尾加 `\n\nuser: ` 等待下一步输入。
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n\nuser: ")


def file_talk():
    import glob

    from watch_file import loop, watcher

    # 监听当前目录下所有 .md；是否是“带标记”文件由 handler 里的 frontmatter 检查决定。
    for md in glob.glob("*.md"):
        watcher.register(md, handler)
    loop()


if __name__ == "__main__":
    file_talk()
