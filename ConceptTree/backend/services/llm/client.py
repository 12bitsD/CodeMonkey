"""Unified LLM client with automatic retry and optional fallback provider.

This module is the reliability layer of the LLM subsystem.  It wraps the
raw provider (``OpenAICompatibleProvider``) with:

- **Exponential-backoff retry** — up to ``settings.LLM_MAX_RETRIES`` attempts
  on timeout or provider errors; wait time between retries is ``2^attempt``
  seconds (1 s, 2 s, 4 s, …).
- **Automatic fallback** — if every retry on the primary provider fails and a
  fallback provider is configured (``settings.LLM_FALLBACK_ENABLED``), the
  request is tried once more on the fallback before a ``LLMServiceError`` is
  raised.
- **JSON mode helper** — :meth:`UnifiedLLMClient.chat_json` is the method
  used by virtually every caller; it assembles messages, requests
  ``{"type": "json_object"}`` structured output, and parses the response.

Primary reader: backend developer configuring LLM reliability settings or
debugging timeouts and quota errors.
"""

import asyncio
import json
from typing import List, Dict, Any, Optional

from config import settings
from .providers import (
    OpenAICompatibleProvider,
    LLMMessage,
    LLMResponse,
    LLMProviderError,
    LLMTimeoutError,
)


