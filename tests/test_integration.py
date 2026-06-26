# =====================================================================
# 集成测试
#
# 测试范围：
# 1. File 模式完整工作流：解析 → LLM → 渲染 → 工具 → 回引
# 2. CLI 模式完整工作流：输入 → LLM → 工具 → 输出
# 3. 配置解析集成
# 4. 错误恢复流程
# =====================================================================
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import json

from src.config import resolve_config
from src.markdown_parser import parse_file
from src.stream_renderer import write_response, write_anchor
from src.tool_executor import parse_do_blocks, execute_blocks, has_do_block


class TestFileWorkflow(unittest.TestCase):
    """测试 File 模式完整工作流"""

    def setUp(self):
        """创建临时文件"""
        self.temp_md = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8')
        self.temp_md.close()
        self.md_path = self.temp_md.name

        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False, encoding='utf-8')
        self.temp_log.close()
        self.log_path = self.temp_log.name

    def tearDown(self):
        """清理临时文件"""
        os.unlink(self.md_path)
        os.unlink(self.log_path)

    def test_parse_and_render(self):
        """解析 → 渲染流程"""
        # 1. 写入初始 markdown
        md_content = "---\nname: 测试\n---\n\n"
        md_content += "## system\n    你是助手\n\n"
        md_content += "## user\n    你好\n\n"

        with open(self.md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        # 2. 解析文件
        config, messages = parse_file(md_content)
        self.assertEqual(config['name'], '测试')
        self.assertEqual(len(messages), 2)  # system + user
        # system 被映射为 assistant（除了 user 外都映射为 assistant）
        self.assertEqual(messages[0]['role'], 'assistant')
        self.assertEqual(messages[1]['role'], 'user')

        # 3. Mock LLM 响应并渲染
        mock_response = Mock()

        with patch('src.stream_renderer.stream_events') as mock_stream:
            mock_stream.return_value = [
                ("role", "assistant"),
                ("content", "你好啊！"),
            ]

            raw = write_response(mock_response, self.md_path, "助手", self.log_path, enable_log=True)

            self.assertEqual(raw, "你好啊！")

        # 4. 写入锚点
        write_anchor(self.md_path)

        # 5. 验证完整文件
        with open(self.md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn("## 助手", content)
        self.assertIn("你好啊！", content)
        self.assertIn("## user", content)

    def test_tool_execution_workflow(self):
        """工具执行完整流程"""
        # 1. Mock AI 返回带 do 块的回复
        ai_response = "好的\n\ndo python\n    print('Hello')\nend"

        # 2. 检测到工具调用
        self.assertTrue(has_do_block(ai_response))

        # 3. 解析工具块
        blocks = parse_do_blocks(ai_response)
        self.assertEqual(len(blocks), 1)

        # 4. 执行工具
        messages = [{"role": "user", "content": "执行工具"}]
        results = execute_blocks(blocks, messages, self.log_path)

        # 5. 验证执行结果
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "py")  # 规范化为 py

        # 6. 验证 log 输出
        with open(self.log_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
        self.assertIn("Hello", log_content)

    def test_multiple_rounds(self):
        """多轮对话流程"""
        messages = [{"role": "system", "content": "你是助手"}]

        # 第一轮
        messages.append({"role": "user", "content": "你好"})

        mock_response1 = Mock()
        with patch('src.stream_renderer.stream_events') as mock_stream:
            mock_stream.return_value = [("content", "你好啊")]
            raw1 = write_response(mock_response1, self.md_path, "AI", self.log_path, enable_log=True)

        messages.append({"role": "assistant", "content": raw1})

        # 第二轮
        messages.append({"role": "user", "content": "再见"})

        mock_response2 = Mock()
        with patch('src.stream_renderer.stream_events') as mock_stream:
            mock_stream.return_value = [("content", "再见")]
            raw2 = write_response(mock_response2, self.md_path, "AI", self.log_path, enable_log=True)

        messages.append({"role": "assistant", "content": raw2})

        # 验证 messages 历史
        self.assertEqual(len(messages), 5)  # system + user + assistant + user + assistant


class TestCLIWorkflow(unittest.TestCase):
    """测试 CLI 模式完整工作流"""

    def test_cli_tool_loop(self):
        """CLI 工具调用循环"""
        from src.cli_talk import consume_to_terminal

        messages = [{"role": "system", "content": "你是助手"}]

        # 第一次调用：AI 返回 do 块
        mock_response1 = Mock()
        with patch('src.cli_talk.stream_events') as mock_stream:
            mock_stream.return_value = [
                ("content", "do python\n    print('test')\nend"),
            ]

            response_text = consume_to_terminal(mock_response1, "test-model")

        # 检测到工具
        self.assertTrue(has_do_block(response_text))

        # 解析并执行
        blocks = parse_do_blocks(response_text)
        self.assertEqual(len(blocks), 1)

        # 执行工具（使用临时 log）
        temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False, encoding='utf-8')
        temp_log.close()

        try:
            results = execute_blocks(blocks, messages, temp_log.name)
            self.assertEqual(len(results), 1)

            # 验证输出
            with open(temp_log.name, 'r', encoding='utf-8') as f:
                output = f.read()
            self.assertIn("test", output)

        finally:
            os.unlink(temp_log.name)


class TestConfigIntegration(unittest.TestCase):
    """测试配置解析集成"""

    def setUp(self):
        """创建临时配置文件"""
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
        json.dump({
            "model": "test-model",
            "api_key": "test-key",
            "base_url": "https://test.com"
        }, self.temp_config)
        self.temp_config.close()
        self.config_path = self.temp_config.name

    def tearDown(self):
        """清理临时文件"""
        os.unlink(self.config_path)

    def test_config_loading(self):
        """配置加载"""
        with patch('src.config.CONFIG_PATH', self.config_path):
            config = resolve_config(path=self.config_path)
            self.assertEqual(config['model'], 'test-model')
            self.assertEqual(config['api_key'], 'test-key')

    def test_config_with_frontmatter(self):
        """frontmatter 覆盖配置"""
        # 创建 markdown 内容
        md_content = "---\nmodel: override-model\n---\n\n"
        md_content += "## user\n    test"

        # 解析
        config, messages = parse_file(md_content)
        self.assertEqual(config['model'], 'override-model')


class TestErrorRecovery(unittest.TestCase):
    """测试错误恢复流程"""

    def test_tool_execution_error(self):
        """工具执行错误恢复"""
        # Python 错误
        blocks = [("python", "raise ValueError('test error')")]

        temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False, encoding='utf-8')
        temp_log.close()

        try:
            messages = []
            results = execute_blocks(blocks, messages, temp_log.name)

            # 执行完成，返回结果
            self.assertEqual(len(results), 1)

            # log 中包含错误信息
            with open(temp_log.name, 'r', encoding='utf-8') as f:
                output = f.read()
            self.assertIn("异常", output)
            self.assertIn("test error", output)

        finally:
            os.unlink(temp_log.name)

    def test_invalid_markdown(self):
        """无效 markdown 处理"""
        # 无效格式（没有 frontmatter）
        md_content = "不是有效的格式"

        # 解析失败返回 None
        config, messages = parse_file(md_content)
        self.assertIsNone(config)
        self.assertIsNone(messages)

    def test_stream_error(self):
        """流式响应错误"""
        from src.cli_talk import consume_to_terminal

        mock_response = Mock()

        with patch('src.cli_talk.stream_events') as mock_stream:
            mock_stream.return_value = [
                ("content", "正常内容"),
                ("error", "Stream error occurred"),
            ]

            result = consume_to_terminal(mock_response, "test-model")

            # 返回错误前的内容
            self.assertEqual(result, "正常内容")


