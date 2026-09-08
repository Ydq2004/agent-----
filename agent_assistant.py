import os
import sqlite3
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import HumanMessage
from langchain.agents.middleware import SummarizationMiddleware

conn= sqlite3.connect("Memory/agent_assistant_memory.db",check_same_thread=False)
memory_saver=SqliteSaver(conn)

llm=ChatOpenAI(
    model="Gemini-3.7-flash",
    api_key=os.environ.get("GEMINI_API_KEY"),
    base_url="https://tengsuan.xiweinet.com/v1",
    temperature=0.9
)

agent=create_agent(
    llm=llm,
    tools=[],
    systemprompt="""
# 核心设定
你叫“柳如烟”，是用户的私人专属电脑系统女仆助理。

"""
)