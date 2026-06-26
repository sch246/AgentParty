"""
tool_executor.py 单元测试

测试覆盖：
- do 块解析（python/sh）
- 沙盒执行与输出捕获
- readfile() 注入函数
- 错误处理（语法错误、异常）
- 行号范围返回
"""
import unittest
import os
import tempfile
from pathlib import Path
import sys

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tool_executor import (
    parse_do_blocks,
    has_do_block,
    execute_blocks,
    _strip_one_indent,
    _run_python,
    _run_sh,
    _build_namespace,
    _read_fn,
)


class TestParseDoBlocks(unittest.TestCase):
    """parse_do_blocks 函数测试"""

    def test_single_python_block(self):
        """测试解析单个 python 块"""
        text = """do python
    print("hello")
end"""
        blocks = parse_do_blocks(text)

        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0][0], "python")
        self.assertEqual(blocks[0][1], 'print("hello")')

    def test_single_sh_block(self):
        """测试解析单个 sh 块"""
        text = """do sh
    echo "hello"
end"""
        blocks = parse_do_blocks(text)

        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0][0], "sh")
        self.assertEqual(blocks[0][1], 'echo "hello"')

    def test_multiple_blocks(self):
        """测试解析多个 do 块"""
        text = """一些文本
do python
    x = 1
    print(x)
end

更多文本

do sh
    ls -la
end"""
        blocks = parse_do_blocks(text)

        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0][0], "python")
        self.assertIn("x = 1", blocks[0][1])
        self.assertEqual(blocks[1][0], "sh")
        self.assertIn("ls -la", blocks[1][1])

    def test_indent_stripping(self):
        """测试缩进去除：只去除一级缩进"""
        text = """do python
    def foo():
        if True:
            print("nested")
end"""
        blocks = parse_do_blocks(text)

        code = blocks[0][1]
        # 第一级缩进去掉，内部缩进保留
        self.assertIn("def foo():", code)
        self.assertIn("    if True:", code)
        self.assertIn('        print("nested")', code)

    def test_empty_block(self):
        """测试空 do 块"""
        text = """do python
end"""
        blocks = parse_do_blocks(text)

        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0][1], "")

    def test_no_blocks(self):
        """测试无 do 块"""
        text = """只是一些普通文本
没有任何 do 块"""
        blocks = parse_do_blocks(text)

        self.assertEqual(len(blocks), 0)

    def test_has_do_block(self):
        """测试 has_do_block 辅助函数"""
        self.assertTrue(has_do_block("do python\nend"))
        self.assertTrue(has_do_block("text\ndo sh\nend\nmore"))
        self.assertFalse(has_do_block("no blocks here"))
        self.assertFalse(has_do_block("do_python is not a block"))


class TestStripOneIndent(unittest.TestCase):
    """_strip_one_indent 函数测试"""

    def test_four_spaces(self):
        """测试去除 4 空格"""
        self.assertEqual(_strip_one_indent("    hello"), "hello")
        self.assertEqual(_strip_one_indent("        nested"), "    nested")

    def test_tab(self):
        """测试去除 1 个 tab"""
        self.assertEqual(_strip_one_indent("\thello"), "hello")
        self.assertEqual(_strip_one_indent("\t\tnested"), "\tnested")

    def test_no_indent(self):
        """测试无缩进"""
        self.assertEqual(_strip_one_indent("hello"), "hello")

    def test_less_than_four_spaces(self):
        """测试少于 4 空格"""
        self.assertEqual(_strip_one_indent("  hello"), "  hello")


class TestRunPython(unittest.TestCase):
    """_run_python 函数测试"""

    def test_simple_print(self):
        """测试简单 print 输出"""
        code = 'print("hello world")'
        output = _run_python(code, {})

        self.assertIn("hello world", output)

    def test_multiple_prints(self):
        """测试多行输出"""
        code = """print("line1")
print("line2")"""
        output = _run_python(code, {})

        self.assertIn("line1", output)
        self.assertIn("line2", output)

    def test_namespace_access(self):
        """测试命名空间注入"""
        code = """print(custom_var)"""
        ns = {"custom_var": 42}
        output = _run_python(code, ns)

        self.assertIn("42", output)

    def test_messages_access(self):
        """测试访问 messages"""
        messages = [{"role": "user", "content": "test"}]
        code = """print(len(messages))
print(messages[0]['role'])"""
        ns = {"messages": messages}
        output = _run_python(code, ns)

        self.assertIn("1", output)
        self.assertIn("user", output)

    def test_syntax_error(self):
        """测试语法错误处理"""
        code = "print('unclosed string"
        output = _run_python(code, {})

        self.assertIn("异常", output)

    def test_runtime_error(self):
        """测试运行时错误处理"""
        code = """x = 1 / 0"""
        output = _run_python(code, {})

        self.assertIn("异常", output)
        # 错误信息格式：[do python 异常: division by zero]
        # 不包含异常类型名，只有消息

    def test_partial_output_before_error(self):
        """测试错误前的部分输出"""
        code = """print("before error")
x = 1 / 0
print("after error")"""
        output = _run_python(code, {})

        self.assertIn("before error", output)
        self.assertIn("异常", output)
        self.assertNotIn("after error", output)