class TestEndToEnd(unittest.TestCase):
    """端到端测试"""

    def test_file_mode_complete_cycle(self):
        """File 模式完整周期"""
        # 创建 markdown 内容
        md_content = "---\nname: 猫娘\n---\n\n"
        md_content += "## system\n    你是猫娘\n\n"
        md_content += "## user\n    喵一下\n\n"

        temp_md = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8')
        temp_md.write(md_content)
        temp_md.close()

        temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False, encoding='utf-8')
        temp_log.close()

        try:
            # 1. 解析
            config, messages = parse_file(md_content)
            self.assertEqual(config['name'], '猫娘')

            # 2. Mock LLM 响应
            mock_response = Mock()
            with patch('src.stream_renderer.stream_events') as mock_stream:
                mock_stream.return_value = [
                    ("thinking", "思考中..."),
                    ("content", "喵～"),
                    ("usage", {"prompt": 10, "completion": 5, "total": 15}),
                ]

                raw = write_response(mock_response, temp_md.name, "猫娘", temp_log.name, enable_log=True)

            # 3. 验证响应
            self.assertEqual(raw, "喵～")

            # 4. 写入锚点
            write_anchor(temp_md.name)

            # 5. 验证完整文件
            with open(temp_md.name, 'r', encoding='utf-8') as f:
                content = f.read()

            self.assertIn("## 猫娘", content)
            self.assertIn("喵～", content)
            self.assertIn("## user", content)

            # 6. 验证 thinking 在 log 中
            with open(temp_log.name, 'r', encoding='utf-8') as f:
                log_content = f.read()
            self.assertIn("思考中...", log_content)

        finally:
            os.unlink(temp_md.name)
            os.unlink(temp_log.name)


if __name__ == "__main__":
    unittest.main()
