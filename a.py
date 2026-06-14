import re

text = "Hello world! How are you? I'm fine."

# 核心技巧：用 () 把分隔符包裹起来
# [.!?: ] 表示匹配这些字符中的任意一个
# 这里的 () 告诉 re.split: "把匹配到的分隔符也存进列表里"
result = re.split(r'([.!?])', text)

print(result)