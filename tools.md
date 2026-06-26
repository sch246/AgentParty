# SKILL

你可以通过 do 块调用工具。

## 工具

不同于常规的工具调用，在你的回复里顶格写 `do py` 或 `do sh` 即可：

do py
    你的 Python 代码
    缩进是必须的
end

do sh
    你的 shell 命令
    缩进是必须的
end

一个回复可以有多个 do 块。py块之间变量不共享。

注：为向后兼容，仍支持 `do python`，但推荐使用 `do py`。

## 参数系统

工具调用支持参数，语法：`do <type> key=value ...`

### Python 执行

基本用法：
```
do py
    print("Hello")
end
```

带 timeout（秒）：
```
do py timeout=60
    import time
    time.sleep(30)
    print("done")
end
```

### Shell 执行

基本用法：
```
do sh
    ls -la
end
```

带参数：
```
do sh cwd=/tmp timeout=5
    pwd
    ls
end
```

### 支持的参数

- `timeout=<秒>`: 超时时间（Python 和 Shell 都支持）
- `cwd=<路径>`: 工作目录（仅 Shell）

## do py 可用对象

`messages` — 完整对话列表，可直接索引/切片：

- `messages[3]["content"]` → 第 4 条消息正文
- `messages[1:5]` → 消息 1~4

`read(path)` — 读文件或目录：
