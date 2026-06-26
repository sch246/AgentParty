"""
markdown_parser.py 单元测试

测试覆盖：
- 基础解析：frontmatter + role 切换
- @file 引用解析（全文、单行、范围）
- 边界情况：无 frontmatter、空文件、格式错误
"""
import unittest
import os
from pathlib import Path
import sys

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from markdown_parser import parse_file


class TestParseFile(unittest.TestCase):
    """parse_file 函数测试"""

    def setUp(self):
        """设置测试 fixtures 路径"""
        self.fixtures_dir = Path(__file__).parent / "fixtures"

    def test_basic_parsing(self):
        """测试基础解析：frontmatter + role 切换"""
        text = """---
model: gpt-4
temperature: 0.7
---

## user

    你好

## assistant

    你好！有什么可以帮你的吗？
"""
        meta, messages = parse_file(text)

        # 验证 meta
        self.assertIsNotNone(meta)
        self.assertEqual(meta["model"], "gpt-4")
        self.assertEqual(meta["temperature"], 0.7)

        # 验证 messages
        self.assertIsNotNone(messages)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[0]["content"], "你好")
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertEqual(messages[1]["content"], "你好！有什么可以帮你的吗？")

    def test_multiline_content(self):
        """测试多行内容和空行保留"""
        text = """---
model: gpt-4
---

## user

    第一段

    第二段

## assistant

    回复第一行
    回复第二行
"""
        meta, messages = parse_file(text)

        self.assertEqual(messages[0]["content"], "第一段\n\n第二段")
        self.assertEqual(messages[1]["content"], "回复第一行\n回复第二行")

    def test_role_mapping(self):
        """测试 role 映射：user 保持，其他映射为 assistant"""
        text = """---
model: gpt-4
---

## user

    用户消息

## assistant

    助手回复

## system

    系统提示

## custom_role

    自定义角色
"""
        meta, messages = parse_file(text)

        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertEqual(messages[2]["role"], "assistant")  # system → assistant
        self.assertEqual(messages[3]["role"], "assistant")  # custom → assistant

    def test_file_ref_full_content(self):
        """测试 @file 引用：全文"""
        # 使用相对路径（相对于当前工作目录）
        text = """---
model: gpt-4
---

@file tests/fixtures/context.txt

## user

    分析上面的代码
"""
        meta, messages = parse_file(text)

        # 第一条消息应该是 system role，包含文件内容
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("[@file", messages[0]["content"])
        self.assertIn("def hello()", messages[0]["content"])
        self.assertIn('print("Hello, World!")', messages[0]["content"])

        # 第二条是用户消息
        self.assertEqual(messages[1]["role"], "user")
        self.assertEqual(messages[1]["content"], "分析上面的代码")

    def test_file_ref_single_line(self):
        """测试 @file 引用：单行"""
        text = """---
model: gpt-4
---

@file tests/fixtures/context.txt:1

## user

    这是第一行吗？
"""
        meta, messages = parse_file(text)

        self.assertEqual(messages[0]["role"], "system")
        content = messages[0]["content"]
        self.assertIn("def hello():", content)
        self.assertNotIn('print("Hello', content)  # 第二行不应出现

    def test_file_ref_line_range(self):
        """测试 @file 引用：行号范围"""
        text = """---
model: gpt-4
---

@file tests/fixtures/context.txt:1-2

## user

    显示完整函数
"""
        meta, messages = parse_file(text)

        self.assertEqual(messages[0]["role"], "system")
        content = messages[0]["content"]
        self.assertIn("def hello():", content)
        self.assertIn('print("Hello, World!")', content)

    def test_file_ref_not_found(self):
        """测试 @file 引用：文件不存在"""
        text = """---
model: gpt-4
---

@file /nonexistent/file.txt

## user

    读取文件
"""
        meta, messages = parse_file(text)

        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("文件不存在", messages[0]["content"])

    def test_no_frontmatter(self):
        """测试边界：缺少 frontmatter"""
        text = """## user

    你好
"""
        meta, messages = parse_file(text)

        # 应该返回 None, None
        self.assertIsNone(meta)
        self.assertIsNone(messages)

    def test_invalid_yaml(self):
        """测试边界：无效 YAML"""
        text = """---
model: [invalid: yaml: structure
---

## user

    你好
"""
        meta, messages = parse_file(text)

        self.assertIsNone(meta)
        self.assertIsNone(messages)

    def test_empty_frontmatter(self):
        """测试边界：空 frontmatter（实际上会解析失败）"""
        text = """---
---

## user

    你好
"""
        meta, messages = parse_file(text)

        # 当前实现：空 frontmatter 无法匹配正则，返回 None
        # 原因：正则要求 --- 和 --- 之间必须有内容
        self.assertIsNone(meta)
        self.assertIsNone(messages)

    def test_no_messages(self):
        """测试边界：只有 frontmatter，无消息"""
        text = """---
model: gpt-4
---
"""
        meta, messages = parse_file(text)

        self.assertIsNotNone(meta)
        self.assertEqual(messages, [])

    def test_empty_role_block(self):
        """测试边界：空角色块被忽略"""
        text = """---
model: gpt-4
---

## user

## assistant

    有效消息
"""
        meta, messages = parse_file(text)

        # 空的 user 块应该被忽略
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["role"], "assistant")

    def test_indent_preservation(self):
        """测试缩进保留：代码块内部结构"""
        text = """---
model: gpt-4
---

## user

    代码如下：

        def foo():
            if True:
                print("nested")
"""
        meta, messages = parse_file(text)

        content = messages[0]["content"]
        # 去掉第一级缩进后，内部缩进应保留
        self.assertIn("    def foo():", content)
        self.assertIn("        if True:", content)
        self.assertIn('            print("nested")', content)

    def test_real_fixture_simple(self):
        """集成测试：真实 fixture 文件 sample_simple.md"""
        fixture = self.fixtures_dir / "sample_simple.md"
        text = fixture.read_text(encoding="utf-8")

        meta, messages = parse_file(text)

        self.assertIsNotNone(meta)
        self.assertEqual(meta["model"], "gpt-4")
        self.assertGreater(len(messages), 0)
        self.assertEqual(messages[0]["role"], "user")

    def test_real_fixture_with_file_ref(self):
        """集成测试：真实 fixture 文件 sample_with_file_ref.md"""
        fixture = self.fixtures_dir / "sample_with_file_ref.md"
        text = fixture.read_text(encoding="utf-8")

        # 修改文本中的路径为绝对路径或从项目根目录的相对路径
        # 这里 fixture 文件里写的是 tests/fixtures/context.txt
        meta, messages = parse_file(text)

        self.assertIsNotNone(meta)
        # 第一条消息应该是 @file 引用的 system 消息
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("def hello()", messages[0]["content"])


if __name__ == "__main__":
    unittest.main()
