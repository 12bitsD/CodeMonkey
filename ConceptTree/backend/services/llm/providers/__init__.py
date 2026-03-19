"""Public exports for the LLM provider layer.

This package implements the provider abstraction that insulates the rest of
the codebase from specific LLM vendor SDKs.  It exposes:

- **Data classes** (:class:`LLMMessage`, :class:`LLMResponse`) — the
  vendor-neutral message and response formats used throughout the LLM stack.
- **Abstract base** (:class:`BaseLLMProvider`) — the contract every concrete
  provider must fulfil (``chat()`` + ``is_available()``).
- **Concrete provider** (:class:`OpenAICompatibleProvider`) — works with any
  OpenAI-compatible endpoint (OpenAI, Kimi 2.5, local proxies).
- **Error classes** (:class:`LLMProviderError`, :class:`LLMTimeoutError`) —
  provider-level exceptions that the client layer converts to retry or fallback
  decisions.

Import from here (or from ``services.llm``) rather than directly from
``base`` or ``openai_compatible``.
"""

from .base import BaseLLMProvider, LLMMessage, LLMResponse
from .openai_compatible import (
    OpenAICompatibleProvider,
    LLMProviderError,
    LLMTimeoutError,
)

__all__ = [
    "BaseLLMProvider",
    "LLMMessage",
    "LLMResponse",
    "OpenAICompatibleProvider",
    "LLMProviderError",
    "LLMTimeoutError",
]
