# 测试文档

## 测试覆盖

本测试套件覆盖了系统的核心模块和集成场景。

### 测试统计

**总计：88 个测试** ✅ 全部通过

| 模块 | 测试数 | 状态 |
|------|--------|------|
| `test_parser.py` | 15 | ✅ |
| `test_tool_executor.py` | 36 | ✅ |
| `test_cli_tools.py` | 16 | ✅ |
| `test_stream_renderer.py` | 14 | ✅ |
| `test_integration.py` | 7 | ✅ |

---

## 测试模块详解

### 1. `test_parser.py` - Markdown 解析器测试

**覆盖模块：** `markdown_parser.py`

**测试范围：**
- ✅ 基础解析：frontmatter + role 切换
- ✅ 多行内容和空行保留
- ✅ Role 映射（user → user，其他 → assistant）
- ✅ @file 引用解析（全文、单行、行号范围）
- ✅ 缩进保留（代码块内部结构）
- ✅ 边界情况：
  - 无 frontmatter
  - 无效 YAML
  - 空 frontmatter（会解析失败）
  - 空角色块
  - 只有 frontmatter 无消息
  - 文件不存在
- ✅ 集成测试：真实 fixture 文件

**测试数量：** 15 个

---

### 2. `test_tool_executor.py` - 工具执行器测试

**覆盖模块：** `tool_executor.py`

**测试范围：**

#### parse_do_blocks 解析
- ✅ 单个 python/sh 块
- ✅ 多个 do 块
- ✅ 缩进去除（一级缩进，内部保留）
- ✅ 空块
- ✅ 无 do 块

#### 沙盒执行
- ✅ Python 执行：
  - print 输出捕获
  - 命名空间注入（messages/readfile）
  - 语法错误处理
  - 运行时错误处理
  - 错误前的部分输出
- ✅ Shell 执行：
  - echo 命令
  - stderr 捕获
  - 命令失败
  - 不存在的命令

#### readfile() 注入函数
- ✅ 读取文件
- ✅ 读取目录（列表）
- ✅ 不存在的路径

#### execute_blocks 集成
- ✅ 单个/多个块串行执行
- ✅ 输出追加到 log
- ✅ 行号范围返回
- ✅ messages 可访问
- ✅ extra_ns 扩展命名空间
- ✅ 错误处理

#### 完整工作流
- ✅ 解析 → 执行 → 验证

**测试数量：** 36 个

---

### 3. `test_cli_tools.py` - CLI 工具调用测试

**覆盖模块：** `cli_talk.py`

**测试范围：**

#### 工具检测
- ✅ 检测 python 块
- ✅ 检测 sh 块
- ✅ 无 do 块
- ✅ do 块在中间
- ✅ 多个 do 块

#### 工具解析
- ✅ 单个 Python/Shell 块
- ✅ 多个块
- ✅ 前后有文字
- ✅ 缩进正确去除

#### CLI 流式消费
- ✅ 简单内容
- ✅ thinking → content 状态切换
- ✅ usage 信息处理
- ✅ 错误处理

#### 集成
- ✅ tools.md 加载逻辑
- ✅ 工具执行循环

**测试数量：** 16 个

---

### 4. `test_stream_renderer.py` - 流式渲染器测试

**覆盖模块：** `stream_renderer.py`

**测试范围：**

#### write_response 流式写入
- ✅ 简单内容写入
- ✅ 缩进正确处理
- ✅ thinking 写入 log
- ✅ thinking 输出到控制台
- ✅ usage 信息
- ✅ 不完整行 flush
- ✅ 多个 chunk 合并

#### write_anchor 锚点写入
- ✅ 锚点格式正确
- ✅ 在已有内容后写入

#### 缩进逻辑
- ✅ 代码块缩进保留
- ✅ 空行处理

**测试数量：** 14 个

---

### 5. `test_integration.py` - 集成测试

**覆盖模块：** 端到端工作流

**测试范围：**

#### File 模式工作流
- ✅ 解析 → 渲染流程
- ✅ 工具执行工作流
- ✅ 多轮对话

#### CLI 模式工作流
- ✅ CLI 工具调用循环

#### 配置集成
- ✅ 配置加载
- ✅ frontmatter 覆盖

#### 错误恢复
- ✅ 工具执行错误
- ✅ 无效 markdown
- ✅ 流式响应错误

#### 端到端
- ✅ File 模式完整周期

**测试数量：** 7 个

---

## 运行测试

### 运行所有测试
```bash
python -m unittest discover tests -v
```

### 运行特定模块
```bash
python -m unittest tests.test_parser -v
python -m unittest tests.test_tool_executor -v
python -m unittest tests.test_cli_tools -v
python -m unittest tests.test_stream_renderer -v
python -m unittest tests.test_integration -v
```

