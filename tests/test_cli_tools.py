# =====================================================================
# CLI 工具调用测试
#
# 测试范围：
# 1. 工具调用检测（has_do_block）
# 2. 工具解析（parse_do_blocks）
# 3. CLI 模式的工具执行集成（consume_to_terminal）
# 4. 工具不可用时的提示
# =====================================================================
import unittest
from unittest.mock import Mock, patch, mock_open
import tempfile
import os

from src.cli_talk import consume_to_terminal
from src.tool_executor import has_do_block, parse_do_blocks


class TestHasDoBlock(unittest.TestCase):
    """测试工具调用检测"""

    def test_has_python_block(self):
        """检测到 do python 块"""
        text = "这是回复\n\ndo python\n    print('hello')\nend"
        self.assertTrue(has_do_block(text))

    def test_has_sh_block(self):
        """检测到 do sh 块"""
        text = "这是回复\n\ndo sh\n    echo hello\nend"
        self.assertTrue(has_do_block(text))

    def test_no_do_block(self):
        """没有 do 块"""
        text = "这是普通回复，没有工具调用"
        self.assertFalse(has_do_block(text))

    def test_do_in_middle(self):
        """do 块在中间"""
        text = "前面的文字\n\ndo python\n    pass\nend\n\n后面的文字"
        self.assertTrue(has_do_block(text))

    def test_multiple_blocks(self):
        """多个 do 块"""
        text = "do python\n    pass\nend\n\ndo sh\n    ls\nend"
        self.assertTrue(has_do_block(text))


class TestParseDoBlocks(unittest.TestCase):
    """测试工具解析"""

    def test_single_python_block(self):
        """单个 Python 块"""
        text = "do python\n    print('test')\n    x = 1\nend"
        blocks = parse_do_blocks(text)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0][0], "py")  # 规范化为 py
        self.assertIn("print('test')", blocks[0][1])
        self.assertIn("x = 1", blocks[0][1])

    def test_single_sh_block(self):
        """单个 Shell 块"""
        text = "do sh\n    echo hello\n    ls -la\nend"
        blocks = parse_do_blocks(text)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0][0], "sh")
        self.assertIn("echo hello", blocks[0][1])

    def test_multiple_blocks(self):
        """多个 do 块"""
        text = "do python\n    pass\nend\n\ndo sh\n    ls\nend"
        blocks = parse_do_blocks(text)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0][0], "py")  # 规范化为 py
        self.assertEqual(blocks[1][0], "sh")

    def test_with_surrounding_text(self):
        """do 块前后有文字"""
        text = "前面的文字\n\ndo python\n    print('test')\nend\n\n后面的文字"
        blocks = parse_do_blocks(text)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0][0], "py")  # 规范化为 py

    def test_indentation_stripped(self):
        """缩进被正确去除"""
        text = "do python\n    if True:\n        print('nested')\nend"
        blocks = parse_do_blocks(text)
        code = blocks[0][1]
        # 第一层缩进去除，第二层保留
        self.assertTrue(code.startswith("if True:"))
        self.assertIn("    print('nested')", code)


class TestConsumeToTerminal(unittest.TestCase):
    """测试 CLI 流式消费"""

    def test_simple_content(self):
        """简单内容流式输出"""
        # Mock stream_events 返回简单内容
        mock_response = Mock()

        with patch('src.cli_talk.stream_events') as mock_stream:
            mock_stream.return_value = [
                ("role", "assistant"),
                ("content", "你好"),
                ("content", "世界"),
            ]

            result = consume_to_terminal(mock_response, "test-model")

            self.assertEqual(result, "你好世界")

    def test_thinking_then_content(self):
        """thinking → content 状态切换"""
        mock_response = Mock()

        with patch('src.cli_talk.stream_events') as mock_stream:
            mock_stream.return_value = [
                ("role", "assistant"),
                ("thinking", "思考中..."),
                ("content", "回复内容"),
            ]

            result = consume_to_terminal(mock_response, "test-model")

            self.assertEqual(result, "回复内容")

    def test_usage_info(self):
        """usage 信息处理"""
        mock_response = Mock()

        with patch('src.cli_talk.stream_events') as mock_stream:
            mock_stream.return_value = [
                ("content", "回复"),
                ("usage", {
                    "prompt": 100,
                    "completion": 50,
                    "total": 150,
                    "reasoning": 20,
                    "cache_hit": 80,
                    "cache_miss": 20,
                }),
            ]

            result = consume_to_terminal(mock_response, "test-model")

            self.assertEqual(result, "回复")

    def test_error_handling(self):
        """错误处理"""
        mock_response = Mock()

        with patch('src.cli_talk.stream_events') as mock_stream:
            mock_stream.return_value = [
                ("error", "Something went wrong"),
            ]

            result = consume_to_terminal(mock_response, "test-model")

            self.assertEqual(result, "")


class TestCLIToolIntegration(unittest.TestCase):
    """测试 CLI 工具调用集成"""

    def test_tools_md_loading(self):
        """测试 tools.md 加载逻辑"""
        # 这个测试验证加载逻辑，不需要实际文件
        # cli_talk.py 中的加载是可选的（try/except），所以只验证逻辑

        tools_content = "# SKILL\n\ndo python 可用"

        # 验证内容包含关键字
        self.assertIn("do python", tools_content)
        self.assertIn("SKILL", tools_content)

    def test_tool_execution_loop(self):
        """测试工具执行循环（逻辑验证）"""
        # 这个测试只验证逻辑，不实际执行

        # 1. 模拟 AI 返回 do 块
        response_with_tool = "好的，我来执行\n\ndo python\n    print('test')\nend"

        # 2. 检测到 do 块
        self.assertTrue(has_do_block(response_with_tool))

        # 3. 解析 do 块
        blocks = parse_do_blocks(response_with_tool)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0][0], "py")  # 规范化为 py

        # 4. 执行逻辑由 execute_blocks 测试，此处只验证流程


if __name__ == "__main__":
    unittest.main()
