# =====================================================================
# 第一部分：借工具
# Python 最强大的地方在于“白嫖”。这几行意思是：我们把别人写好的、
# 用来连接人工智能的工具包拿过来用。对于新手来说，这部分“当做咒语照抄”就行。
# =====================================================================
from openai import OpenAI
from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import ChoiceDelta, Choice
from openai.types.completion_usage import CompletionUsage, CompletionTokensDetails, PromptTokensDetails

# =====================================================================
# 第二部分：买手机并插上手机卡
# client（客户端）就像是我们买的一部专门给AI打电话的手机。
# api_key 就是你的“手机卡密码”，base_url 就是你要打给哪家运营商（这里是DeepSeek）。
# =====================================================================
client = OpenAI(
    api_key="sk-93bb529a9af8460aa5f36c6083a95503",
    base_url="https://api.deepseek.com"
)

# =====================================================================
# 第三部分：教电脑学会一个新动作：【怎么给AI打电话】
# def 的意思是 define（定义），相当于你教电脑一个名叫 request_llm 的新配方。
# =====================================================================
def request_llm(messages):
    return client.chat.completions.create(
        model="deepseek-v4-flash",  # 告诉客服我们要找哪个型号的AI接电话
        messages=messages,          # 把我们想说的话递过去
        stream=True,                # 这个非常关键！意思是“像打字机一样一个字一个字蹦出来”，而不是等几分钟后一次性发一长串
        reasoning_effort="high",    # 让 AI 多动点脑子
        extra_body={"thinking": {"type": "enabled"}} # 强行让 AI 把它的“心理活动（思考过程）”也发给我们看
    )


def print_stream(response, color_print):
    response_text = "" # 拿出一个空本子，准备把AI说的所有字抄下来
    
    # for...in... 叫做“循环”。意思是从 response（快递传送带）上，
    # 每次拿一个名叫 delta 的小包裹下来，直到包裹拿完为止。
    for delta in response:
        
        # match...case 叫做“模式匹配”。相当于给包裹进行“垃圾分类”！
        match delta:
            # 第一种包裹：里面装着AI的名字（也就是刚开始回话的时候）
            case ChatCompletionChunk(choices=[Choice(delta=ChoiceDelta(role='assistant'))], model=model_name):
                color_print(f"{model_name}: ", "cyan", end="")
            
            # 第二种包裹：里面装着AI的“心理活动”（思考内容）
            case ChatCompletionChunk(choices=[Choice(delta=ChoiceDelta(content=None, reasoning_content=reasoning_content))]):
                # 用黄色把心理活动打印出来
                color_print(reasoning_content, color="yellow", end="")
            
            # 第三种包裹：里面装着AI真正说出口的话（正式回复）
            case ChatCompletionChunk(choices=[Choice(delta=ChoiceDelta(content=content, reasoning_content=None))]):
                # 用绿色把正式回复打印出来
                color_print(content, color="green", end="")
                
                # 如果包裹里确实有文字，就把它写进我们的空本子里存起来
                if content is not None:
                    response_text += content
            
            # 第四种包裹：不认识的奇怪包裹（报错兜底）
            case el:
                print()
                color_print(el, color="red") # 用红色警告我们
                
        # 看看包裹底部有没有贴着“账单”（本次花了多少钱/Token）
        match delta.usage:
            # 如果有账单，就把输入的字数、输出的字数、花费的脑力等数据提取出来
            case CompletionUsage(completion_tokens=completion_tokens, prompt_tokens=prompt_tokens, total_tokens=total_tokens, completion_tokens_details=CompletionTokensDetails(reasoning_tokens=reasoning_tokens), prompt_cache_hit_tokens=prompt_cache_hit_tokens, prompt_cache_miss_tokens=prompt_cache_miss_tokens):
                print() # 换个行，让排版好看点
                # 用低调的灰色打印账单明细
                color_print(f"输入: {prompt_tokens}, 输出: {completion_tokens}, 总: {total_tokens}", color="gray")
                color_print(f"思考: {reasoning_tokens}, 缓存命中: {prompt_cache_hit_tokens}, 缓存未命中: {prompt_cache_miss_tokens}", color="gray")
    
    # 包裹全部拆完后，把刚才抄满字的本子交出去
    return response_text

