# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- **工具参数系统**：支持带参数的工具调用
  - 语法：`do <type> key=value ...`（如 `do py timeout=60`）
  - Python 支持 `timeout` 参数：防止长时间运行
  - Shell 支持 `timeout` 和 `cwd` 参数：控制超时和工作目录
  - 向后兼容：无参数时保持原有行为
  - 日志显示参数：`--- do py timeout=60 ---`
  - 新增测试：参数解析、超时功能、cwd 功能

### Changed
- **工具调用语法优化**：`do python` → `do py`
  - 新语法：`do py` / `do sh`（更简洁、对称）
  - 向后兼容：仍支持 `do python`（自动规范化为 `py`）
  - 内部统一使用 `py` 类型标识符
  - 错误信息更新为 `[do py 异常: ...]`

### Added
- **配置实时读取**：每次处理消息时读取最新配置，无需重启程序
  - File 模式：每次处理用户消息或工具调用时重新读取 `.config.json` 和 frontmatter
  - CLI 模式：每轮对话前重新读取 `.config.json`
  - 修改 `debug`、`log`、`max_tool_rounds` 等配置立即生效
  - 性能影响可忽略（读取 JSON <1ms，AI 调用频率低）

### Changed
- `FileHandler` 不再在初始化时缓存配置
- `_debug()` 方法实时读取 `debug` 配置

### Technical
- 移除 `FileHandler.__init__()` 的 `config` 参数
- `_process_once()` 每次调用时通过 `resolve_config(meta)` 读取配置
- `_call_llm_with_retry()` 接收 `config` 参数而非使用缓存
- `handler()` 函数简化，不再预加载配置

## [0.1.0] - 2026-06-27

### Added
- CLI 模式：终端交互式聊天
- File 模式：监听 markdown 文件自动触发
- 工具调用：Python/Shell 代码执行
- 配置系统：全局配置 + frontmatter 覆写
- @file 引用系统：避免重复粘贴
- 错误重试机制：网络问题自动重试
- 虚拟缓冲区：零预设中断检测
- 完整测试套件：88 个测试覆盖核心功能
