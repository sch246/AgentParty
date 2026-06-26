# =====================================================================
# 工具执行器
#
# 设计理念：
# 1. do python/sh 块：AI 可以调用本地工具
# 2. 输出追加 log：结果通过 @file 回引到上下文
# 3. 沙盒命名空间：注入 messages/readfile，可通过 extra_ns 扩展
#
# parse_do_blocks: 从 AI 原始回复提取 do python / do sh 块
# execute_blocks:  沙盒执行 → 输出追加 log → 返回行号范围
# =====================================================================
import io
import re
import os
import subprocess
import sys
from pathlib import Path


def parse_do_blocks(text: str):
    """提取 do python / do sh 块 → [(type, code)]。code 已 strip 一层缩进。"""
    blocks = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        m = re.match(r"^do\s+(python|sh)\s*$", lines[i])
        if m:
            block_type = m.group(1)
            code_lines = []
            i += 1
            while i < len(lines):
                if re.match(r"^end\s*$", lines[i]):
                    break
                code_lines.append(_strip_one_indent(lines[i]))
                i += 1
            blocks.append((block_type, "\n".join(code_lines)))
        i += 1
    return blocks


def has_do_block(text: str) -> bool:
    return bool(re.search(r"^do\s+(python|sh)\s*$", text, re.MULTILINE))


def execute_blocks(blocks, messages, log_path, extra_ns=None):
    """串行执行 do 块，输出追加 log_path。
    返回 [(type, start_line, end_line)]。
    extra_ns 合并进沙盒命名空间（可覆盖 message/readfile 或追加新函数）。
    """
    results = []
    with open(log_path, "a", encoding="utf-8") as log:
        for block_type, code in blocks:
            before = _count_lines(log_path)
            log.write(f"\n--- do {block_type} ---\n")
            log.flush()

            output = _run(block_type, code, messages, extra_ns)
            log.write(output)
            if not output.endswith("\n"):
                log.write("\n")
            log.flush()

            after = _count_lines(log_path)
            results.append((block_type, before + 1, after))
    return results


# ---------------------------------------------------------------------------
def _run(block_type, code, messages, extra_ns):
    ns = _build_namespace(messages, extra_ns)
    if block_type == "sh":
        return _run_sh(code)
    return _run_python(code, ns)


def _build_namespace(messages, extra_ns):
    """构建沙盒命名空间。extra_ns 可覆盖/追加。"""
    ns = {
        "messages": messages,
        "readfile": _read_fn(),
    }
    if extra_ns:
        ns.update(extra_ns)
    return ns


# ---- sh ----------------------------------------------------------------
def _run_sh(code):
    try:
        r = subprocess.run(code, shell=True, capture_output=True, text=True)
        out = r.stdout
        if r.stderr:
            out += r.stderr
        return out
    except Exception as exc:
        return f"[do sh 异常: {exc}]"


# ---- python ------------------------------------------------------------
def _run_python(code, ns):
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        exec(code, ns)
        return buf.getvalue()
    except Exception as exc:
        return f"[do python 异常: {exc}]\n{buf.getvalue()}"
    finally:
        sys.stdout = old


def _read_fn():
    def read(path):
        try:
            if os.path.isfile(path):
                return Path(path).read_text(encoding="utf-8")
            elif os.path.isdir(path):
                return _plist_dir(path)
        except Exception as exc:
            return f"[read({path}) 失败: {exc}]"

    return read


# ---- util --------------------------------------------------------------
def _strip_one_indent(line):
    if line.startswith("    "):
        return line[4:]
    if line.startswith("\t"):
        return line[1:]
    return line


def _count_lines(path):
    try:
        with open(path, encoding="utf-8") as f:
            return sum(1 for _ in f)
    except FileNotFoundError:
        return 0

def _plist_dir(path):
    return '\n'.join(f'> {d}' if os.path.isdir(os.path.join(path, d)) else d
                     for d in os.listdir(path))
