"""OpenAI SDK compatible provider (works with Kimi, OpenAI, etc.)"""

from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI, APIError, Timeout

from .base import BaseLLMProvider, LLMMessage, LLMResponse


class OpenAICompatibleProvider(BaseLLMProvider):
    """Provider using OpenAI SDK (compatible with Kimi 2.5)"""

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: str = "",
        timeout: int = 30,
    ):
        super().__init__(api_key, base_url, model, timeout)

        client_kwargs = {
            "api_key": api_key,
            "timeout": timeout,
        }
        if base_url:
            client_kwargs["base_url"] = base_url

        self.client = AsyncOpenAI(**client_kwargs)

    def is_available(self) -> bool:
        """Check if API key is configured"""
        return bool(self.api_key and self.api_key.strip())

    async def chat(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        response_format: Optional[Dict] = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        Send chat completion using OpenAI SDK.

        Kimi 2.5 supports response_format={"type": "json_object"}
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
    """LLM provider specific error"""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class LLMTimeoutError(Exception):
    """LLM request timeout"""

    pass