class TestRunSh(unittest.TestCase):
    """_run_sh 函数测试"""

    def test_simple_echo(self):
        """测试简单 echo 命令"""
        output = _run_sh('echo "hello"')

        self.assertIn("hello", output)

    def test_stderr_capture(self):
        """测试 stderr 捕获"""
        output = _run_sh('echo "error" >&2')

        self.assertIn("error", output)

    def test_command_failure(self):
        """测试命令失败"""
        output = _run_sh("exit 1")

        # sh 命令失败不抛异常，只是返回空输出
        # 这里主要测试不会崩溃
        self.assertIsInstance(output, str)

    def test_nonexistent_command(self):
        """测试不存在的命令"""
        output = _run_sh("nonexistent_command_12345")

        # 应该捕获错误信息
        self.assertIsInstance(output, str)


class TestReadFunction(unittest.TestCase):
    """_read_fn 注入函数测试"""

    def setUp(self):
        """创建临时测试文件"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = Path(self.temp_dir) / "test.txt"
        self.temp_file.write_text("Hello from file", encoding="utf-8")

        # 创建子目录
        self.sub_dir = Path(self.temp_dir) / "subdir"
        self.sub_dir.mkdir()
        (self.sub_dir / "file1.txt").write_text("content1", encoding="utf-8")
        (self.sub_dir / "file2.txt").write_text("content2", encoding="utf-8")

    def tearDown(self):
        """清理临时文件"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_read_file(self):
        """测试读取文件"""
        read_fn = _read_fn()
        content = read_fn(str(self.temp_file))

        self.assertEqual(content, "Hello from file")

    def test_read_directory(self):
        """测试读取目录"""
        read_fn = _read_fn()
        content = read_fn(str(self.sub_dir))

        # 应该列出目录内容
        self.assertIn("file1.txt", content)
        self.assertIn("file2.txt", content)

    def test_read_nonexistent(self):
        """测试读取不存在的路径"""
        read_fn = _read_fn()
        content = read_fn("/nonexistent/path")

        # 不存在的路径返回 None（代码中没有 return 默认返回）
        # 实际检查代码：如果 isfile/isdir 都为 False，函数返回 None
        self.assertIsNone(content)


class TestBuildNamespace(unittest.TestCase):
    """_build_namespace 函数测试"""

    def test_basic_namespace(self):
        """测试基础命名空间"""
        messages = [{"role": "user", "content": "test"}]
        ns = _build_namespace(messages, None)

        self.assertIn("messages", ns)
        self.assertIn("readfile", ns)
        self.assertEqual(ns["messages"], messages)
        self.assertTrue(callable(ns["readfile"]))

    def test_extra_namespace(self):
        """测试 extra_ns 合并"""
        messages = []
        extra = {"custom_func": lambda: 42, "custom_var": "value"}
        ns = _build_namespace(messages, extra)

        self.assertIn("custom_func", ns)
        self.assertIn("custom_var", ns)
        self.assertEqual(ns["custom_var"], "value")

    def test_extra_namespace_override(self):
        """测试 extra_ns 可以覆盖默认值"""
        messages = []
        custom_read = lambda x: "custom"
        extra = {"readfile": custom_read}
        ns = _build_namespace(messages, extra)

        # readfile 应该被覆盖
        self.assertEqual(ns["readfile"], custom_read)


