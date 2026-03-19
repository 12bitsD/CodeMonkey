"""Concrete LLM provider using the OpenAI Python SDK.

Works with any OpenAI-compatible API endpoint by pointing the SDK's
``base_url`` at the desired host.  Tested with Kimi 2.5 (Moonshot AI) and
standard OpenAI endpoints.  Supports JSON mode via
``response_format={"type": "json_object"}``.

Primary reader: backend developer configuring a new API endpoint or debugging
provider-level errors (timeouts, quota limits, authentication failures).

Key things to understand:
  1. **Endpoint flexibility** — set ``base_url`` to target any OpenAI-
     compatible service; omit it (``None``) to use the standard OpenAI API.
  2. **Two error types** — :class:`LLMTimeoutError` (retryable, triggers the
     client's backoff loop) vs :class:`LLMProviderError` (API or logic error,
     may carry an HTTP ``status_code`` for diagnosis).
  3. **JSON mode** — ``response_format={"type": "json_object"}`` is passed
     through to the SDK; both Kimi 2.5 and OpenAI honour this flag.
"""

from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI, APIError, Timeout

from .base import BaseLLMProvider, LLMMessage, LLMResponse


class OpenAICompatibleProvider(BaseLLMProvider):
    """LLM provider implemented with the ``openai`` async SDK.

    Accepts any OpenAI-compatible endpoint (OpenAI, Kimi 2.5, local proxies)
    by pointing the ``openai.AsyncOpenAI`` client at the desired ``base_url``.
    An ``AsyncOpenAI`` client is created once at instantiation and reused for
    all subsequent requests, sharing its internal HTTP connection pool.

    Errors from the SDK are mapped to two provider-level exception types so
    the client layer can decide whether to retry:

    - :class:`LLMTimeoutError` — on SDK ``Timeout``; always retryable.
    - :class:`LLMProviderError` — on SDK ``APIError`` or unexpected response
      shape; carries the HTTP ``status_code`` when available.
    """

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: str = "",
        timeout: int = 30,
    ):
        """Initialise the provider and create the async OpenAI SDK client.

        Args:
            api_key: API authentication key for the LLM endpoint.
            base_url: Custom endpoint URL (e.g. Kimi's
                ``https://api.moonshot.cn/v1``).  ``None`` uses the default
                OpenAI API endpoint.
            model: Model identifier to pass in every request
                (e.g. ``"moonshot-v1-8k"``).
            timeout: Request timeout in seconds; the SDK raises ``Timeout``
                after this many seconds, which becomes :class:`LLMTimeoutError`.
        """
        super().__init__(api_key, base_url, model, timeout)

        client_kwargs = {
            "api_key": api_key,
            "timeout": timeout,
        }
        if base_url:
            client_kwargs["base_url"] = base_url

        self.client = AsyncOpenAI(**client_kwargs)

    def is_available(self) -> bool:
        """Return ``True`` if the API key is configured (non-empty string)."""
        return bool(self.api_key and self.api_key.strip())

    async def chat(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        response_format: Optional[Dict] = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send a chat completion via the OpenAI SDK and return a normalised response.

        Translates :class:`~.base.LLMMessage` objects to the SDK's dict
        format, calls ``client.chat.completions.create``, validates that the
        response has at least one non-null choice, and wraps the result in a
        :class:`~.base.LLMResponse`.

        Kimi 2.5 and OpenAI both support
        ``response_format={"type": "json_object"}`` to guarantee the model
        replies with valid JSON — pass this when you need structured output.

        Args:
            messages: Ordered list of :class:`~.base.LLMMessage` objects.
            temperature: Sampling temperature for this request.
            response_format: Optional structured-output flag, e.g.
                ``{"type": "json_object"}``.  Omitted from the SDK call if
                ``None``.
            max_tokens: Maximum tokens to generate in the completion.

        Returns:
            :class:`~.base.LLMResponse` with ``content``, ``usage`` dict
            (``prompt_tokens``, ``completion_tokens``, ``total_tokens``),
            ``model`` name, and ``finish_reason``.

        Raises:
            LLMTimeoutError: The SDK raised ``openai.Timeout`` — the request
                took longer than ``self.timeout`` seconds.
            LLMProviderError: The SDK raised ``openai.APIError``, the
                response had no choices, or the choice content was ``None``.
        """
        try:
            openai_messages = [
                {"role": msg.role, "content": msg.content} for msg in messages
            ]

            request_kwargs = {
                "model": self.model,
                "messages": openai_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if response_format:
                request_kwargs["response_format"] = response_format

            response = await self.client.chat.completions.create(**request_kwargs)

            # Validate response
            if not response.choices:
                raise LLMProviderError("Empty response from API")
            content = response.choices[0].message.content
            if content is None:
                raise LLMProviderError("API returned empty content")

            return LLMResponse(
                content=content,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
                if response.usage
                else None,
                model=response.model,
                finish_reason=response.choices[0].finish_reason,
            )

        except Timeout:
            raise LLMTimeoutError(f"Request timed out after {self.timeout}s")
        except APIError as e:
            raise LLMProviderError(f"API error: {e.message}", status_code=e.status_code)
        except Exception as e:
            raise LLMProviderError(f"Unexpected error: {str(e)}")


class LLMProviderError(Exception):
    """Raised when the LLM API returns an error or an unexpected response.

    Carries an optional ``status_code`` (HTTP status from the API) that
    callers can inspect to distinguish authentication errors (401/403) from
    quota errors (429) and server errors (5xx).
    """

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class LLMTimeoutError(Exception):
    """Raised when the LLM API request exceeds the configured timeout.

    Always treated as retryable by
    :class:`~services.llm.client.UnifiedLLMClient` — the client will wait
    ``2^attempt`` seconds and try again up to ``max_retries`` times.
    """

    pass
