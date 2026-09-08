import os
import sqlite3
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import HumanMessage
from langchain.agents.middleware import SummarizationMiddleware
from tools_registry import ALL_TOOLS

conn=sqlite3.connect("Memory_db/checkpoint.db",check_same_thread=False)
memory_saver=SqliteSaver(conn)


llm=ChatOpenAI(
    model="deepseek-v4.1-flash-expires-on-0910",
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0.8
)

agent=create_agent(
    model=llm,
    tools=ALL_TOOLS,
    system_prompt="""
# 核心设定
你叫“雪之下雪乃”，是一位ai电脑系统助理。
你的初始性格设定是：（参考我的青春恋爱物语果然有问题里前期的雪之下雪乃）。

#基础必要前置
每次接收聊天先调用记忆查询工具查询当前会话可能涉及的信息.
    """, 
    checkpointer=memory_saver,
    middleware=[
              SummarizationMiddleware(
                  model=llm,  # 用同一个模型来总结旧对话
                  trigger=("tokens", 300000),  # 超过 20000 tokens 就触发总结
              )
          ]
)

thread_id="001"
if __name__ == "__main__":
    while True:
        userinput=input("我：").strip()

        if not userinput:
            continue
        if userinput=='退出':#我想保留这个顺序，这样可以看到这个助手对于我离开的反应
            break

        result= agent.invoke(
             {"messages": [HumanMessage(content=userinput)]},
             config={"configurable":{"thread_id":thread_id}}
        )
        print(f"🤖 AI: {result['messages'][-1].content}\n")
        
