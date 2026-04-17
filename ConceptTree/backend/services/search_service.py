"""Web search service used by the AI learning assistant."""

from __future__ import annotations

import logging
import time
from typing import Callable, Optional
from urllib.parse import urlparse

import httpx

from config import get_search_allowed_domains, settings

logger = logging.getLogger(__name__)


class SearchServiceError(Exception):
    """Raised when the search provider fails."""


class SearchService:
    def __init__(
        self,
        *,
        enabled: Optional[bool] = None,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        max_results: Optional[int] = None,
        allowed_domains: Optional[list[str]] = None,
        cache_ttl_seconds: Optional[int] = None,
        client_factory: Optional[Callable[..., httpx.AsyncClient]] = None,
    ) -> None:
        self.enabled = settings.SEARCH_ENABLED if enabled is None else enabled
        self.provider = (provider or settings.SEARCH_PROVIDER).strip().lower()
        self.api_key = api_key if api_key is not None else settings.SEARCH_API_KEY
        self.timeout = timeout if timeout is not None else settings.SEARCH_TIMEOUT
        self.max_results = (
            max_results if max_results is not None else settings.SEARCH_MAX_RESULTS
        )
        self.allowed_domains = (
            get_search_allowed_domains() if allowed_domains is None else allowed_domains
        )
        self.cache_ttl_seconds = (
            cache_ttl_seconds
            if cache_ttl_seconds is not None
            else settings.SEARCH_CACHE_TTL_SECONDS
        )
        self._cache: dict[tuple[str, tuple[str, ...]], tuple[float, list[dict]]] = {}
        self._client_factory = client_factory or httpx.AsyncClient

    def is_available(self) -> bool:
        return self.enabled and self.provider == "tavily" and bool(self.api_key)

    async def search(self, query: str, *, max_results: Optional[int] = None) -> list[dict]:
        normalized_query = (query or "").strip()
        if not normalized_query:
            return []

        if not self.is_available():
            raise SearchServiceError("Web search is not configured")

        domains = tuple(self.allowed_domains)
        cache_key = (normalized_query, domains)
        cached = self._cache.get(cache_key)
        now = time.time()
        if cached and cached[0] > now:
            return cached[1]

        if self.provider != "tavily":
            raise SearchServiceError(f"Unsupported search provider: {self.provider}")

        results = await self._search_tavily(
            normalized_query,
            max_results=max_results or self.max_results,
            include_domains=list(domains),
        )
        self._cache[cache_key] = (now + self.cache_ttl_seconds, results)
        return results

    async def _search_tavily(
        self,
        query: str,
        *,
        max_results: int,
        include_domains: list[str],
    ) -> list[dict]:
        payload = {
            "query": query,
            "topic": "general",
            "search_depth": "basic",
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False,
        }
        if include_domains:
            payload["include_domains"] = include_domains

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with self._client_factory(
                timeout=self.timeout,
                trust_env=False,
            ) as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as error:
            raise SearchServiceError(f"Search request failed: {error}") from error

        formatted_results = []
        for item in data.get("results", []):
            url = (item.get("url") or "").strip()
            if not url:
                continue
            formatted_results.append(
                {
                    "title": (item.get("title") or "Untitled result").strip(),
                    "url": url,
                    "snippet": (item.get("content") or item.get("snippet") or "").strip(),
                    "source": urlparse(url).netloc or "web",
                }
            )

        return formatted_results


_search_service: Optional[SearchService] = None


def get_search_service() -> SearchService:
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service

