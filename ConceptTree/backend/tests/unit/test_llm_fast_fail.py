import pytest

from services.llm.client import LLMServiceError, UnifiedLLMClient
from services.llm.providers import LLMMessage, LLMResponse
from services.llm.providers.openai_compatible import LLMProviderError

pytestmark = pytest.mark.no_db


class _AuthFailProvider:
    def __init__(self):
        self.calls = 0

    def is_available(self):
        return True

    async def chat(self, *args, **kwargs):
        self.calls += 1
        raise LLMProviderError("Invalid API Key", status_code=401)


class _TimeoutProvider:
    def __init__(self):
        self.calls = 0

    def is_available(self):
        return True

    async def chat(self, *args, **kwargs):
        self.calls += 1
        raise LLMProviderError("temporary outage", status_code=500)


class _SlowProvider:
    def __init__(self, timeout=0.01):
        self.calls = 0
        self.timeout = timeout

    def is_available(self):
        return True

    async def chat(self, *args, **kwargs):
        self.calls += 1
        await __import__("asyncio").sleep(10)
        return None


@pytest.mark.asyncio
async def test_auth_error_does_not_retry_or_sleep(monkeypatch):
    provider = _AuthFailProvider()
    client = UnifiedLLMClient.__new__(UnifiedLLMClient)
    client.primary = provider
    client.fallback = None
    client.max_retries = 3

    async def fail_sleep(_seconds):
        raise AssertionError("auth failures should not back off and retry")

    monkeypatch.setattr("services.llm.client.asyncio.sleep", fail_sleep)

    with pytest.raises(LLMServiceError, match="Invalid API Key"):
        await client.chat([LLMMessage(role="user", content="hi")])

    assert provider.calls == 1


@pytest.mark.asyncio
async def test_retryable_provider_error_still_retries(monkeypatch):
    provider = _TimeoutProvider()
    client = UnifiedLLMClient.__new__(UnifiedLLMClient)
    client.primary = provider
    client.fallback = None
    client.max_retries = 2
    sleeps = []

    async def record_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr("services.llm.client.asyncio.sleep", record_sleep)

    with pytest.raises(LLMServiceError, match="temporary outage"):
        await client.chat([LLMMessage(role="user", content="hi")])

    assert provider.calls == 2
    assert sleeps == [1]


@pytest.mark.asyncio
async def test_provider_call_is_hard_capped_by_provider_timeout(monkeypatch):
    provider = _SlowProvider(timeout=0.01)
    client = UnifiedLLMClient.__new__(UnifiedLLMClient)
    client.primary = provider
    client.fallback = None
    client.max_retries = 1

    with pytest.raises(LLMServiceError, match="timed out"):
        await client.chat([LLMMessage(role="user", content="hi")])

    assert provider.calls == 1


@pytest.mark.asyncio
async def test_chat_json_accepts_unescaped_control_characters_from_json_mode():
    client = UnifiedLLMClient.__new__(UnifiedLLMClient)

    async def fake_chat(**_kwargs):
        return LLMResponse(
            content='{"is_correct": true, "feedback": "第一行\n第二行"}',
            model="kimi-k3",
            finish_reason="stop",
        )

    client.chat = fake_chat

    result = await client.chat_json("system", "user")

    assert result == {"is_correct": True, "feedback": "第一行\n第二行"}
