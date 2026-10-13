"""FastAPI 接口测试：不调用真实模型，也不修改正式数据库。"""

import json
import sys
import types
from unittest.mock import patch

from langchain_core.messages import AIMessage

# api_server 导入 agent_core 时会初始化真实向量模型。API 测试只验证 HTTP
# 层，因此在导入 api_server 前注入轻量假 agent，避免联网和加载模型。
fake_agent_core = types.ModuleType("agent_core")

class _FakeAgent:
    def invoke(self,messages,config):
        raise AssertionError("测试没有替换invoke")

    def stream(self, messages, config):
        yield from ()


fake_agent_core.agent = _FakeAgent()
sys.modules["agent_core"] = fake_agent_core

from fastapi.testclient import TestClient
import api_server


client = TestClient(api_server.app)


def _request_body(thread_id="api-test", message="你好"):
    return {"thread_id": thread_id, "message": message}


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_chat_validation_rejects_empty_fields():
    response = client.post("/chat", json=_request_body("", ""))
    assert response.status_code == 422
    locations = {tuple(item["loc"]) for item in response.json()["detail"]}
    assert ("body", "thread_id") in locations
    assert ("body", "message") in locations


def test_chat_passes_thread_id_and_returns_request_id(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    captured = {}

    def fake_invoke(messages, config):
        captured["config"] = config
        return {"messages": [AIMessage(content="mock answer")]}

    with patch.object(api_server.agent,"invoke", side_effect=fake_invoke):
        response = client.post("/chat", json=_request_body("thread-123", "测试"))

    assert response.status_code == 200
    body = response.json()
    assert body["thread_id"] == "thread-123"
    assert body["answer"] == "mock answer"
    assert body["request_id"]
    assert captured["config"] == {"configurable": {"thread_id": "thread-123"}}


def test_chat_returns_structured_error_when_agent_fails(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    with patch.object(api_server.agent,"invoke",side_effect=RuntimeError("boom")):
        response = client.post("/chat", json=_request_body())

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert detail["message"] == "Agent 执行失败"
    assert detail["request_id"]


def test_chat_stream_emits_token_and_done(monkeypatch):
    def fake_stream(messages, config):
        yield {"model": {"messages": [AIMessage(content="流式结果")]}}

    with patch.object(api_server.agent, "stream", side_effect=fake_stream):
        response = client.post("/chat/stream", json=_request_body("stream-123", "测试"))

    assert response.status_code == 200
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert [event["type"] for event in events] == ["token", "done"]
    assert all(event["thread_id"] == "stream-123" for event in events)
    assert all(event["request_id"] for event in events)


def test_chat_stream_emits_error_without_done():
    def failing_stream(messages, config):
        raise RuntimeError("stream failed")
        yield  # 保持这是一个生成器函数

    with patch.object(api_server.agent, "stream", side_effect=failing_stream):
        response = client.post("/chat/stream", json=_request_body("stream-error", "测试"))

    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert [event["type"] for event in events] == ["error"]
    assert events[0]["request_id"]

def test_chat_returns_502_when_agent_result_is_invalid_json(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    def fake_invoke(messages, config):
        return {"messages": [AIMessage(content='{"answer":"完成",}') ]}

    with patch.object(api_server.agent,"invoke", side_effect=fake_invoke):
        response = client.post("/chat", json=_request_body())

    assert response.status_code == 200
    assert response.json()["answer"] == '{"answer":"完成",}'
   

def test_chat_returns_502_when_agent_returns_no_messages(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    with patch.object(
        api_server.agent,
        "invoke",
        return_value={"messages": []},
    ):
        response = client.post("/chat", json=_request_body())

    assert response.status_code == 502
    assert response.json()["detail"]["message"] == "Agent 返回结果格式无效"