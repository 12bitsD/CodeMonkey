import pytest

from services.llm.client import LLMServiceError, UnifiedLLMClient
from services.llm.providers import LLMMessage
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
