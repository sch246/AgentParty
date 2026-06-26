# 变更日志

所有重要的项目变更都记录在这个文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## [未发布]

### 新增
- 完整的测试套件（88 个测试）
- 集成测试覆盖完整工作流
- CLI 工具调用测试
- 流式渲染器测试

### 改进
- 更新 README 文档，添加详细使用说明
- 创建 CHANGELOG 记录项目历史
- 更新测试文档

---

## [2026-06-27] - CLI 工具调用支持

### 新增
- **工具执行支持**：AI 可以在回复中使用 `do python` / `do sh` 块
- **Python 沙盒**：注入 `messages` 和 `readfile()` 函数
- **Shell 执行**：直接执行系统命令
- **工具循环**：支持多轮工具调用（可配置上限）
- **工具说明文档**：`tools.md` 自动加载为系统提示

### 实现细节
- `tool_executor.py`：工具解析和沙盒执行
  - `parse_do_blocks()`: 提取 do 块
  - `execute_blocks()`: 串行执行并输出到 log
  - `has_do_block()`: 快速检测是否有工具调用
- CLI 模式工具调用循环（`cli_talk.py`）
- File 模式工具回引机制（通过 `@file` 引用 log）

### 配置项
- `max_tool_rounds`: 单次对话最多工具调用次数（默认 10）

---

## [2026-06-27] - Session 4: CLI 模式统一

### 改进
- **统一流式处理架构**：CLI 和 File 模式都直接消费 `stream_events`
- **提取 `meta_output()` 函数**：统一 thinking/usage/role 的元信息输出
- **废弃 `pipeline.py`**：简化架构，移除额外抽象层
- **内联状态机**：CLI 模式的 UI 状态机逻辑内联到 `consume_to_terminal()`

### 变更
- `core.py`: 新增 `meta_output()` 函数（+23 行）
- `cli_talk.py`: 重写 `consume_to_terminal()`，从 40 行增至 60 行
- `pipeline.py`: 标记为废弃，添加迁移说明

### 设计原则
- KISS 原则：不引入接口/抽象类
- 架构统一：两种模式都直接消费 stream_events
- 保持功能：51 个测试全部通过

### 详细文档
参见 `CLI_UNIFICATION_SUMMARY.md`

---

## [2026-06-27] - Session 1/2/6: 模块化重构

### 新增
- **模块化架构**：拆分为独立的功能模块
  - `markdown_parser.py`: Markdown 解析
  - `stream_renderer.py`: 流式渲染
  - `chat_formatter.py`: 对话格式化
  - `format_schema.py`: 格式常量
- **完整测试覆盖**：
  - `test_parser.py`: 15 个测试
  - `test_tool_executor.py`: 36 个测试
- **错误处理改进**：
  - 网络错误重试
  - 指数退避策略
  - 详细错误日志

### 改进
- 配置系统：`config.py` 支持优先级合并
- 核心功能：`core.py` 提供统一的 LLM 请求和流式事件
- 文件监听：`watch_file.py` 基于 watchdog

### 配置项
- `log`: thinking 输出到 log 文件（默认 false）
- `watch_path`: 监听目录（默认当前目录）
- `debug`: 打印系统运行日志（默认 false）
- `max_retries`: 最大重试次数（默认 3）
- `retry_delay`: 重试间隔秒数（默认 2.0）

---

## [初始版本] - 基础功能

### 新增
- **CLI 模式**：终端交互式聊天
  - 彩色输出
  - 打字机效果
  - 流式响应
- **File 模式**：Markdown 文件聊天
  - 文件监听（watchdog）
  - 自动触发（双换行符）
  - 回复追加
- **配置系统**：
  - `.config.json` 存储
  - Frontmatter 覆写
  - 交互式补全
- **@file 引用**：
  - 全文引用
  - 单行引用
  - 行号范围引用

### 技术栈
- Python 3.8+
- OpenAI SDK
- watchdog (文件监听)
- PyYAML (配置解析)

---

## 开发约定

### 版本号规则
采用语义化版本：`主版本.次版本.修订号`

- **主版本**：不兼容的 API 变更
- **次版本**：向后兼容的功能新增
- **修订号**：向后兼容的问题修正

### 变更类型
- **新增** (Added)：新功能
- **改进** (Changed)：现有功能的变更
- **废弃** (Deprecated)：即将移除的功能
- **移除** (Removed)：已移除的功能
- **修复** (Fixed)：错误修复
- **安全** (Security)：安全相关的变更

---

## 路线图

### 计划中
- [ ] 流式响应测试覆盖
- [ ] 性能基准测试
- [ ] 多文件上下文管理
- [ ] 工具超时控制
- [ ] 更丰富的工具沙盒（网络、文件系统权限）

### 考虑中
- [ ] GUI 模式
- [ ] 插件系统
- [ ] 多模型对话
- [ ] 上下文压缩
- [ ] 向量数据库集成
