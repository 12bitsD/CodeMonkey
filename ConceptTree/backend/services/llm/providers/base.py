"""Abstract contract and shared data classes for all LLM providers.

Defines the three building blocks every provider implementation must use:

- :class:`LLMMessage` — a vendor-neutral chat message (role + content).
- :class:`LLMResponse` — a vendor-neutral completion response.
- :class:`BaseLLMProvider` — the abstract base class that concrete providers
  (e.g. :class:`~openai_compatible.OpenAICompatibleProvider`) must subclass.

Primary reader: backend developer adding a new LLM provider (e.g. Anthropic,
Gemini) — subclass :class:`BaseLLMProvider` and implement ``chat()`` and
``is_available()``.

Key things to understand:
  1. :class:`LLMMessage` and :class:`LLMResponse` are the only message formats
     used anywhere in the LLM stack — providers must translate to/from their
     vendor SDK types internally.
  2. Passing ``response_format={"type": "json_object"}`` to ``chat()`` enables
     JSON mode on supporting endpoints; providers that don't support it should
     ignore this parameter gracefully.
  3. The ``timeout`` field is stored on the provider so each subclass can
     apply it to its own SDK client.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class LLMMessage:
    """A single message in a chat conversation.

    Wraps the universal ``role`` / ``content`` structure used by all
    OpenAI-compatible APIs.  Roles are ``"system"``, ``"user"``, or
    ``"assistant"``.
    """

    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMResponse:
    """A vendor-neutral wrapper around an LLM completion response.

    Concrete providers are responsible for mapping their SDK response to this
    structure.  ``usage`` and ``model`` may be ``None`` if the provider does
    not return them.
    """

    content: str
    usage: Optional[Dict[str, int]] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None


class BaseLLMProvider(ABC):
    """Abstract base class that all LLM provider implementations must subclass.

    Defines the two methods the client layer depends on — :meth:`chat` and
    :meth:`is_available` — and stores the four standard configuration
    attributes shared by every provider.

    Subclassing guide:
    1. Call ``super().__init__(api_key, base_url, model, timeout)`` to store
       the config attributes.
    2. Implement :meth:`is_available` to check whether the provider is
       properly configured (typically checks that ``api_key`` is non-empty).
    3. Implement :meth:`chat` to call the vendor SDK, convert the vendor
       response to :class:`LLMResponse`, and raise
       :class:`~openai_compatible.LLMTimeoutError` on timeout or
       :class:`~openai_compatible.LLMProviderError` on API errors.
    """

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: str = "",
        timeout: int = 30,
    ):
        """Store shared configuration used by all provider implementations.

        Args:
            api_key: Authentication key for the LLM provider API.
            base_url: Override the default API endpoint URL.  Pass ``None``
                to use the provider SDK's default (e.g. ``api.openai.com``).
            model: Model identifier string (e.g. ``"gpt-4o"``).
            timeout: Request timeout in seconds applied to every API call.
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = timeout

    @abstractmethod
    async def chat(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        response_format: Optional[Dict] = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send a chat completion request and return a vendor-neutral response.

        Implementations must translate ``messages`` to the vendor SDK format,
        make the async API call, and wrap the result in :class:`LLMResponse`.

        Args:
            messages: Ordered list of :class:`LLMMessage` objects (typically
                ``system`` first, then ``user``).
            temperature: Sampling temperature; 0.0 is deterministic,
                higher values increase randomness.
            response_format: Optional structured-output hint, e.g.
                ``{"type": "json_object"}`` to request a JSON response.
                Providers that do not support this may ignore it.
            max_tokens: Maximum number of tokens to generate.

        Returns:
            :class:`LLMResponse` with the model's reply and optional metadata.

        Raises:
            LLMTimeoutError: The request exceeded the configured timeout.
            LLMProviderError: The API returned an error or an unexpected
                response shape.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Return ``True`` if this provider is configured and ready to use.

        Typically checks that :attr:`api_key` is non-empty.  Used by
        :class:`~services.llm.client.UnifiedLLMClient` to decide whether to
        route a request to this provider or skip to the fallback.
        """
        pass
