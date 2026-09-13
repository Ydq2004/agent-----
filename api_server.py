import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field #pydantic 是一个专门用来做数据校验和数据转换的 Python 模块。
from langchain_core.messages import HumanMessage

app = FastAPI(
    title="雪之下雪乃Agent API",
    version="0.1.0"
)

from agent_core import agent

class ChatRequest(BaseModel):
    thread_id:str = Field(...,min_length=1,max_length=100)
    message:str = Field(...,min_length=1,max_length=50000)

class ChatResponse(BaseModel):
    thread_id:str
    answer:str

@app.get("/health")
def health():
    return {
        "status":"ok",
        "version":app.version
    }

@app.post("/chat",response_model=ChatResponse)
def chat(request:ChatRequest):

    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="服务未配置 DEEPSEEK_API_KEY"
        )
  
    
    result=agent.invoke(
       {
           "messages":[
                       HumanMessage(content=request.message)
            ]
       },
       config={
           "configurable":{
               "thread_id":request.thread_id
           }
       }
        
    )
    return{
        "thread_id":request.thread_id,
        "answer":result["messages"][-1].content
    }
