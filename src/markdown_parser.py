# =====================================================================
# Markdown 解析器：md 文本 → (meta, messages)
#
# 职责：
# 1. 提取 YAML frontmatter（元信息：model/api_key 等）
# 2. 解析对话消息：按顶格 ## role 分段，4 空格缩进内容
# 3. 展开 @file 引用：替换为文件实际内容到 system 消息
#
# 为什么独立：
# - 纯函数，无副作用，易于测试
# - 与渲染逻辑分离，符合单一职责原则
# =====================================================================
import re
from pathlib import Path

import yaml

from src.format_schema import ROLE_MARKER, FILE_REF_PREFIX, FRONTMATTER_SEP, INDENT


def parse_file(text: str):
    """解析 md 文件：提取 frontmatter + 对话消息

    返回：(meta: dict | None, messages: list | None)
    - meta: YAML 头部解析结果，解析失败返回 None
    - messages: OpenAI 格式消息列表，格式错误返回 None
    """
    # 1. 提取 frontmatter
    pattern = rf"^{FRONTMATTER_SEP}\s*\n(.*?)\n{FRONTMATTER_SEP}\s*\n?(.*)$"
    m = re.match(pattern, text, re.DOTALL)
    if not m:
        return None, None

    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None, None

    if not isinstance(meta, dict):
        return None, None

    # 2. 解析对话消息
    body = m.group(2)
    messages = []
    current_role = None
    current_lines = []

    for raw_line in body.split("\n"):
        # 空行：追加到当前消息（保留段落结构）
        if raw_line == "":
            if current_lines:
                current_lines.append("")
            continue

        # 顶格行：可能是控制行（## role 或 @file）
        if raw_line[0] not in (" ", "\t"):
            # Flush 当前消息
            flushed = _flush(current_role, current_lines)
            if flushed is not None:
                messages.append(flushed)
            current_role = None
            current_lines = []

            # 处理控制行
            if raw_line.startswith(FILE_REF_PREFIX):
                ref = raw_line[len(FILE_REF_PREFIX):].strip()
                content = _resolve_file_ref(ref)
                if content:
                    messages.append({"role": "system", "content": content})

            elif raw_line.startswith(f"{ROLE_MARKER} "):
                current_role = _map_role(raw_line[len(ROLE_MARKER) + 1:].strip())

            continue

        # 缩进行：消息内容
        if current_role:
            current_lines.append(_strip_one_indent(raw_line))

    # Flush 最后一条消息
    flushed = _flush(current_role, current_lines)
    if flushed is not None:
        messages.append(flushed)

    return meta, messages


# =====================================================================
# 内部辅助函数
# =====================================================================

def _flush(role, lines):
    """将缓冲区内容转为一条消息

    为什么需要：解析是逐行的，需要攒够一个完整角色块才能输出
    """
    if not role or not lines:
        return None
    content = "\n".join(lines).strip()
    if not content:
        return None
    return {"role": role, "content": content}


def _map_role(name):
    """将 md 标记映射为 OpenAI 角色名

    为什么这样设计：
    - user 保持原样（人类输入）
    - 其他一律视为 assistant（AI 响应、系统提示等）
    """
    return {"user": "user"}.get(name, "assistant")


def _strip_one_indent(line):
    """去除一级缩进（4 空格或 1 tab）

    为什么只去一级：
    - 保留用户代码块的内部缩进结构
    - 例：Python 代码的 if 嵌套不会被破坏
    """
    if line.startswith(INDENT):
        return line[len(INDENT):]
    if line.startswith("\t"):
        return line[1:]
    return line


def _resolve_file_ref(ref):
    """展开 @file 引用：读取文件内容

    格式：
    - @file path：全文
    - @file path:10：第 10 行
    - @file path:10-20：第 10-20 行（闭区间）

    为什么返回带标记的字符串：
    - 让 AI 知道这是引用内容，不是直接输入
    - 便于调试：错误信息也带标记
    """
    parts = ref.split(":")
    path_str = parts[0].strip()

    try:
        p = Path(path_str)
        if not p.exists():
            return f"[@file 文件不存在: {path_str}]"

        with open(p, encoding="utf-8") as f:
            all_lines = f.readlines()

        # 解析行号范围
        if len(parts) > 1:
            r = parts[1].strip()
            if "-" in r:
                # 范围：10-20
                s, e = r.split("-", 1)
                start = max(0, int(s.strip()) - 1)  # 用户从 1 开始计数
                end = min(len(all_lines), int(e.strip()))
                selected = all_lines[start:end]
            else:
                # 单行：10
                idx = max(0, int(r.strip()) - 1)
                selected = [all_lines[idx]] if idx < len(all_lines) else []
        else:
            # 全文
            selected = all_lines

        content = "".join(selected).rstrip()
        if not content:
            return None
        return f"[@file {ref}]\n{content}"

    except Exception as exc:
        return f"[@file 读取失败 {path_str}: {exc}]"
