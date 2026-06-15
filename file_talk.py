# =====================================================================
# file 模式：用“读写 md 文件”的方式和 AI 聊天。
#
# 核心约定：
#   1. 文件开头是 YAML frontmatter（两道 --- 夹起来），可提供
#      base_url / api_key / model / name。没有 frontmatter 的文件静默跳过。
#      （缺的配置项由 resolve_config 从 .config.json 或手输补。）
#   2. 正文用 `<role>: ` 分割角色（system / user / 显示名）。
#   3. 第一个 `<role>: ` 之前的内容被丢弃（预期行为）。
#   4. 检测到文件以双换行 `\n\n` 结尾时触发一次聊天。
#   5. 思考仅打印到控制台（根本不进文件）；正文仅追加到文件。
#      —— 因为思考不入文件，body 里只有正文，无需缩进检测。
# =====================================================================
import re

import yaml
from openai import OpenAI

from config import resolve_config
from core import request_llm, stream_events, terminal_color_print


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
    本函数只负责拆分，不处理缩进/思考。
    """
    # 角色头形如 `role: `（冒号后跟一个空格或换行）。
    # 用命名分组保留分隔符，后面用 m.group('role') 取出角色名。
    alt = "|".join(re.escape(r) for r in roles)
    pattern = r"(?P<sep>(?P<role>" + alt + r"):[ \n])"
    parts = re.split(pattern, text)

    # re.split 带命名组时会把 sep 和 role 两个组都塞进结果里。
    # 结构：[前缀, sep, role, content, sep, role, content, ...]
    # 用状态机扫描：遇到一个合法 role 就开一个新段。
    dialogues = []
    i = 0
    while i < len(parts):
        tok = parts[i]
        if tok in roles:
            # parts[i] 是 role 名，parts[i+1] 是 content
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
        # 也许应该允许空输入
        # if not content:
        #     continue
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
                terminal_color_print(f"\n{name}({model}):", "cyan")
                append(f"{name}: ")
            case ("thinking", text):
                if not thinking:
                    thinking = True
                terminal_color_print(text, "yellow", end="")
            case ("content", text):
                if thinking:
                    thinking = False
                    print()
                append(text)
            case ("usage", u):
                if thinking:
                    thinking = False
                print()
                terminal_color_print(
                    f"输入: {u['prompt']}, 输出: {u['completion']}, 总: {u['total']}",
                    "gray",
                )
                terminal_color_print(
                    f"思考: {u['reasoning']}, 缓存命中: {u['cache_hit']}, 缓存未命中: {u['cache_miss']}",
                    "gray",
                )
            case ("error", el):
                print()
                terminal_color_print(el, "red")


def handler(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()

    # 只有以双换行结尾时才触发（表示 user 输入完毕）。
    # 我们自己写入后以 `\n\nuser: ` 结尾，不会重复触发。
    if not text.endswith("\n\n"):
        return

    meta, body = parse_frontmatter(text)
    # 无 frontmatter → 静默跳过（“带标记”= 以 frontmatter 开头）。
    # api_key/base_url/model 缺不缺，交给 resolve_config 补（config 或手输）。
    if meta is None:
        return

    # file 版优先级：frontmatter（source）> .config.json > 手输补缺。
    config = resolve_config(meta)

    # 解析历史时，角色名用显示名（frontmatter name 优先，回退到 model）。
    messages = build_messages(config, body)
    if not messages:
        return

    client = OpenAI(api_key=config["api_key"], base_url=config["base_url"])
    response = request_llm(client, config["model"], messages)

    # 因为文件已以 `\n\n` 结尾，直接追加 `<name>: ` 再接正文，排版合理。
    consume_to_file(
        stream_events(response), path, display_name(config), config["model"]
    )

    # 模型输出完成，末尾加 `\n\nuser: ` 等待下一步输入。
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n\nuser: ")


def file_talk():
    from watch_file import NonBlockingWatcher

    watcher = NonBlockingWatcher()
    watcher.set_handler(handler)  # 通用处理器，所有 .md 文件自动接管
    watcher.loop()


if __name__ == "__main__":
    file_talk()
