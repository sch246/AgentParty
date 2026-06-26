# 贡献指南

感谢你对 AgentParty 的关注！这份指南帮助你了解如何为项目做出贡献。

---

## 开发环境设置

### 1. Fork 和克隆仓库

```bash
# Fork 项目到你的 GitHub 账号
# 然后克隆到本地

git clone https://github.com/YOUR_USERNAME/AgentParty.git
cd AgentParty
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置项目

```bash
# 首次运行会提示输入配置
python cli_talk.py
```

### 4. 运行测试

```bash
# 确保所有测试通过
python -m unittest discover tests -v
```

---

## 开发工作流

### 1. 创建分支

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/issue-number
```

**分支命名规范：**
- `feature/xxx` - 新功能
- `fix/xxx` - Bug 修复
- `docs/xxx` - 文档更新
- `test/xxx` - 测试相关
- `refactor/xxx` - 代码重构

### 2. 开发

遵循项目的代码风格和设计原则（见下文）。

### 3. 测试

```bash
# 运行所有测试
python -m unittest discover tests -v

# 运行特定模块测试
python -m unittest tests.test_your_module -v
```

为新功能添加测试：
- 单元测试：测试单个函数/类
- 集成测试：测试模块间交互
- 端到端测试：测试完整工作流

### 4. 提交

```bash
git add .
git commit -m "描述你的改动"
```

**提交信息规范：**

```
<类型>: <简短描述>

<详细描述（可选）>

<关联 Issue（可选）>
```

**类型：**
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `test`: 测试相关
- `refactor`: 代码重构
- `style`: 代码格式（不影响功能）
- `chore`: 构建/工具相关

**示例：**
```
feat: 添加工具超时控制

- 添加 timeout 配置项
- 工具执行超过时间自动终止
- 添加相关测试

Closes #42
```

### 5. 推送和 PR

```bash
git push origin feature/your-feature-name
```

在 GitHub 上创建 Pull Request：
- 描述改动内容
- 关联相关 Issue
- 说明测试情况

---

## 代码风格

### Python 风格

遵循 PEP 8，但有以下偏好：

**1. 行长度**
- 优先 80 字符
- 最多 100 字符

**2. 注释风格**
```python
# 单行注释：说明"为什么"而不只是"是什么"

def parse_file(text: str):
    """函数 docstring：简短描述功能
    
    参数：
    - text: 输入文本
    
    返回：
    - tuple: (config, messages)
    """
    pass
```

**3. 模块注释**
```python
# =====================================================================
# 模块名：简短描述
#
# 职责：
# 1. 职责一
# 2. 职责二
#
# 为什么独立：
# - 原因一
# - 原因二
# =====================================================================
```

**4. 类型提示**
```python
# 推荐使用类型提示
def process(data: dict) -> list:
    pass

# 复杂类型
from typing import List, Dict, Optional, Tuple

def parse(text: str) -> Tuple[Optional[dict], Optional[List[dict]]]:
    pass
```

---

## 设计原则

### 1. KISS 原则（Keep It Simple, Stupid）

- 不过度抽象
- 不引入不必要的接口/抽象类
- 简单逻辑直接内联
- 只提取明显重复的代码

**好的示例：**
```python
# 简单状态机直接内联
state = "idle"
if event == "thinking":
    if state != "thinking":
        print()  # 插入空行
        state = "thinking"
```

**避免：**
```python
# 过度抽象
class StateMachine:
    def __init__(self):
        self.transitions = {}
    
    def add_transition(self, from_state, to_state, action):
        ...
```

### 2. 单一职责

每个模块/函数只做一件事：

```python
# 好：单一职责
def parse_file(text: str) -> tuple:
    """只负责解析"""
    pass

def render_response(response, path: str):
    """只负责渲染"""
    pass

# 避免：混合职责
def parse_and_render(text: str, path: str):
    """解析和渲染混在一起"""
    pass
```

### 3. "为什么"注释

注释应该说明设计决策，而不只是重复代码：

```python
# ❌ 不好：重复代码
# 将 text 转为小写
text = text.lower()

# ✅ 好：说明为什么
# 统一大小写以支持不区分大小写的匹配
text = text.lower()

# ✅ 更好：说明设计决策
# 为什么不用正则：顶格行判断很简单，直接字符串匹配更清晰
if raw_line[0] not in (" ", "\t"):
    pass
```

### 4. 显式优于隐式

```python
# ✅ 好：显式返回
def parse_file(text: str) -> tuple:
    if error:
        return None, None
    return meta, messages

# ❌ 不好：隐式默认值
def parse_file(text: str):
    if error:
        return
    return meta, messages
```

