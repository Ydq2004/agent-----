import pytest

from langchain.agents.middleware import ToolRetryMiddleware
from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest
from langchain.agents.middleware import ModelRetryMiddleware
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.messages import AIMessage


def make_tool_request(tool_name):
    return ToolCallRequest(
        tool_call={
            "name": tool_name,
            "args": {},
            "id": f"call-{tool_name}",
            "type": "tool_call",
        },
        tool=None,
        state={},
        runtime=None,
    )


def test_read_tool_retries_timeout_once():
    middleware = ToolRetryMiddleware(
        tools=["search_memory"],
        max_retries=1,
        retry_on=(TimeoutError,),
        backoff_factor=0,
        initial_delay=0,
        jitter=False,
    )

    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1

        if calls == 1:
            raise TimeoutError("temporary failure")

        return ToolMessage(
            content="查询成功",
            name="search_memory",
            tool_call_id=request.tool_call["id"],
        )

    result = middleware.wrap_tool_call(
        make_tool_request("search_memory"),
        handler,
    )

    assert result.content == "查询成功"
    assert calls == 2


def test_write_tool_is_not_retried():
    middleware = ToolRetryMiddleware(
        tools=["search_memory"],
        max_retries=1,
        retry_on=(TimeoutError,),
        backoff_factor=0,
        initial_delay=0,
        jitter=False,
    )

    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        raise TimeoutError("temporary failure")

    with pytest.raises(TimeoutError):
        middleware.wrap_tool_call(
            make_tool_request("tool_write_file"),
            handler,
        )

    assert calls == 1

def test_model_retry_retries_timeout_once():
    middleware = ModelRetryMiddleware(
        max_retries=1,
        retry_on=(TimeoutError,),
        on_failure="error",
        backoff_factor=0,
        initial_delay=0,
        jitter=False,
    )

    request = ModelRequest(
        model=None,
        messages=[],
        state={},
    )

    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1

        if calls == 1:
            raise TimeoutError("temporary model failure")

        return ModelResponse(
            result=[AIMessage(content="模型成功返回")],
        )

    result = middleware.wrap_model_call(request, handler)

    assert result.result[-1].content == "模型成功返回"
    assert calls == 2

def test_model_retry_does_not_retry_value_error():
    middleware = ModelRetryMiddleware(
        max_retries=1,
        retry_on=(TimeoutError,),
        on_failure="error",
        backoff_factor=0,
        initial_delay=0,
        jitter=False,
    )

    request = ModelRequest(
        model=None,
        messages=[],
        state={},
    )

    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        raise ValueError("invalid model input")

    with pytest.raises(ValueError):
        middleware.wrap_model_call(request, handler)

    assert calls == 1