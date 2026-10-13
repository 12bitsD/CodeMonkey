import pytest

from services.llm.client import UnifiedLLMClient
from services.llm.providers import LLMMessage, LLMResponse


class _Provider:
    timeout = 10

    def is_available(self):
        return True

    async def chat(self, **_kwargs):
        return LLMResponse(
            content="answer",
            usage={"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
        )


@pytest.mark.no_db
@pytest.mark.asyncio
async def test_successful_chat_emits_usage_without_content(monkeypatch):
    client = UnifiedLLMClient.__new__(UnifiedLLMClient)
    client.primary = _Provider()
    client.fallback = None
    client.max_retries = 1
    events = []
    monkeypatch.setattr("services.llm.client.emit_trace_event", lambda **event: events.append(event))

    response = await client.chat([LLMMessage(role="user", content="private prompt")])

    assert response.content == "answer"
    assert events[0]["input_tokens"] == 11
    assert events[0]["output_tokens"] == 7
    assert "private prompt" not in str(events[0])