### 运行单个测试类
```bash
python -m unittest tests.test_parser.TestParseFile -v
python -m unittest tests.test_tool_executor.TestExecuteBlocks -v
python -m unittest tests.test_cli_tools.TestConsumeToTerminal -v
python -m unittest tests.test_stream_renderer.TestWriteResponse -v
python -m unittest tests.test_integration.TestFileWorkflow -v
```

### 运行单个测试方法
```bash
python -m unittest tests.test_parser.TestParseFile.test_basic_parsing -v
```

---

## Fixtures

测试使用的 fixture 文件位于 `tests/fixtures/` 目录：

- `sample_simple.md` - 基础对话示例
- `sample_with_file_ref.md` - 包含 @file 引用
- `context.txt` - 被引用的代码示例

---

## 测试设计原则

### 1. 无外部依赖
- 只使用 Python 标准库 `unittest`
- 使用 `unittest.mock` 模拟外部调用
- 不依赖网络或真实 LLM API

### 2. 独立运行
- 测试间无依赖，可单独运行
- 使用 `setUp`/`tearDown` 管理临时文件
- 每个测试独立验证一个场景

### 3. 真实场景
- 包含集成测试验证完整工作流
- 使用真实的文件格式和数据结构
- 验证错误路径和边界情况

### 4. Mock 策略
- **Mock LLM 响应**：使用 `patch('core.stream_events')` 模拟流式事件
- **Mock 文件系统**：使用临时文件，测试后清理
- **Mock 配置**：使用临时配置文件，避免污染全局配置

### 5. 边界覆盖
- 测试正常路径
- 测试错误路径
- 测试边界情况（空输入、特殊字符、格式错误等）

---

## Mock 示例

### Mock LLM 流式响应

```python
from unittest.mock import Mock, patch

mock_response = Mock()
with patch('cli_talk.stream_events') as mock_stream:
    mock_stream.return_value = [
        ("role", "assistant"),
        ("thinking", "思考中..."),
        ("content", "回复内容"),
        ("usage", {"prompt": 100, "completion": 50, "total": 150}),
    ]
    
    result = consume_to_terminal(mock_response, "test-model")
```

### Mock 文件系统

```python
import tempfile
import os

# 创建临时文件
temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8')
temp_file.write("测试内容")
temp_file.close()

try:
    # 使用临时文件
    with open(temp_file.name, 'r', encoding='utf-8') as f:
        content = f.read()
finally:
    # 清理
    os.unlink(temp_file.name)
```

---

## 已知限制

### markdown_parser.py
- 空 frontmatter（`---\n---`）会解析失败，因为正则要求中间有内容
- 这是当前实现的预期行为，测试已标注

### tool_executor.py
- Python 错误信息格式为 `[do python 异常: message]`，不包含异常类型名
- 不存在的文件路径在 `readfile()` 中返回 `None`

### 测试覆盖
- 流式响应的实时渲染效果（打字机效果）未完全测试
- 文件监听触发机制（watchdog）未测试（依赖文件系统事件）
- 真实 LLM API 集成未测试（使用 mock）

---

## 测试覆盖率

**总计：** 88 个测试
- `test_parser.py`: 15 个测试 ✅
- `test_tool_executor.py`: 36 个测试 ✅
- `test_cli_tools.py`: 16 个测试 ✅
- `test_stream_renderer.py`: 14 个测试 ✅
- `test_integration.py`: 7 个测试 ✅

**状态：** ✅ 全部通过

---

## 未来改进

### 短期
- [ ] 添加代码覆盖率报告（`coverage.py`）
- [ ] 性能基准测试
- [ ] 更多边界情况测试

### 中期
- [ ] 添加 E2E 测试（真实文件监听）
- [ ] 添加压力测试（大文件、长对话）
- [ ] 并发测试（多文件同时触发）

### 长期
- [ ] 持续集成（CI/CD）
- [ ] 自动化测试报告
- [ ] 测试覆盖率目标：90%+

---

## 贡献指南

添加新测试时请遵循：

1. **命名规范**：
   - 测试类：`TestXxx`
   - 测试方法：`test_xxx_yyy`
   - 使用描述性名称

2. **文档注释**：
   - 每个测试类添加 docstring
   - 每个测试方法添加简短描述

3. **独立性**：
   - 不依赖其他测试
   - 使用 `setUp`/`tearDown` 管理状态
   - 清理临时资源

4. **断言清晰**：
   - 使用具体的断言方法（`assertEqual` 而非 `assertTrue`）
   - 添加失败消息帮助调试

5. **覆盖全面**：
   - 正常路径
   - 错误路径
   - 边界情况

参见项目根目录的 `CONTRIBUTING.md` 了解更多开发规范。

