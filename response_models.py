"""Agent 结构化响应模型。

该模型先作为输出契约使用，Agent 接入和解析放在后续任务中完成。
"""

from pydantic import BaseModel, ConfigDict, Field
import json
from pydantic import ValidationError


class StructuredAgentResponse(BaseModel):
    """Agent 对一次用户请求的结构化判断。"""

    model_config = ConfigDict(extra="forbid")

    answer: str = Field(..., min_length=1, description="给用户展示的最终回答")
    intent: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="请求意图，例如 general、memory、file 或 code",
    )
    memory_candidates: list[str] = Field(
        default_factory=list,
        description="与当前请求相关、可供记忆检索的关键词或短语",
    )
    need_tool: bool = Field(
        ...,
        description="是否需要调用工具才能完成请求",
    )


def normalize_agent_result(raw_result):
  parsed=None
  str_content=None

  if isinstance(raw_result,str):
     try:
        parsed=json.loads(raw_result)
     except json.JSONDecodeError:
        if raw_result.lstrip().startswith(("{","[")):
           raise ValueError("agent结果json格式错误")
        str_content=raw_result

  if parsed is not None:
     try:
        return StructuredAgentResponse.model_validate(parsed)
     except ValidationError  as e:
        raise ValueError(f"agent结果字典校验失败: {e}") from e

  if str_content is not None:
    return StructuredAgentResponse(
            answer= raw_result,
            intent="general",
            memory_candidates=[],
            need_tool=False,
        )  
  
  if isinstance(raw_result,dict):
     try:
        return StructuredAgentResponse.model_validate(raw_result)
     except ValidationError  as e:
        raise ValueError(f"agent结果dict校验:{e}") from e

  raise TypeError(
      f"agent结果类型错误: {type(raw_result).__name__}"
  )
