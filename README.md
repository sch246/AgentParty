# AgentParty

两种方式和大模型聊天：终端直接聊，或者读写 markdown 文件。

**特性：**
- 🖥️ CLI 模式：终端交互式聊天，带打字机效果
- 📝 File 模式：监听 markdown 文件，自动触发 AI 回复
- 🔧 工具调用：AI 可以执行 Python/Shell 命令
- ⚙️ 灵活配置：全局配置 + 文件级覆写

## 快速开始

### 安装

```bash
pip install -r requirements.txt
```

### 配置

首次运行会提示输入必要配置（API key、base URL、model），自动保存到 `.config.json`。

```bash
# CLI 模式：直接启动，缺少配置时会提示
python cli_talk.py

# File 模式：同样会自动补全配置
python file_talk.py
```

## 使用方式

### CLI 模式 —— 终端聊天

```bash
python cli_talk.py
```

在终端里一轮一轮地聊，带颜色、有打字机效果。

**工具调用示例：**

```
user: 帮我列出当前目录的文件

assistant: 好的，我来执行

do sh
    ls -la
end

[执行 1 个工具...]
--- do sh ---
total 64
drwxr-xr-x  10 user  staff   320 Jun 27 10:00 .
...

assistant: 当前目录有以下文件：...
```

AI 可以在回复中使用 `do py` 或 `do sh` 块执行工具，系统自动执行并将结果返回给 AI。

> 注：为向后兼容，仍支持 `do python`，但推荐使用 `do py`。

**配置项：**
- `max_tool_rounds`: 单次对话最多工具调用次数（默认 10）

### File 模式 —— 读写 md 文件

```bash
python file_talk.py
```

启动后监听当前目录下所有 `.md` 文件。符合格式的文件（见下文）写到 `\n\n` 结尾时自动触发 AI 回复，回复追加到文件末尾。

**工作流程：**
1. 编辑 `.md` 文件，写入对话内容
2. 以双换行符 `\n\n` 结尾触发
3. AI 思考过程显示在控制台
4. 回复追加到文件末尾
5. 自动添加 `## user\n    ` 等待下一轮输入

**工具调用：**

File 模式同样支持工具调用。当 AI 返回 `do py` 或 `do sh` 块时：
1. 自动执行工具代码
2. 输出写入 `.log` 文件（可选控制台）
3. 将结果通过 `@file` 引用回注入上下文
4. AI 继续生成后续回复

## 配置

### 全局配置 (.config.json)

首次运行时自动创建，包含：

```json
{
  "api_key": "your-api-key",
  "base_url": "https://api.openai.com/v1",
  "model": "gpt-4",
  "log": false,
  "watch_path": ".",
  "max_tool_rounds": 10,
  "debug": false,
  "max_retries": 3,
  "retry_delay": 2.0
}
```

**配置项说明：**
- `api_key`: API 密钥（必需）
- `base_url`: API 端点（必需）
- `model`: 模型名称（必需）
- `log`: thinking 输出到 log 文件而非控制台（默认 false）
- `watch_path`: 监听目录（默认当前目录）
- `max_tool_rounds`: 工具调用最多次数（默认 10）
- `debug`: 打印系统运行日志（默认 false）
- `max_retries`: 可恢复错误最大重试次数（默认 3）
- `retry_delay`: 重试间隔秒数（默认 2.0）

**配置实时生效：**
- File 模式：每次处理消息时读取最新配置，修改 `.config.json` 或 frontmatter 立即生效，无需重启
- CLI 模式：每轮对话前读取最新配置

### 文件级配置 (Frontmatter)

File 模式可以在单个 md 文件的 YAML frontmatter 里覆写配置：

```markdown
---
name: 猫娘
model: gpt-4-turbo
log: true
---

## system
    你是一只可爱的猫娘，说话要带"喵～"

## user
    你好
```

**优先级：** frontmatter > .config.json > 默认值

## 文件格式（File 模式）

```markdown
---
name: 猫娘
# name 可选：显示用，文件角色头用这个名字。缺省用 model。
# model / api_key / base_url 缺了会从 .config.json 或手输补。
---

## system
    你是猫娘，回答简短

## user
    你好
```

**格式规则：**
- frontmatter：`---` 包围的 YAML 配置
- 角色标记：顶格 `## role`
- 消息内容：4 空格缩进
- 触发条件：文件末尾双换行 `\n\n`

**@file 引用：**

```markdown
## user
    分析这段代码

@file context.py
@file utils.py:10
@file main.py:5-20
```

引用格式：
- `@file path.txt` - 全文
- `@file path.txt:10` - 第 10 行
- `@file path.txt:5-20` - 第 5 到 20 行

