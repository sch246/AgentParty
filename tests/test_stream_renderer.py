# =====================================================================
# 流式渲染器测试
#
# 测试范围：
# 1. write_response: 流式消费 LLM 响应
# 2. write_anchor: 写入用户锚点
# 3. 缩进处理逻辑
# 4. thinking/usage 输出逻辑
# =====================================================================
import unittest
from unittest.mock import Mock, patch, call
import tempfile
import os

from src.stream_renderer import write_response, write_anchor
from src.format_schema import ROLE_MARKER, INDENT


class TestWriteResponse(unittest.TestCase):
    """测试流式写入响应"""

    def setUp(self):
        """创建临时文件"""
        self.temp_md = tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8')
        self.temp_md.close()
        self.md_path = self.temp_md.name

        self.temp_log = tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8')
        self.temp_log.close()
        self.log_path = self.temp_log.name

    def tearDown(self):
        """清理临时文件"""
        os.unlink(self.md_path)
        os.unlink(self.log_path)

    def test_simple_content(self):
        """简单内容写入"""
        mock_response = Mock()

        with patch('src.stream_renderer.stream_events') as mock_stream:
            mock_stream.return_value = [
                ("role", "assistant"),
                ("content", "第一行\n第二行"),
            ]

            raw = write_response(mock_response, self.md_path, "AI", self.log_path, enable_log=True)

            # 验证返回的原始文本
            self.assertEqual(raw, "第一行\n第二行")

            # 验证文件内容（带缩进）
            with open(self.md_path, 'r', encoding='utf-8') as f:
                content = f.read()

            self.assertIn(f"{ROLE_MARKER} AI", content)
            self.assertIn(f"{INDENT}第一行", content)
            self.assertIn(f"{INDENT}第二行", content)

    def test_indentation_preserved(self):
        """缩进正确处理"""
        mock_response = Mock()

        with patch('src.stream_renderer.stream_events') as mock_stream:
            mock_stream.return_value = [
                ("content", "def foo():\n    return 42"),
            ]

            raw = write_response(mock_response, self.md_path, "AI", self.log_path, enable_log=True)

            # 原始文本无额外缩进
            self.assertEqual(raw, "def foo():\n    return 42")

            # 文件中每行都有 4 空格缩进
            with open(self.md_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 第一行是角色标记
            self.assertTrue(lines[0].startswith(ROLE_MARKER))
            # 后续行都有缩进
            self.assertEqual(lines[1], f"{INDENT}def foo():\n")
            self.assertEqual(lines[2], f"{INDENT}    return 42")  # 原有缩进保留

    def test_thinking_to_log(self):
        """thinking 写入 log"""
        mock_response = Mock()

        with patch('src.stream_renderer.stream_events') as mock_stream:
            mock_stream.return_value = [
                ("thinking", "思考中..."),
                ("content", "回复"),
            ]

            raw = write_response(mock_response, self.md_path, "AI", self.log_path, enable_log=True)

            # thinking 不在原始文本中
            self.assertEqual(raw, "回复")

            # thinking 在 log 中
            with open(self.log_path, 'r', encoding='utf-8') as f:
                log_content = f.read()
            self.assertIn("思考中...", log_content)

            # thinking 不在 md 中
            with open(self.md_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            self.assertNotIn("思考中", md_content)

    def test_thinking_to_console(self):
        """thinking 输出到控制台（enable_log=False）"""
        mock_response = Mock()

        with patch('src.stream_renderer.stream_events') as mock_stream:
            mock_stream.return_value = [
                ("thinking", "思考中..."),
                ("content", "回复"),
            ]

            with patch('src.stream_renderer.terminal_color_print') as mock_print:
                raw = write_response(mock_response, self.md_path, "AI", self.log_path, enable_log=False)

                # 验证 thinking 被打印
                mock_print.assert_any_call("思考中...", "yellow", end="")

    def test_usage_info(self):
        """usage 信息写入"""
        mock_response = Mock()

        with patch('src.stream_renderer.stream_events') as mock_stream:
            mock_stream.return_value = [
                ("content", "回复"),
                ("usage", {
                    "prompt": 100,
                    "completion": 50,
                    "total": 150,
                }),
            ]

            raw = write_response(mock_response, self.md_path, "AI", self.log_path, enable_log=True)

            # usage 不在原始文本中
            self.assertEqual(raw, "回复")

            # usage 在 log 中
            with open(self.log_path, 'r', encoding='utf-8') as f:
                log_content = f.read()
            self.assertIn("输入: 100", log_content)
            self.assertIn("输出: 50", log_content)

    def test_incomplete_line_flushed(self):
        """没有换行符的结尾被 flush"""
        mock_response = Mock()

        with patch('src.stream_renderer.stream_events') as mock_stream:
            mock_stream.return_value = [
                ("content", "没有换行符"),
            ]

            raw = write_response(mock_response, self.md_path, "AI", self.log_path, enable_log=True)

            self.assertEqual(raw, "没有换行符")

            # 文件中有缩进，但没有额外换行
            with open(self.md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertIn(f"{INDENT}没有换行符", content)

    def test_multiple_chunks(self):
        """多个 content chunk 合并"""
        mock_response = Mock()

        with patch('src.stream_renderer.stream_events') as mock_stream:
            mock_stream.return_value = [
                ("content", "第"),
                ("content", "一"),
                ("content", "行\n"),
                ("content", "第二行"),
            ]

            raw = write_response(mock_response, self.md_path, "AI", self.log_path, enable_log=True)

            self.assertEqual(raw, "第一行\n第二行")

            with open(self.md_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 验证分行正确
            self.assertIn(f"{INDENT}第一行", lines[1])
            self.assertIn(f"{INDENT}第二行", lines[2])


class TestWriteAnchor(unittest.TestCase):
    """测试锚点写入"""

    def setUp(self):
        """创建临时文件"""
        self.temp_md = tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8')
        self.temp_md.close()
        self.md_path = self.temp_md.name

    def tearDown(self):
        """清理临时文件"""
        os.unlink(self.md_path)

    def test_anchor_format(self):
        """锚点格式正确"""
        write_anchor(self.md_path)

        with open(self.md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 验证格式：\n\n## user\n
        self.assertIn(f"\n\n{ROLE_MARKER} user\n{INDENT}", content)

    def test_anchor_after_content(self):
        """在已有内容后写入锚点"""
        # 先写入一些内容
        with open(self.md_path, 'w', encoding='utf-8') as f:
            f.write(f"{ROLE_MARKER} AI\n{INDENT}回复内容")

        # 写入锚点
        write_anchor(self.md_path)

        with open(self.md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 验证锚点在末尾
        self.assertTrue(content.endswith(f"\n\n{ROLE_MARKER} user\n{INDENT}"))


class TestIndentLogic(unittest.TestCase):
    """测试缩进处理逻辑"""

    def setUp(self):
        """创建临时文件"""
        self.temp_md = tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8')
        self.temp_md.close()
        self.md_path = self.temp_md.name

        self.temp_log = tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8')
        self.temp_log.close()
        self.log_path = self.temp_log.name

    def tearDown(self):
        """清理临时文件"""
        os.unlink(self.md_path)
        os.unlink(self.log_path)

    def test_code_block_indentation(self):
        """代码块缩进保留"""
        mock_response = Mock()

        with patch('src.stream_renderer.stream_events') as mock_stream:
            mock_stream.return_value = [
                ("content", "```python\ndef foo():\n    return 42\n```"),
            ]

            raw = write_response(mock_response, self.md_path, "AI", self.log_path, enable_log=True)

            with open(self.md_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 每行都有基础缩进，内部缩进保留
            for line in lines[1:]:  # 跳过角色标记
                self.assertTrue(line.startswith(INDENT))

    def test_empty_lines(self):
        """空行处理"""
        mock_response = Mock()

        with patch('src.stream_renderer.stream_events') as mock_stream:
            mock_stream.return_value = [
                ("content", "第一段\n\n第二段"),
            ]

            raw = write_response(mock_response, self.md_path, "AI", self.log_path, enable_log=True)

            with open(self.md_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 空行也有缩进
            lines = content.split('\n')
            for line in lines[1:]:  # 跳过角色标记
                if line:  # 非空行
                    self.assertTrue(line.startswith(INDENT))


if __name__ == "__main__":
    unittest.main()
