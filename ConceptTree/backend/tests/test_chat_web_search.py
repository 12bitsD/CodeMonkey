import json

import pytest

from models import ChatMessage, ChatRequest
from routers import ai as ai_router


async def _collect_stream(stream):
    chunks = []
    async for item in stream:
        chunks.append(item)
    return "".join(chunks)


def _parse_sse_payload(payload):
    events = []
    for line in payload.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


@pytest.mark.asyncio
async def test_stream_chat_emits_sources_after_chunks(monkeypatch):
    class StubAIService:
        async def prepare_chat_session(self, **_kwargs):
            return {
                "sources": [
                    {
                        "title": "Attention Is All You Need",
                        "url": "https://example.com/paper",
                        "source": "example.com",
                    }
                ],
                "search_status": "done",
            }

        async def stream_chat_session(self, _session):
            yield "first"
            yield " second"

    monkeypatch.setattr(ai_router, "get_ai_service", lambda: StubAIService())

    request = ChatRequest(
        messages=[ChatMessage(role="user", content="latest transformer paper")],
        enableWebSearch=True,
    )

    payload = await _collect_stream(ai_router._stream_chat(request, "user-1"))
    events = _parse_sse_payload(payload)

    assert events[0] == {"type": "search_status", "status": "searching"}
    assert events[1] == {"type": "chunk", "text": "first"}
    assert events[2] == {"type": "chunk", "text": " second"}
    assert events[3]["type"] == "sources"
    assert events[3]["sources"][0]["title"] == "Attention Is All You Need"
    assert events[4] == {"type": "search_status", "status": "done"}
    assert events[-1] == {"type": "done"}


@pytest.mark.asyncio
async def test_stream_chat_falls_back_when_search_has_no_results(monkeypatch):
    class StubAIService:
        async def prepare_chat_session(self, **_kwargs):
            return {"sources": [], "search_status": "fallback"}

        async def stream_chat_session(self, _session):
            yield "plain answer"

    monkeypatch.setattr(ai_router, "get_ai_service", lambda: StubAIService())

    request = ChatRequest(
        messages=[ChatMessage(role="user", content="what is layer norm")],
        enableWebSearch=True,
    )

    payload = await _collect_stream(ai_router._stream_chat(request, "user-1"))
    events = _parse_sse_payload(payload)

    assert events[0] == {"type": "search_status", "status": "searching"}
    assert events[1] == {"type": "chunk", "text": "plain answer"}
    assert events[2] == {"type": "search_status", "status": "fallback"}
