from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from services.llm.providers import LLMMessage
from services.llm.providers.openai_compatible import OpenAICompatibleProvider


@pytest.mark.asyncio
async def test_kimi_k3_uses_supported_completion_parameters():
    provider = OpenAICompatibleProvider(
        api_key="test-key",
        base_url="https://api.moonshot.cn/v1",
        model="kimi-k3",
        reasoning_effort="low",
    )
    provider.client.chat.completions.create = AsyncMock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="ok"),
                    finish_reason="stop",
                )
            ],
            usage=None,
            model="kimi-k3",
        )
    )

    await provider.chat(
        [LLMMessage(role="user", content="hello")],
        temperature=0.3,
        max_tokens=800,
    )

    request = provider.client.chat.completions.create.await_args.kwargs
    assert request["model"] == "kimi-k3"
    assert request["max_completion_tokens"] == 800
    assert "max_tokens" not in request
    assert "temperature" not in request
    assert request["reasoning_effort"] == "low"


@pytest.mark.asyncio
async def test_kimi_k3_stream_uses_supported_completion_parameters():
    async def response_stream():
        yield SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content="ok"))]
        )

    provider = OpenAICompatibleProvider(
        api_key="test-key",
        base_url="https://api.moonshot.cn/v1",
        model="kimi-k3",
        reasoning_effort="low",
    )
    provider.client.chat.completions.create = AsyncMock(
        return_value=response_stream()
    )

    chunks = [
        chunk
        async for chunk in provider.chat_stream(
            [LLMMessage(role="user", content="hello")],
            temperature=0.3,
            max_tokens=800,
        )
    ]

    request = provider.client.chat.completions.create.await_args.kwargs
    assert chunks == ["ok"]
    assert request["max_completion_tokens"] == 800
    assert "max_tokens" not in request
    assert "temperature" not in request
    assert request["reasoning_effort"] == "low"
