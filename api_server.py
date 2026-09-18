import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse #把生成器不断产生的内容，持续发送给客户端。
from pydantic import BaseModel, Field #pydantic 是一个专门用来做数据校验和数据转换的 Python 模块。
from langchain_core.messages import HumanMessage
from observability import create_request_id,log_request_event
from time import perf_counter
import time
import json

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
    request_id:str


def is_retryable_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)

    if status_code in {429, 500, 502, 503, 504}:
        return True

    return isinstance(
        exc,
        (TimeoutError, ConnectionError)
    )

def invoke_agent_with_retry(
    messages,
    config,
    max_retries=2
):
    for attempt in range(max_retries + 1):
        try:
            return agent.invoke(
                messages,
                config=config
            )
        except Exception as e:
            if not is_retryable_error(e):
                raise

            if attempt == max_retries:
                raise

            wait_seconds = attempt + 1
            time.sleep(wait_seconds)



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

    request_id = create_request_id()
    start_time = perf_counter()

    log_request_event(
        "request_start",
        request_id,
        request.thread_id
    )
    try:
        result= invoke_agent_with_retry(
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
    except Exception as e:
        elapsed_ms=round( (perf_counter()-start_time)*1000, 2 )
        log_request_event(
            "request_end",
            request_id,
            request.thread_id,
            elapsed_ms=elapsed_ms,
            success=False,
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=500,
            detail={
                "message":"Agent 执行失败",
                "request_id":request_id
            }
        ) from e

    elapsed_ms = round( (perf_counter()-start_time)*1000 , 2 )
    log_request_event(
        "request_end",
        request_id,
        request.thread_id,
        elapsed_ms=elapsed_ms,
        success=True
    )


    return{
        "thread_id":request.thread_id,
        "answer":result["messages"][-1].content,
        "request_id":request_id
    }




def agent_event_generator(
        request:ChatRequest,
        request_id:str,
        start_time: float
        ):
    try:
        for chunk in agent.stream(
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
        ):
           tools_result = chunk.get("tools")
           if tools_result:
               tool_messages = tools_result.get("messages",[])

               for tool_message in tool_messages:
                   log_request_event(
                       "tool_end",
                       request_id,
                       request.thread_id,
                       tool_name=getattr(tool_message,"name","unknown"),
                       success=True
                   )

            
           model_result = chunk.get("model")       
           if not model_result:
               continue

           messages = model_result.get("messages",[])

           if not messages:
               continue

           message = messages[-1]
           content = getattr(message,"content","")
           tool_calls = getattr(message, "tool_calls",[])
               

           if content and not tool_calls:
               yield f"data: {json.dumps({'type': 'token', 'content': content, 'thread_id': request.thread_id}, ensure_ascii=False)}\n\n"
    except Exception as e:
        elapsed_ms = round(
            (perf_counter() - start_time) * 1000,
            2
        )

        log_request_event(
            "request_end",
            request_id,
            request.thread_id,
            elapsed_ms=elapsed_ms,
            success=False,
            error_type=type(e).__name__
        )
        yield f"data: {json.dumps({'type': 'error', 'content': 'Agent 执行失败', 'thread_id': request.thread_id}, ensure_ascii=False)}\n\n"
        return  #阻止异常后继续发送成功日志和 [DONE]

    elapsed_ms = round(
        (perf_counter() - start_time) * 1000,
        2
    )

    log_request_event(
        "request_end",
        request_id,
        request.thread_id,
        elapsed_ms=elapsed_ms,
        success=True
    )
    yield f"data: {json.dumps({'type': 'done', 'content': '', 'thread_id': request.thread_id}, ensure_ascii=False)}\n\n"   



@app.post("/chat/stream")
def chat_stream(request:ChatRequest):
    request_id = create_request_id()
    start_time = perf_counter()

    log_request_event(
        "request_start",
        request_id,
        request.thread_id
    )

    return StreamingResponse(
        agent_event_generator(request=request,request_id=request_id,start_time=start_time),
        media_type="text/event-stream"
    )


渗滤