class UnifiedLLMClient:
    """Single async interface for all LLM operations in ConceptTree.

    Abstracts provider differences, retry logic, and fallback routing behind
    two public methods: :meth:`chat` for full control and :meth:`chat_json`
    for the common JSON-structured-response case.

    Reliability features:

    - Primary provider is tried up to ``max_retries`` times with exponential
      backoff (``2^attempt`` seconds) on :class:`~.providers.LLMTimeoutError`
      or :class:`~.providers.LLMProviderError`.
    - If all primary retries fail, the optional fallback provider is tried
      once (no additional retry loop).
    - If both fail, :class:`LLMServiceError` is raised.

    Configuration is read from ``config.settings`` at instantiation time; see
    ``config.py`` for the full list of ``LLM_*`` environment variables.
    """

    def __init__(self):
        """Initialise primary provider and optional fallback from app settings.

        Reads from ``settings``:
        - ``LLM_API_KEY``, ``LLM_BASE_URL``, ``LLM_MODEL``, ``LLM_TIMEOUT``
          for the primary provider.
        - ``LLM_FALLBACK_ENABLED``, ``LLM_FALLBACK_API_KEY``,
          ``LLM_FALLBACK_BASE_URL``, ``LLM_FALLBACK_MODEL`` for the fallback.
        - ``LLM_MAX_RETRIES`` for the retry loop count.
        """
        self.primary = self._create_primary_provider()
        self.fallback = (
            self._create_fallback_provider() if settings.LLM_FALLBACK_ENABLED else None
        )
        self.max_retries = settings.LLM_MAX_RETRIES

    def _create_primary_provider(self) -> OpenAICompatibleProvider:
        """Instantiate the primary LLM provider from app settings."""
        return OpenAICompatibleProvider(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL if settings.LLM_BASE_URL else None,
            model=settings.LLM_MODEL,
            timeout=settings.LLM_TIMEOUT,
        )

    def _create_fallback_provider(self) -> Optional[OpenAICompatibleProvider]:
        """Instantiate the fallback LLM provider, or return ``None`` if unconfigured.

        Returns ``None`` when ``settings.LLM_FALLBACK_API_KEY`` is empty,
        which disables the fallback path in :meth:`chat`.
        """
        if not settings.LLM_FALLBACK_API_KEY:
            return None

        return OpenAICompatibleProvider(
            api_key=settings.LLM_FALLBACK_API_KEY,
            base_url=settings.LLM_FALLBACK_BASE_URL
            if settings.LLM_FALLBACK_BASE_URL
            else None,
            model=settings.LLM_FALLBACK_MODEL,
            timeout=settings.LLM_TIMEOUT,
        )

    async def chat(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        response_format: Optional[Dict] = None,
        max_tokens: int = 4096,
        use_fallback: bool = False,
    ) -> LLMResponse:
        """Send a chat completion with retry-backoff and automatic fallback.

        Retry behaviour (primary provider):

        1. Attempt the request up to ``self.max_retries`` times.
        2. On :class:`~.providers.LLMTimeoutError` or
           :class:`~.providers.LLMProviderError`, wait ``2^attempt`` seconds
           before the next attempt (1 s → 2 s → 4 s …).
        3. If all retries are exhausted and a fallback provider exists, call
           this method recursively with ``use_fallback=True``.
        4. If the fallback also fails, raise :class:`LLMServiceError` with
           the original error from the primary provider.

        Temperature defaults to ``settings.LLM_TEMPERATURE`` when ``None``
        is passed, so callers only need to override it for non-default tasks.

        Args:
            messages: Ordered list of :class:`~.providers.LLMMessage` objects
                (``system`` first, then ``user``).
            temperature: Sampling temperature (0.0 = deterministic, 1.0 =
                creative).  ``None`` falls back to ``settings.LLM_TEMPERATURE``.
            response_format: Optional dict for structured output, e.g.
                ``{"type": "json_object"}`` to enable JSON mode.
            max_tokens: Maximum tokens in the completion.
            use_fallback: Internal flag — forces the fallback provider.
                Do not set this manually; use the retry/fallback path instead.

        Returns:
            :class:`~.providers.LLMResponse` with ``content``, optional
            ``usage`` stats, ``model`` name, and ``finish_reason``.

        Raises:
            LLMServiceError: All retry attempts (and fallback, if configured)
                were exhausted, or no provider is available.
        """
        provider = self.fallback if use_fallback else self.primary

        if not provider or not provider.is_available():
            if use_fallback:
                raise LLMServiceError("Fallback provider not available")
            if self.fallback and self.fallback.is_available():
                provider = self.fallback
            else:
                raise LLMServiceError("No LLM provider available")

        temp = temperature if temperature is not None else settings.LLM_TEMPERATURE
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = await provider.chat(
                    messages=messages,
                    temperature=temp,
                    response_format=response_format,
                    max_tokens=max_tokens,
                )
                return response

            except (LLMTimeoutError, LLMProviderError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                continue

        if not use_fallback and self.fallback:
            try:
                return await self.chat(
                    messages=messages,
                    temperature=temperature,
                    response_format=response_format,
                    max_tokens=max_tokens,
                    use_fallback=True,
                )
            except Exception as fallback_error:
                # Log fallback failure; will raise original error below
                import logging

                logging.getLogger(__name__).warning(
                    f"Fallback provider also failed: {fallback_error}"
                )

        raise LLMServiceError(
            f"LLM request failed after {self.max_retries} retries: {str(last_error)}"
        )

    async def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """Request a JSON-structured LLM response and return it as a parsed dict.

        This is the primary entry point used by
        :class:`~services.ai_service.AIService` for all four learning
        workflows.  It handles message assembly, JSON mode activation, and
        response parsing so callers only deal with plain Python dicts.

        Internally calls :meth:`chat` with ``response_format={"type":
        "json_object"}`` — the provider must support this flag (all
        OpenAI-compatible APIs tested with this project do).

        Args:
            system_prompt: Content of the ``system`` role message — sets the
                LLM's persona and global instructions.
            user_prompt: Content of the ``user`` role message — the specific
                request assembled by :func:`~services.llm.configs.load_ai_config`.
            temperature: Sampling temperature.  ``None`` uses
                ``settings.LLM_TEMPERATURE``.
            max_tokens: Maximum tokens in the completion.

        Returns:
            Parsed JSON dict from the LLM response.

        Raises:
            LLMServiceError: The LLM request failed (see :meth:`chat`), or the
                response content could not be parsed as valid JSON.
        """
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        response = await self.chat(
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
            max_tokens=max_tokens,
        )

        try:
            return json.loads(response.content)
        except json.JSONDecodeError as e:
            raise LLMServiceError(f"Failed to parse JSON response: {e}")


class LLMServiceError(Exception):
    """Raised when the LLM client exhausts all retries and the fallback provider.

    Wraps the last provider-level error message.  Callers (e.g.
    :class:`~services.ai_service.AIService`) catch this and convert it to an
    ``ApiError`` returned in the response body.
    """

    pass


_llm_client: Optional[UnifiedLLMClient] = None


def get_llm_client() -> UnifiedLLMClient:
    """Return the shared :class:`UnifiedLLMClient`, creating it on first call.

    Uses the singleton pattern so the provider's HTTP connection pool (from
    the ``openai`` async client) is initialised once and reused across all
    requests in the process lifetime.

    Returns:
        The application-wide :class:`UnifiedLLMClient` singleton.
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = UnifiedLLMClient()
    return _llm_client


def close_llm_client():
    """Release the shared :class:`UnifiedLLMClient` singleton.

    Drops the reference so the next call to :func:`get_llm_client` creates a
    fresh instance.  Call this during application shutdown or in tests that
    need a clean client state.
    """
    global _llm_client
    _llm_client = None
