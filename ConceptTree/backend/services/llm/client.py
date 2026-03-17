"""Unified LLM Client with retry and fallback support"""

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
        self.max_retries = settings.LLM_MAX_RETRIES

    def _create_primary_provider(self) -> OpenAICompatibleProvider:
        """Create primary LLM provider"""
        return OpenAICompatibleProvider(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL if settings.LLM_BASE_URL else None,
            model=settings.LLM_MODEL,
            timeout=settings.LLM_TIMEOUT,
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

    async def chat(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        response_format: Optional[Dict] = None,
        use_fallback: bool = False,
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

        for attempt in range(self.max_retries):
            try:
                response = await provider.chat(
                    messages=messages, temperature=temp, response_format=response_format
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
                    use_fallback=True,
                )
            except Exception:
                pass

        raise LLMServiceError(
            f"LLM request failed after {self.max_retries} retries: {str(last_error)}"
        )

    async def chat_json(
        self, system_prompt: str, user_prompt: str, temperature: Optional[float] = None
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
        )

        try:
            return json.loads(response.content)
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


async def close_llm_client():
    """Close LLM client connections"""
    global _llm_client
    _llm_client = None
