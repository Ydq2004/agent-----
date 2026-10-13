"""结构化响应模型测试。"""

import pytest
from pydantic import ValidationError

from response_models import StructuredAgentResponse


def test_structured_response_accepts_valid_payload():
    result = StructuredAgentResponse(
        answer="已查询到相关记忆。",
        intent="memory",
        memory_candidates=["用户偏好"],
        need_tool=True,
    )

    assert result.answer == "已查询到相关记忆。"
    assert result.intent == "memory"
    assert result.memory_candidates == ["用户偏好"]
    assert result.need_tool is True


def test_memory_candidates_default_to_empty_list():
    result = StructuredAgentResponse(
        answer="这是普通问答。",
        intent="general",
        need_tool=False,
    )

    assert result.memory_candidates == []


@pytest.mark.parametrize("field", ["answer", "intent", "need_tool"])
def test_required_fields_are_enforced(field):
    payload = {
        "answer": "回答",
        "intent": "general",
        "need_tool": False,
    }
    payload.pop(field)

    with pytest.raises(ValidationError):
        StructuredAgentResponse.model_validate(payload)


def test_empty_answer_and_unknown_fields_are_rejected():
    with pytest.raises(ValidationError):
        StructuredAgentResponse(
            answer="",
            intent="general",
            need_tool=False,
        )

    with pytest.raises(ValidationError):
        StructuredAgentResponse(
            answer="回答",
            intent="general",
            need_tool=False,
            unexpected="value",
        )
