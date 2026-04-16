"""OpenAI SDK compatible provider (works with Kimi, OpenAI, etc.)"""

from typing import List, Dict, Any, Optional, AsyncGenerator
import httpx
from openai import AsyncOpenAI, APIConnectionError, APIError, APITimeoutError

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
            # Ignore broken system proxy variables like HTTP_PROXY=127.0.0.1:9.
            "http_client": httpx.AsyncClient(timeout=timeout, trust_env=False),
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
        model: Optional[str] = None,
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
                "model": model or self.model,
                "messages": openai_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if response_format:
                request_kwargs["response_format"] = response_format

            try:
                response = await self.client.chat.completions.create(**request_kwargs)
            except APIError as e:
                # Some models (e.g. kimi-k2.5) only accept temperature=1
                if e.status_code == 400 and "temperature" in str(e).lower():
                    request_kwargs["temperature"] = 1
                    response = await self.client.chat.completions.create(**request_kwargs)
                else:
                    raise

            # Validate response
            if not response.choices:
                raise LLMProviderError("Empty response from API")
            content = response.choices[0].message.content
            if content is None or content.strip() == "":
                finish_reason = response.choices[0].finish_reason
                raise LLMProviderError(
                    f"API returned empty content (finish_reason={finish_reason}). "
                    "Possible causes: max_tokens too low for reasoning model."
                )

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

        except APITimeoutError:
            raise LLMTimeoutError(f"Request timed out after {self.timeout}s")
        except APIConnectionError as e:
            raise LLMProviderError(f"Connection error: {str(e)}")
        except APIError as e:
            raise LLMProviderError(f"API error: {e.message}", status_code=e.status_code)
        except Exception as e:
            raise LLMProviderError(f"Unexpected error: {str(e)}")


    async def chat_stream(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion using OpenAI SDK, yielding text chunks."""
        try:
            openai_messages = [
                {"role": msg.role, "content": msg.content} for msg in messages
            ]
            stream = await self.client.chat.completions.create(
                model=model or self.model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
        except APITimeoutError:
            raise LLMTimeoutError(f"Stream request timed out after {self.timeout}s")
        except APIConnectionError as e:
            raise LLMProviderError(f"Connection error during stream: {str(e)}")
        except APIError as e:
            raise LLMProviderError(f"API error during stream: {e.message}", status_code=e.status_code)
        except Exception as e:
            raise LLMProviderError(f"Unexpected error during stream: {str(e)}")


class LLMProviderError(Exception):
    """LLM provider specific error"""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class LLMTimeoutError(Exception):
    """LLM request timeout"""

    pass
