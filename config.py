# =====================================================================
# 配置解析：把“从哪里读配置”这件事单独拎出来，和对话逻辑解耦。
#
# 配置项：api_key / base_url / model（file 版还会带可选的 name，但 name
# 不是“必需项”，不参与补缺，所以这里只关心 required 三项）。
#
# 优先级（从低到高，dict 合并时高优先级在右覆盖低优先级）：
#   DEFAULTS(默认值) < .config.json < 各 sources（如 frontmatter） < 手输补缺
#
# 设计原则：
#   - 每个“环境”单独写读取函数，各自 fallback，满足即停。
#   - 合并用 dict 解包 {**low, **high}，最优美。
#   - 逐项补缺：只对缺的 key 手输。
#   - 只存手输补的那几项：不动已有项、不把 frontmatter 覆盖项污染进全局。
# =====================================================================
import json
import os

CONFIG_PATH = ".config.json"
REQUIRED = ["api_key", "base_url", "model"]
# 所有的可选配置项默认值统一在这里管理
DEFAULTS = {
    "log": False,
    "watch_path": "."
}


def load_config(path=CONFIG_PATH):
    """读 .config.json。文件不存在或坏掉就返回空 dict（垫底用）。"""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(patch, path=CONFIG_PATH):
    """把 patch 里的 key 合并进现有 .config.json 后写回。

    只更新 patch 里的项，已有的其他项原样保留——所以是“合并写回”而非覆盖。
    """
    if not patch:
        return
    merged = {**load_config(path), **patch}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)


def prompt_missing(merged, required=REQUIRED):
    """找出 merged 里还缺的 required 项，逐项 input()，返回手输到的 dict。

    只问缺的那几项；已有的不重问。返回的 dict 仅含本次手输补的 key。
    """
    typed = {}
    for key in required:
        if not merged.get(key):
            typed[key] = input(f"请输入 {key}: ").strip()
    return typed


def resolve_config(*sources, required=REQUIRED, path=CONFIG_PATH):
    """按优先级合并配置，逐项补缺手输，把手输项存回 .config.json。

    sources: 若干来源 dict，低优先级在前、高优先级在后。
             例如 file 版传 frontmatter（它该覆盖 .config.json）。
             CLI 版不传 sources。
    返回：满足 required 的完整配置 dict。

    合并顺序（低→高）：DEFAULTS -> .config.json -> *sources -> 手输补缺。
    """
    # 1. DEFAULTS 垫底，.config.json 和 sources 依次叠上去（后者覆盖前者）
    merged = {**DEFAULTS, **load_config(path)}
    for src in sources:
        merged = {**merged, **(src or {})}

    # 2. 逐项补缺：只对仍然缺的 required 项手输
    typed = prompt_missing(merged, required)

    # 3. 只把手输补的那几项存回 .config.json（不污染已有项 / 不存 frontmatter 覆盖项）
    save_config(typed, path)

    # 4. 手输项优先级最高，叠在最上面
    return {**merged, **typed}
