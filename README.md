# AgentParty

两种方式和大模型聊天：终端直接聊，或者读写 markdown 文件。

## 安装

```bash
pip install -r requirements.txt
```

## 用法

### CLI 模式 —— 终端聊天

```bash
python cli_talk.py
```

在终端里一轮一轮地聊，带颜色、有打字机效果。

### File 模式 —— 读写 md 文件

```bash
python file_talk.py
```

启动后监听当前目录下所有 `.md` 文件。符合格式的文件（见下文）写到 `\n\n` 结尾时自动触发 AI 回复，回复追回文件末尾。

## 配置

项目不存 api key。首次运行任一模式时，缺什么问什么，回答后自动存到 `.config.json`（已加入 `.gitignore`）。

File 模式还可以在单个 md 文件的 YAML frontmatter 里覆写配置（临时换模型/API 很方便）。

## 文件格式（File 模式）

```markdown
---
name: 猫娘
# name 可选：显示用，文件角色头用这个名字。缺省用 model。
# model / api_key / base_url 缺了会从 .config.json 或手输补。
---

system: 你是猫娘，回答简短

user: 你好
```

文件末尾写两个换行触发聊天。AI 思考打印在控制台，正文追加到文件。一轮说完自动补 `\n\nuser: ` 等你写下一句。

## 文件结构

```
config.py      配置解析 — resolve_config 按优先级合并 fallback
core.py        共享内核 — request_llm + stream_events + 彩色打印
cli_talk.py    CLI 模式入口
file_talk.py   File 模式入口
watch_file.py  基于 watchdog 的文件监听
```
