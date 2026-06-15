# =====================================================================
# 单一事实来源：掌管所有"文件格式"和"控制台格式"的声明。
# parse_file 把 text→(meta, messages)；format_* 把参数→字符串。
# 所有硬编码字符串（分隔符、role 语法、结尾提示）都在这里。
# =====================================================================
import re
import yaml


class ChatFormatter:
    """声明式定义 Markdown 聊天文件的格式映射。

    集中管理：frontmatter 分隔符、role 头语法、角色映射规则、
    控制台抬头格式、下一轮输入提示。改格式只改这里。
    """
    FRONTMATTER_SEP = "---\n"
    SYS_ROLES = ["system", "user"]

    # ==================================================================
    # 解析方向：Text → (Meta, Messages)
    # ==================================================================
    @classmethod
    def parse_file(cls, text: str):
        """反序列化：文件文本 → (meta 字典, OpenAI messages 列表)。

        两阶段解析：
          1. 静态阶段：剥离 frontmatter（--- 包裹的 YAML）
          2. 动态阶段：用 frontmatter 推导出的显示名编译 role 正则，
             再拆分正文为 dialogue 片段并映射为 OpenAI 格式。
        返回 (meta, messages)；不符合格式返回 (None, None)。
        """
        # --- 第一阶段：剥离 frontmatter ---
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
        if not m:
            return None, None
        try:
            meta = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            return None, None
        if not isinstance(meta, dict):
            return None, None
        body = m.group(2)

        # --- 运行时推导动态 Schema ---
        display_name = meta.get("name") or meta.get("model", "assistant")
        valid_roles = cls.SYS_ROLES + [display_name]

        # --- 第二阶段：上下文感知的正文解析 ---
        alt = "|".join(re.escape(r) for r in valid_roles)
        pattern = r"(?P<sep>(?P<role>" + alt + r"):[ \n])"
        parts = re.split(pattern, body)

        messages = []
        i = 0
        while i < len(parts):
            tok = parts[i]
            if tok in valid_roles:
                content = (parts[i + 1] if i + 1 < len(parts) else "").strip()
                api_role = "assistant" if tok not in cls.SYS_ROLES else tok
                messages.append({"role": api_role, "content": content})
                i += 2
            else:
                i += 1
        return meta, messages

    # ==================================================================
    # 渲染方向：参数 → 字符串
    # ==================================================================
    @classmethod
    def format_role_header_file(cls, display_name: str) -> str:
        """文件里的角色头格式（不带换行——换行由 body 末尾的 \n\n 提供）"""
        return f"{display_name}: "

    @classmethod
    def format_role_header_console(cls, name: str, model: str) -> str:
        """控制台里的角色头格式"""
        return f"\n{name}({model}):"

    @classmethod
    def format_next_user_prompt(cls) -> str:
        """对话结束时留给用户的下一轮输入锚点"""
        return "\n\nuser: "