class TestExecuteBlocks(unittest.TestCase):
    """execute_blocks 函数测试"""

    def setUp(self):
        """创建临时 log 文件"""
        self.temp_log = tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8")
        self.log_path = self.temp_log.name
        self.temp_log.close()

    def tearDown(self):
        """清理临时文件"""
        if os.path.exists(self.log_path):
            os.unlink(self.log_path)

    def test_single_block_execution(self):
        """测试单个块执行"""
        blocks = [("python", 'print("test")')]
        messages = []

        results = execute_blocks(blocks, messages, self.log_path)

        # 验证返回值
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "python")
        self.assertIsInstance(results[0][1], int)  # start_line
        self.assertIsInstance(results[0][2], int)  # end_line

        # 验证 log 文件
        with open(self.log_path, encoding="utf-8") as f:
            content = f.read()
            self.assertIn("--- do python ---", content)
            self.assertIn("test", content)

    def test_multiple_blocks_execution(self):
        """测试多个块串行执行"""
        blocks = [
            ("python", 'print("first")'),
            ("sh", 'echo "second"'),
        ]
        messages = []

        results = execute_blocks(blocks, messages, self.log_path)

        self.assertEqual(len(results), 2)

        # 验证 log 文件
        with open(self.log_path, encoding="utf-8") as f:
            content = f.read()
            self.assertIn("--- do python ---", content)
            self.assertIn("first", content)
            self.assertIn("--- do sh ---", content)
            self.assertIn("second", content)

    def test_line_numbers(self):
        """测试行号范围正确性"""
        blocks = [("python", 'print("line1")')]
        messages = []

        results = execute_blocks(blocks, messages, self.log_path)

        block_type, start, end = results[0]
        self.assertGreater(end, start)  # end 应该大于 start

        # 验证行号范围包含输出内容
        with open(self.log_path, encoding="utf-8") as f:
            lines = f.readlines()
            # start 到 end 之间应该包含标记和输出
            section = "".join(lines[start - 1:end])
            self.assertIn("--- do python ---", section)
            self.assertIn("line1", section)

    def test_append_to_existing_log(self):
        """测试追加到已有 log"""
        # 先写入一些内容
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write("existing content\n")

        blocks = [("python", 'print("new")')]
        results = execute_blocks(blocks, [], self.log_path)

        with open(self.log_path, encoding="utf-8") as f:
            content = f.read()
            self.assertIn("existing content", content)
            self.assertIn("new", content)

    def test_messages_accessible_in_block(self):
        """测试 do 块中可以访问 messages"""
        blocks = [("python", 'print(f"messages count: {len(messages)}")')]
        messages = [{"role": "user", "content": "test"}]

        results = execute_blocks(blocks, messages, self.log_path)

        with open(self.log_path, encoding="utf-8") as f:
            content = f.read()
            self.assertIn("messages count: 1", content)

    def test_extra_namespace(self):
        """测试 extra_ns 参数"""
        blocks = [("python", 'print(custom_value)')]
        messages = []
        extra_ns = {"custom_value": 42}

        results = execute_blocks(blocks, messages, self.log_path, extra_ns)

        with open(self.log_path, encoding="utf-8") as f:
            content = f.read()
            self.assertIn("42", content)

    def test_error_in_block(self):
        """测试块执行出错"""
        blocks = [("python", "x = 1 / 0")]
        messages = []

        results = execute_blocks(blocks, messages, self.log_path)

        # 应该仍然返回结果（错误信息）
        self.assertEqual(len(results), 1)

        with open(self.log_path, encoding="utf-8") as f:
            content = f.read()
            self.assertIn("异常", content)


class TestIntegration(unittest.TestCase):
    """集成测试：完整工作流"""

    def setUp(self):
        self.temp_log = tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8")
        self.log_path = self.temp_log.name
        self.temp_log.close()

    def tearDown(self):
        if os.path.exists(self.log_path):
            os.unlink(self.log_path)

    def test_full_workflow(self):
        """测试完整工作流：解析 → 执行 → 验证"""
        ai_response = """好的，我来分析数据：

do python
    data = [1, 2, 3, 4, 5]
    avg = sum(data) / len(data)
    print(f"平均值: {avg}")
end

分析完成！

do sh
    echo "任务结束"
end
"""
        # 1. 解析
        blocks = parse_do_blocks(ai_response)
        self.assertEqual(len(blocks), 2)

        # 2. 执行
        messages = [{"role": "user", "content": "分析数据"}]
        results = execute_blocks(blocks, messages, self.log_path)
        self.assertEqual(len(results), 2)

        # 3. 验证输出
        with open(self.log_path, encoding="utf-8") as f:
            content = f.read()
            self.assertIn("平均值: 3.0", content)
            self.assertIn("任务结束", content)

        # 4. 验证行号
        python_result = results[0]
        sh_result = results[1]
        self.assertEqual(python_result[0], "python")
        self.assertEqual(sh_result[0], "sh")
        self.assertLess(python_result[2], sh_result[1])  # python 结束在 sh 开始之前


if __name__ == "__main__":
    unittest.main()
