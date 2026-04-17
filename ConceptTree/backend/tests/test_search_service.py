import pytest

from services.search_service import SearchService, SearchServiceError


class MockResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class MockAsyncClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, headers=None, json=None):
        self.calls.append({"url": url, "headers": headers, "json": json})
        return MockResponse(self.payload)


@pytest.mark.asyncio
async def test_search_service_formats_tavily_results():
    payload = {
        "results": [
            {
                "title": "Layer Normalization",
                "url": "https://example.com/layernorm",
                "content": "A normalization technique used in deep learning.",
            }
        ]
    }
    client = MockAsyncClient(payload)
    service = SearchService(
        enabled=True,
        provider="tavily",
        api_key="tvly-test",
        allowed_domains=["example.com"],
        client_factory=lambda **_kwargs: client,
    )

    results = await service.search("what is layer normalization")

    assert results == [
        {
            "title": "Layer Normalization",
            "url": "https://example.com/layernorm",
            "snippet": "A normalization technique used in deep learning.",
            "source": "example.com",
        }
    ]
    assert client.calls[0]["json"]["include_domains"] == ["example.com"]


@pytest.mark.asyncio
async def test_search_service_raises_when_disabled():
    service = SearchService(enabled=False, api_key="")

    with pytest.raises(SearchServiceError):
        await service.search("latest transformer paper")
