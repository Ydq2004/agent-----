import os
import sqlite3
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import HumanMessage , SystemMessage
from langchain.agents.middleware import SummarizationMiddleware,dynamic_prompt
from tools_registry import ALL_TOOLS
from datetime import datetime


BASE_SYSTEM_PROMPT = """# 核心设定
你叫"雪之下雪乃",是一位 AI 电脑系统助理。
你的初始性格设定是:理性、冷静、说话直接但做事极其可靠(参考"我的青春恋爱物语果然有问题"里前期的雪之下雪乃)。

# 基础前置
每次接收聊天先调用记忆查询工具查询当前会话可能涉及的信息。
"""


conn=sqlite3.connect("Memory_db/checkpoint.db",check_same_thread=False)
memory_saver=SqliteSaver(conn)


llm=ChatOpenAI(
    model="deepseek-v4.1-flash-expires-on-0910",
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0.8
)

@dynamic_prompt
def runtime_prompt(request)->str:
    """动态更新systemprompt时间且不污染 Checkpoint"""
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S %A")

    # 动态拼装系统人设与最新时间
    prompt_text = f"{BASE_SYSTEM_PROMPT}\n[当前系统精确时间]: {current_time_str}"

    # 返回包含最新时间的 SystemMessage
    return prompt_text

agent=create_agent(
    model=llm,
    tools=ALL_TOOLS,
    system_prompt=BASE_SYSTEM_PROMPT,
    checkpointer=memory_saver,
    middleware=[
            runtime_prompt,
            SummarizationMiddleware(
                model=llm,  # 用同一个模型来总结旧对话
                trigger=("tokens", 300000),  # 超过 300000 tokens 就触发总结
            )
          ]
)

thread_id="001"
if __name__ == "__main__":
    while True:
        userinput=input("我:").strip()

        if not userinput:
            continue

        if userinput=='退出':
            break

        try:
            result= agent.invoke(
                 {"messages": [HumanMessage(content=userinput)]},
                 config={"configurable":{"thread_id":thread_id}}
            )
        except Exception as e:
            print(f"模型调用失败:{e}")
            continue
        print(f"🤖 AI: {result['messages'][-1].content}\n")

