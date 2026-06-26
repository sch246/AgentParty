# 工具参数系统使用示例

本文档展示如何使用工具参数系统。

## Python 超时控制

### 基础用法（无超时）

```markdown
do py
    print("Hello, World!")
    for i in range(5):
        print(f"Count: {i}")
end
```

### 带超时参数

```markdown
do py timeout=60
    import time
    print("Starting long task...")
    time.sleep(30)
    print("Task completed!")
end
```

如果执行超过 60 秒，会输出：
```
[do py 超时: 60秒]
Starting long task...
```

## Shell 命令参数

### 基础用法（当前目录）

```markdown
do sh
    pwd
    ls -la
end
```

### 指定工作目录

```markdown
do sh cwd=/tmp
    pwd
    ls -la
end
```

输出会显示 `/tmp` 目录的内容。

### 同时使用多个参数

```markdown
do sh cwd=/var/log timeout=5
    pwd
    ls -la | head -10
end
```

## 实际应用场景

### 场景 1: 运行可能耗时的测试

```markdown
do py timeout=300
    import subprocess
    print("Running test suite...")
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    print(result.stderr)
end
```

### 场景 2: 在特定目录执行构建

```markdown
do sh cwd=/path/to/project timeout=600
    npm install
    npm run build
end
```

### 场景 3: 下载文件（带超时保护）

```markdown
do py timeout=120
    import urllib.request
    print("Downloading file...")
    urllib.request.urlretrieve(
        "https://example.com/large-file.zip",
        "download.zip"
    )
    print("Download complete!")
end
```

### 场景 4: 临时目录操作

```markdown
do sh cwd=/tmp timeout=10
    # 创建临时工作目录
    mkdir -p work
    cd work
    
    # 执行操作
    echo "test" > file.txt
    cat file.txt
    
    # 清理
    cd ..
    rm -rf work
end
```

## 注意事项

1. **超时值选择**：根据实际任务耗时设置合理的超时值
2. **工作目录**：`cwd` 参数仅对 Shell 有效，Python 使用 `os.chdir()` 切换目录
3. **向后兼容**：不使用参数时，行为与之前完全相同
4. **错误处理**：超时会返回已有的部分输出和超时提示

## 参数参考

| 参数 | 适用工具 | 类型 | 说明 | 示例 |
|------|---------|------|------|------|
| `timeout` | py, sh | 整数 | 超时秒数 | `timeout=60` |
| `cwd` | sh | 字符串 | 工作目录路径 | `cwd=/tmp` |

## 调试技巧

### 查看执行日志

参数会显示在日志中：

```
--- do py timeout=60 ---
Hello, World!
```

```
--- do sh cwd=/tmp timeout=5 ---
/tmp
total 120
...
```

### 测试超时设置

先用短超时测试，确认功能正常：

```markdown
do py timeout=1
    import time
    time.sleep(2)  # 故意超时
    print("This won't print")
end
```

预期输出：
```
[do py 超时: 1秒]
```