cli_thinking = False

def color_print(text, color, end="\n"):
    global cli_thinking
    if color == "yellow" and not cli_thinking:
        cli_thinking = True
        print()
    elif color == "green" and cli_thinking:
        cli_thinking = False
        print()

    # 字典（长得像大括号 {}）：就像一本汉英词典。
    # 左边是颜色的名字，右边是电脑终端才能看懂的“颜色魔法代码”。
    color_dict = {
        "red": "\033[31m",      
        "green": "\033[32m",    
        "yellow": "\033[33m",   
        "blue": "\033[34m",     
        "purple": "\033[35m",   
        "cyan": "\033[36m",     
        "white": "\033[37m",    
        "gray": "\033[90m",     
    }
    
    reset = "\033[0m" # 变色完毕后，必须用这个代码把颜色洗掉，不然整个屏幕都会被染色
    
    # 去上面的词典里查颜色代码。如果找不到，就默认什么颜色都不加（返回 ""）
    color_code = color_dict.get(color.lower(), "")
    
    # f"..." 是一种超级方便的文字拼接魔法，把颜色代码、文字、洗掉颜色的代码串在一起打印。
    # end=end 是为了控制打字机效果，告诉电脑“打印完这批字先不要换行”。
    print(f"{color_code}{text}{reset}", end=end)

def cli_talk():
    # 1. 创建一个叫 messages 的“列表”（长得像方括号 []）。
    # 列表就像是一个大抽屉，里面按顺序装着我们聊天的历史记录。
    # 最开始，抽屉里只有一句话：偷偷给AI设定一个“猫娘”的身份。
    messages = [
        {"role": "system", "content": "你是一只猫娘"}
    ]

    # 2. while True: 是一个“死循环”。
    # 意思是不管发生什么，一遍又一遍地重复下面的事情，这样我们就可以一直聊天不中断。
    while True:
        # 提醒轮到你说话了
        color_print("user: ", color="cyan", end="")
        
        # input() 就是在屏幕上停住，等你用键盘打字，打完按回车。
        # 你的话会被存进 request_text 这个盒子里。
        request_text = input()
        
        # 将你说的话，装进一个特定的格式里，扔进 messages（历史记录大抽屉）的最后面。
        messages += [{"role": "user", "content": request_text}]
        
        # 把整个抽屉（包括人设、之前的聊天、你刚说的话）打包发给AI！
        response = request_llm(messages)
        
        # 让机器人在屏幕上“打字机”式地把回复打印出来，并把完整的回复记下来。
        response_text = print_stream(response, color_print)
        
        # 最关键的一步：有了记忆！
        # 把 AI 刚刚说的话，也扔进 messages 大抽屉里。
        # 这样下一轮聊天时，AI 就能看到自己上回说了啥，从而不会精神分裂。
        messages += [{"role": "assistant", "content": response_text}]


import re
def parse_text_to_dialogue(text, roles):
    """
    roles: 列表或集合，例如 ['user', 'ai', 'system']
    """
    # 构建正则
    roles = [role+": " for role in roles]
    pattern = r'(' + '|'.join(map(re.escape, roles)) + r')'
    
    # 1. 拆分文本，保留分隔符
    # split 结果示例: ['user: ', ' Hello ', 'ai: ', '', 'user: ', ' World']
    tokens = re.split(pattern, text)
    
    dialogues = []
    current_role = None
    
    # 2. 遍历 token 处理
    for token in tokens:
        if token in roles:
            # 遇到新 Key，切换角色
            current_role = token
            dialogues.append({"role": current_role, "content": ""})
        elif current_role is not None:
            # 遇到内容，追加到当前角色的 content 中
            # 如果连续两个 Key，这里第一次循环会遇到空字符串，符合要求
            dialogues[-1]["content"] += token

    # 3. 清理
    return [d for d in dialogues if d["role"] is not None]


def handler(path):
    with open(path, encoding='utf-8') as f:
        text = f.read()
    if text.endswith('\n\n'):
        messages = parse_text_to_dialogue(text, ['system', 'user', 'deepseek-v4-flash'])


def file_talk():
    from watch_file import watcher, loop
    watcher.register('talk.md', handler)
    loop()
