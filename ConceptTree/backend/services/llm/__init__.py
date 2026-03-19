"""Public API surface for the LLM subsystem.

Import everything LLM-related from here — do not import directly from the
sub-modules (``client``, ``providers``).  This single import point makes it
easy to swap internals without touching callers.

Usage::

    from services.llm import get_llm_client, LLMServiceError

Exports:

- **Provider layer** (``services.llm.providers``): data classes and the
  concrete OpenAI-compatible provider used to make API calls.
- **Client layer** (``services.llm.client``): the unified client that adds
  retry-with-backoff, fallback provider support, and JSON mode helpers.
"""

from .providers import (
    BaseLLMProvider,
    LLMMessage,
    LLMResponse,
    OpenAICompatibleProvider,
    LLMProviderError,
    LLMTimeoutError,
)
from .client import UnifiedLLMClient, LLMServiceError, get_llm_client, close_llm_client

__all__ = [
    "BaseLLMProvider",
    "LLMMessage",
    "LLMResponse",
    "OpenAICompatibleProvider",
    "LLMProviderError",
    "LLMTimeoutError",
    "UnifiedLLMClient",
    "LLMServiceError",
    "get_llm_client",
    "close_llm_client",
]