## 工具系统

AI 可以通过 `do` 块调用本地工具。

### 语法

```markdown
do py
    print("Hello from Python")
    x = 1 + 1
    print(f"Result: {x}")
end

do sh
    ls -la
    cat README.md
end
```

**规则：**
- 顶格写 `do py` 或 `do sh`（向后兼容 `do python`）
- 代码内容必须缩进（4 空格或 1 tab）
- 以顶格 `end` 结束
- 一个回复可以有多个 `do` 块

### 参数系统

工具调用支持参数，语法：`do <type> key=value ...`

**Python 超时控制：**
```markdown
do py timeout=60
    import time
    time.sleep(30)
    print("done")
end
```

**Shell 工作目录和超时：**
```markdown
do sh cwd=/tmp timeout=5
    pwd
    ls -la
end
```

**支持的参数：**
- `timeout=<秒>`: 超时时间（Python 和 Shell 都支持）
- `cwd=<路径>`: 工作目录（仅 Shell）

### Python 沙盒

Python 代码运行在沙盒环境中，可以访问：

**`messages`** - 完整对话历史：
```python
# 访问第 3 条消息
print(messages[2]["content"])

# 遍历所有消息
for msg in messages:
    print(f"{msg['role']}: {msg['content'][:50]}...")
```

**`readfile(path)`** - 读取文件或目录：
```python
# 读取文件
content = readfile("config.json")
print(content)

# 列出目录
files = readfile(".")
print(files)
```

### Shell 执行

Shell 命令直接在系统 shell 中执行：

```markdown
do sh
    # 列出文件
    ls -la
    
    # 查看 Git 状态
    git status
    
    # 运行测试
    python -m pytest tests/
end
```

**注意事项：**
- 不同 `do` 块之间不共享状态
- Python 块之间变量不共享
- 输出会完整返回给 AI
- 使用 `timeout` 参数可防止长时间运行

## 项目结构

```
.
├── cli_talk.py          CLI 模式入口
├── file_talk.py         File 模式入口
├── config.py            配置解析（优先级合并 + 补缺）
├── core.py              共享内核（LLM 请求 + 流式事件 + 彩色打印）
├── markdown_parser.py   Markdown 解析（frontmatter + 消息 + @file）
├── stream_renderer.py   流式渲染（LLM 响应 → 缩进写文件）
├── tool_executor.py     工具执行器（do 块解析 + 沙盒执行）
├── watch_file.py        文件监听（基于 watchdog）
├── format_schema.py     格式常量定义
├── tools.md             工具说明文档（自动加载为系统提示）
└── tests/               测试套件
    ├── test_parser.py
    ├── test_tool_executor.py
    ├── test_cli_tools.py
    ├── test_stream_renderer.py
    └── test_integration.py
```

## 测试

```bash
# 运行所有测试
python -m unittest discover tests -v

# 运行特定模块
python -m unittest tests.test_parser -v
python -m unittest tests.test_tool_executor -v
python -m unittest tests.test_integration -v

# 查看测试文档
cat tests/README.md
```

**测试覆盖：** 109 个测试，覆盖核心模块和集成场景。

## 架构设计

### KISS 原则

- 不引入接口/抽象类
- 状态机逻辑简单时内联（3 行）
- 只提取明显重复的函数（如 `meta_output`）

### 流式处理统一

CLI 和 File 模式都直接消费 `stream_events`：

```python
for kind, payload in stream_events(response):
    if kind == "content":
        # 处理正文
    elif kind == "thinking":
        # 处理思考过程
    elif kind == "usage":
        # 处理 token 统计
```

### 配置优先级

```
DEFAULTS < .config.json < frontmatter < 手输补缺
```

低优先级在前，高优先级覆盖。

## 常见问题

**Q: 工具调用没有触发？**

A: 检查格式：
- `do python` 和 `do sh` 必须顶格
- 代码必须缩进
- 必须以 `end` 结束

**Q: File 模式没有自动触发？**

A: 确保：
- 文件以双换行符 `\n\n` 结尾
- 文件格式正确（有 frontmatter 和角色标记）
- 监听进程正在运行

**Q: 如何临时换模型？**

A: 在 markdown 文件的 frontmatter 中覆写：
```yaml
---
model: gpt-4-turbo
---
```

**Q: thinking 输出太多？**

A: 在配置中设置 `log: true`，thinking 会写入 `.log` 文件而非控制台。

## 许可证

MIT

## 贡献

欢迎提交 Issue 和 Pull Request！

开发指南请参考 `CONTRIBUTING.md`。

