import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.llm.client import LLMServiceError, UnifiedLLMClient
from services.llm.providers.openai_compatible import LLMProviderError


class _FakeProvider:
    def __init__(self, chunks=None, error=None):
        self._chunks = chunks or []
        self._error = error

    def is_available(self):
        return True

    async def chat_stream(self, **_kwargs):
        if self._error:
            raise self._error
        for chunk in self._chunks:
            yield chunk


class _PartialFailureProvider:
    def is_available(self):
        return True

    async def chat_stream(self, **_kwargs):
        yield "partial"
        raise LLMProviderError("primary stream broke after emitting")


async def _collect_chunks(async_gen):
    chunks = []
    async for chunk in async_gen:
        chunks.append(chunk)
    return chunks


def test_chat_stream_falls_back_before_first_chunk():
    client = UnifiedLLMClient.__new__(UnifiedLLMClient)
    client.primary = _FakeProvider(error=LLMProviderError("primary unavailable"))
    client.fallback = _FakeProvider(chunks=["hello", " world"])
    client.max_retries = 3

    chunks = asyncio.run(_collect_chunks(client.chat_stream(messages=[])))

    assert "".join(chunks) == "hello world"


def test_chat_stream_does_not_switch_provider_after_partial_output():
    client = UnifiedLLMClient.__new__(UnifiedLLMClient)
    client.primary = _PartialFailureProvider()
    client.fallback = _FakeProvider(chunks=["fallback"])
    client.max_retries = 3

    with pytest.raises(LLMServiceError, match="primary stream broke after emitting"):
        asyncio.run(_collect_chunks(client.chat_stream(messages=[])))