---

## 测试规范

### 测试结构

```python
import unittest
from unittest.mock import Mock, patch

class TestYourFeature(unittest.TestCase):
    """测试 YourFeature 功能"""
    
    def setUp(self):
        """每个测试前执行"""
        # 创建临时资源
        pass
    
    def tearDown(self):
        """每个测试后执行"""
        # 清理临时资源
        pass
    
    def test_normal_case(self):
        """正常情况"""
        # Arrange（准备）
        data = "test"
        
        # Act（执行）
        result = process(data)
        
        # Assert（断言）
        self.assertEqual(result, expected)
    
    def test_edge_case(self):
        """边界情况"""
        pass
    
    def test_error_case(self):
        """错误情况"""
        pass
```

### 测试命名

- 测试类：`TestXxx`
- 测试方法：`test_xxx_yyy`
- 使用描述性名称

### Mock 使用

```python
# Mock LLM 响应
with patch('module.stream_events') as mock_stream:
    mock_stream.return_value = [
        ("content", "test"),
    ]
    result = function()

# Mock 文件系统
import tempfile
temp = tempfile.NamedTemporaryFile(delete=False)
try:
    # 使用 temp.name
    pass
finally:
    os.unlink(temp.name)
```

### 测试覆盖

新功能需要包含：
- ✅ 单元测试（函数/类级别）
- ✅ 集成测试（模块交互）
- ✅ 正常路径
- ✅ 错误路径
- ✅ 边界情况

---

## 文档规范

### README 更新

添加新功能时更新：
- 功能列表
- 使用示例
- 配置项说明

### CHANGELOG 更新

在 `[未发布]` 部分记录：

```markdown
## [未发布]

### 新增
- 新功能描述

### 改进
- 改进说明

### 修复
- Bug 修复说明
```

### 代码注释

```python
# 模块级别：说明职责和设计决策
# 函数级别：docstring 说明功能和参数
# 行级别：说明"为什么"而非"是什么"
```

---

## Pull Request 规范

### PR 标题

```
<类型>: <简短描述>
```

示例：
- `feat: 添加工具超时控制`
- `fix: 修复 CLI 工具调用循环问题`
- `docs: 更新 README 文档`

### PR 描述模板

```markdown
## 改动说明
简要描述这个 PR 做了什么。

## 改动类型
- [ ] 新功能
- [ ] Bug 修复
- [ ] 文档更新
- [ ] 代码重构
- [ ] 测试相关

## 测试
- [ ] 添加了新测试
- [ ] 所有测试通过
- [ ] 手动测试通过

## 相关 Issue
Closes #123

## 检查清单
- [ ] 代码遵循项目风格
- [ ] 添加了必要的注释
- [ ] 更新了相关文档
- [ ] 添加了测试
- [ ] 所有测试通过
```

### Review 流程

1. 提交 PR 后等待 review
2. 根据反馈修改代码
3. 推送更新到同一分支
4. 获得批准后会被合并

---

## 常见问题

### Q: 如何添加新的配置项？

1. 在 `config.py` 的 `DEFAULTS` 中添加默认值
2. 在 `README.md` 中文档化
3. 添加测试验证配置加载

### Q: 如何添加新的工具类型？

1. 在 `tool_executor.py` 中扩展 `parse_do_blocks()`
2. 添加执行逻辑
3. 更新 `tools.md` 文档
4. 添加测试

### Q: 如何调试测试失败？

```bash
# 运行单个测试查看详细输出
python -m unittest tests.test_module.TestClass.test_method -v

# 添加 print 调试（测试通过时不显示）
import sys
print("Debug info", file=sys.stderr)
```

### Q: 代码风格检查工具？

目前项目没有强制的 linter，但建议：
- 使用 IDE 的 PEP 8 检查
- 遵循项目现有风格
- 注重代码可读性

---

## 行为准则

### 我们的承诺

为了营造开放和友好的环境，我们承诺：
- 尊重不同的观点和经验
- 优雅地接受建设性批评
- 专注于对社区最有利的事情
- 对其他社区成员表示同理心

### 不可接受的行为

- 使用性化语言或图像
- 人身攻击或侮辱性评论
- 公开或私下骚扰
- 未经许可发布他人的私人信息
- 其他不道德或不专业的行为

---

## 获取帮助

- 💬 提出 Issue：遇到问题或有建议
- 📧 联系维护者：通过 GitHub
- 📖 阅读文档：`README.md`、`tests/README.md`

---

## 致谢

感谢所有贡献者！你的努力让这个项目变得更好。

---

**记住：没有愚蠢的问题，只有未被回答的问题。欢迎提问！**
