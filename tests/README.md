# 测试文档

## 测试覆盖

本测试套件覆盖了系统的核心模块：

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

## 运行测试

### 运行所有测试
```bash
python -m unittest discover tests -v
```

### 运行特定模块
```bash
python -m unittest tests.test_parser -v
python -m unittest tests.test_tool_executor -v
```

### 运行单个测试类
```bash
python -m unittest tests.test_parser.TestParseFile -v
python -m unittest tests.test_tool_executor.TestExecuteBlocks -v
```

### 运行单个测试方法
```bash
python -m unittest tests.test_parser.TestParseFile.test_basic_parsing -v
```

## Fixtures

测试使用的 fixture 文件位于 `tests/fixtures/` 目录：

- `sample_simple.md` - 基础对话示例
- `sample_with_file_ref.md` - 包含 @file 引用
- `context.txt` - 被引用的代码示例

## 测试设计原则

1. **无外部依赖：** 只使用 Python 标准库 `unittest`
2. **独立运行：** 测试间无依赖，可单独运行
3. **清理资源：** 使用 `setUp`/`tearDown` 管理临时文件
4. **真实场景：** 包含集成测试验证完整工作流
5. **边界覆盖：** 测试正常路径 + 错误路径 + 边界情况

## 已知限制

### markdown_parser.py
- 空 frontmatter（`---\n---`）会解析失败，因为正则要求中间有内容
- 这是当前实现的预期行为，测试已标注

### tool_executor.py
- Python 错误信息格式为 `[do python 异常: message]`，不包含异常类型名
- 不存在的文件路径在 `readfile()` 中返回 `None`

## 测试覆盖率

**总计：** 51 个测试
- `test_parser.py`: 15 个测试
- `test_tool_executor.py`: 36 个测试

**状态：** ✅ 全部通过

## 下一步

Session 6 第二阶段建议：
- 为 `stream_renderer.py` 添加测试（需要 mock LLM 流式响应）
- 为主程序 `chat.py` 添加集成测试
- 考虑添加测试覆盖率报告（`coverage.py`）
