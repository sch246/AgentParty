# SKILL

你可以通过 do 块调用工具。

## 工具

不同于常规的工具调用，在你的回复里顶格写 `do python` 或 `do sh` 即可：

do python
    你的 Python 代码
end

do sh
    你的 shell 命令
end

一个回复可以有多个 do 块。py块之间变量不共享。无超时，请手动设置超时。

## do python 可用对象

`messages` — 完整对话列表，可直接索引/切片：

- `messages[3]["content"]` → 第 4 条消息正文
- `messages[1:5]` → 消息 1~4

`read(path)` — 读文件或目录：
