"""Unified LLM Client with retry and fallback support"""

import asyncio
import json
import logging
import time
from typing import List, Dict, Any, Optional, AsyncGenerator

from config import settings
from .providers import (
    OpenAICompatibleProvider,
    LLMMessage,
    LLMResponse,
    LLMProviderError,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)


def _is_non_retryable_provider_error(error: Exception) -> bool:
    status_code = getattr(error, "status_code", None)
    return status_code in {400, 401, 403, 404}


class UnifiedLLMClient:
    """
    Unified client for LLM operations.

    Features:
    - Primary provider with fallback
    - Retry logic with exponential backoff
    - JSON mode support
    - Error handling and normalization
    """

    def __init__(self):
        self.primary = self._create_primary_provider()
        self.fallback = (
            self._create_fallback_provider() if settings.LLM_FALLBACK_ENABLED else None
        )
        self.image = self._create_image_provider()
        self.max_retries = settings.LLM_MAX_RETRIES

    def _create_primary_provider(self) -> OpenAICompatibleProvider:
        """Create primary LLM provider"""
        return OpenAICompatibleProvider(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL if settings.LLM_BASE_URL else None,
            model=settings.LLM_MODEL,
            timeout=settings.LLM_TIMEOUT,
            reasoning_effort=settings.LLM_REASONING_EFFORT,
        )

    def _create_fallback_provider(self) -> Optional[OpenAICompatibleProvider]:
        """Create fallback LLM provider"""
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

    def _create_image_provider(self) -> Optional[OpenAICompatibleProvider]:
        """Create the dedicated image generation provider."""
        if not settings.IMAGE_API_KEY:
            return None

        return OpenAICompatibleProvider(
            api_key=settings.IMAGE_API_KEY,
            base_url=settings.IMAGE_BASE_URL if settings.IMAGE_BASE_URL else None,
            model=settings.IMAGE_MODEL,
            timeout=settings.IMAGE_TIMEOUT,
        )

    async def generate_image(self, prompt: str) -> bytes:
        """Generate an image with the dedicated image provider."""
        if not self.image or not self.image.is_available():
            raise LLMServiceError("Image provider not available")

        return await self.image.generate_image(
            prompt=prompt,
            model=settings.IMAGE_MODEL,
        )

    async def chat(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        response_format: Optional[Dict] = None,
        max_tokens: int = 4096,
        use_fallback: bool = False,
        model: Optional[str] = None,
        max_retries: Optional[int] = None,
    ) -> LLMResponse:
        """
        Send chat completion with retry and fallback.

        Args:
            messages: List of messages
            temperature: Override default temperature
            response_format: JSON schema for structured output
            use_fallback: Force use of fallback provider

        Returns:
            LLMResponse

        Raises:
            LLMServiceError: If all retries and fallback exhausted
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
        retry_count = max_retries if max_retries is not None else self.max_retries

        provider_label = "fallback" if provider is self.fallback else "primary"
        for attempt in range(retry_count):
            start = time.monotonic()
            try:
                provider_timeout = getattr(provider, "timeout", settings.LLM_TIMEOUT)
                try:
                    response = await asyncio.wait_for(
                        provider.chat(
                            messages=messages,
                            temperature=temp,
                            response_format=response_format,
                            max_tokens=max_tokens,
                            model=model,
                        ),
                        timeout=provider_timeout,
                    )
                except asyncio.TimeoutError:
                    raise LLMTimeoutError(
                        f"Request timed out after {provider_timeout}s"
                    )
                duration_ms = int((time.monotonic() - start) * 1000)
                logger.info(
                    "llm_call provider=%s model=%s attempt=%d duration_ms=%d status=ok",
                    provider_label,
                    model or settings.LLM_MODEL,
                    attempt,
                    duration_ms,
                )
                return response

            except (LLMTimeoutError, LLMProviderError) as e:
                duration_ms = int((time.monotonic() - start) * 1000)
                logger.warning(
                    "llm_call provider=%s model=%s attempt=%d duration_ms=%d status=error error=%s",
                    provider_label,
                    model or settings.LLM_MODEL,
                    attempt,
                    duration_ms,
                    e,
                )
                last_error = e
                if _is_non_retryable_provider_error(e):
                    break
                if attempt < retry_count - 1:
                    wait_time = min(2**attempt, 3)
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
                    max_retries=max_retries,
                )
            except Exception as fallback_error:
                # Log fallback failure; will raise original error below
                import logging

                logging.getLogger(__name__).warning(
                    f"Fallback provider also failed: {fallback_error}"
                )

        raise LLMServiceError(
            f"LLM request failed after {retry_count} retries: {str(last_error)}"
        )

    async def chat_stream(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: int = 1024,
        model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion, yielding text chunks.

        If the primary provider fails before emitting any chunk, the client will
        transparently retry the stream using the fallback provider when available.
        """
        providers = []
        if self.primary and self.primary.is_available():
            providers.append(("primary", self.primary))
        if self.fallback and self.fallback.is_available():
            providers.append(("fallback", self.fallback))

        if not providers:
            raise LLMServiceError("No LLM provider available")

        temp = temperature if temperature is not None else settings.LLM_TEMPERATURE
        last_error = None

        for index, (provider_name, provider) in enumerate(providers):
            emitted_any_chunk = False
            try:
                async for chunk in provider.chat_stream(
                    messages=messages,
                    temperature=temp,
                    max_tokens=max_tokens,
                    model=model,
                ):
                    emitted_any_chunk = True
                    yield chunk
                return
            except (LLMTimeoutError, LLMProviderError) as error:
                last_error = error

                has_next_provider = index < len(providers) - 1
                if emitted_any_chunk or not has_next_provider:
                    break

                logger.warning(
                    "Stream chat failed on %s provider before first chunk, trying fallback: %s",
                    provider_name,
                    error,
                )

        raise LLMServiceError(f"LLM stream failed: {last_error}")

    async def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: int = 4096,
        model: Optional[str] = None,
        max_retries: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Convenience method for JSON mode chat.

        Args:
            system_prompt: System message content
            user_prompt: User message content
            temperature: Sampling temperature

        Returns:
            Parsed JSON dict
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
            model=model,
            max_retries=max_retries,
        )

        try:
            return json.loads(response.content, strict=False)
        except json.JSONDecodeError as e:
            raise LLMServiceError(f"Failed to parse JSON response: {e}")


class LLMServiceError(Exception):
    """Unified LLM service error"""

    pass


_llm_client: Optional[UnifiedLLMClient] = None


def get_llm_client() -> UnifiedLLMClient:
    """Get or create LLM client singleton"""
    global _llm_client
    if _llm_client is None:
        _llm_client = UnifiedLLMClient()
    return _llm_client


def close_llm_client():
    """Close LLM client connections"""
    global _llm_client
    _llm_client = None
