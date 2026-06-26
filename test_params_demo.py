#!/usr/bin/env python
"""
参数系统演示脚本

展示新的工具参数功能：
1. Python timeout 参数
2. Shell timeout 和 cwd 参数
3. 向后兼容（无参数）
"""

from src.tool_executor import parse_do_blocks, execute_blocks
import tempfile
import os

def demo():
    print("=" * 60)
    print("工具参数系统演示")
    print("=" * 60)

    # 创建临时 log 文件
    with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8', suffix='.log') as f:
        log_path = f.name

    try:
        # 测试 1: Python 无参数（向后兼容）
        print("\n1. Python 基础执行（无参数）")
        print("-" * 60)
        text1 = """
do py
    print("Hello from Python!")
    print(f"1 + 1 = {1 + 1}")
end
"""
        blocks1 = parse_do_blocks(text1)
        print(f"解析结果: {len(blocks1)} 个块")
        print(f"参数: {blocks1[0][2]}")

        execute_blocks(blocks1, [], log_path)
        with open(log_path, 'r', encoding='utf-8') as f:
            print(f.read())

        # 清空 log
        open(log_path, 'w').close()

        # 测试 2: Python 带 timeout（快速完成）
        print("\n2. Python 带 timeout（快速完成）")
        print("-" * 60)
        text2 = """
do py timeout=5
    print("Fast execution")
    import time
    time.sleep(0.1)
    print("Done!")
end
"""
        blocks2 = parse_do_blocks(text2)
        print(f"解析结果: {len(blocks2)} 个块")
        print(f"参数: {blocks2[0][2]}")

        execute_blocks(blocks2, [], log_path)
        with open(log_path, 'r', encoding='utf-8') as f:
            print(f.read())

        # 清空 log
        open(log_path, 'w').close()

        # 测试 3: Python 超时
        print("\n3. Python 超时测试")
        print("-" * 60)
        text3 = """
do py timeout=1
    import time
    print("Starting slow task...")
    time.sleep(3)
    print("This won't print")
end
"""
        blocks3 = parse_do_blocks(text3)
        print(f"解析结果: {len(blocks3)} 个块")
        print(f"参数: {blocks3[0][2]}")

        execute_blocks(blocks3, [], log_path)
        with open(log_path, 'r', encoding='utf-8') as f:
            print(f.read())

        # 清空 log
        open(log_path, 'w').close()

        # 测试 4: Shell 无参数
        print("\n4. Shell 基础执行（无参数）")
        print("-" * 60)
        text4 = """
do sh
    echo "Hello from Shell!"
    echo "Current directory: $(pwd)"
end
"""
        blocks4 = parse_do_blocks(text4)
        print(f"解析结果: {len(blocks4)} 个块")
        print(f"参数: {blocks4[0][2]}")

        execute_blocks(blocks4, [], log_path)
        with open(log_path, 'r', encoding='utf-8') as f:
            print(f.read())

        # 清空 log
        open(log_path, 'w').close()

        # 测试 5: Shell 带 cwd
        print("\n5. Shell 带 cwd 参数")
        print("-" * 60)
        text5 = """
do sh cwd=/tmp
    pwd
    echo "Working in /tmp"
end
"""
        blocks5 = parse_do_blocks(text5)
        print(f"解析结果: {len(blocks5)} 个块")
        print(f"参数: {blocks5[0][2]}")

        execute_blocks(blocks5, [], log_path)
        with open(log_path, 'r', encoding='utf-8') as f:
            print(f.read())

        # 清空 log
        open(log_path, 'w').close()

        # 测试 6: Shell 带 timeout（快速完成）
        print("\n6. Shell 带 timeout（快速完成）")
        print("-" * 60)
        text6 = """
do sh timeout=5
    echo "Fast shell command"
    sleep 0.1
    echo "Done"
end
"""
        blocks6 = parse_do_blocks(text6)
        print(f"解析结果: {len(blocks6)} 个块")
        print(f"参数: {blocks6[0][2]}")

        execute_blocks(blocks6, [], log_path)
        with open(log_path, 'r', encoding='utf-8') as f:
            print(f.read())

        # 清空 log
        open(log_path, 'w').close()

        # 测试 7: Shell 超时
        print("\n7. Shell 超时测试")
        print("-" * 60)
        text7 = """
do sh timeout=1
    echo "Starting slow task..."
    sleep 3
    echo "This won't print"
end
"""
        blocks7 = parse_do_blocks(text7)
        print(f"解析结果: {len(blocks7)} 个块")
        print(f"参数: {blocks7[0][2]}")

        execute_blocks(blocks7, [], log_path)
        with open(log_path, 'r', encoding='utf-8') as f:
            print(f.read())

        # 清空 log
        open(log_path, 'w').close()

        # 测试 8: 多参数组合
        print("\n8. Shell 多参数组合")
        print("-" * 60)
        text8 = """
do sh cwd=/tmp timeout=5
    pwd
    ls -la | head -5
end
"""
        blocks8 = parse_do_blocks(text8)
        print(f"解析结果: {len(blocks8)} 个块")
        print(f"参数: {blocks8[0][2]}")

        execute_blocks(blocks8, [], log_path)
        with open(log_path, 'r', encoding='utf-8') as f:
            print(f.read())

        print("\n" + "=" * 60)
        print("演示完成！")
        print("=" * 60)

    finally:
        # 清理临时文件
        if os.path.exists(log_path):
            os.unlink(log_path)

if __name__ == "__main__":
    demo()
