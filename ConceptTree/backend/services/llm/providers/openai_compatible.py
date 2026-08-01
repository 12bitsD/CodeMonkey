"""OpenAI SDK compatible provider (works with MiMo, Kimi, OpenAI, etc.)"""

import base64
from typing import List, Dict, Any, Optional, AsyncGenerator
import httpx
from openai import AsyncOpenAI, APIConnectionError, APIError, APITimeoutError

from .base import BaseLLMProvider, LLMMessage, LLMResponse


class OpenAICompatibleProvider(BaseLLMProvider):
    """Provider using the OpenAI SDK against compatible chat APIs."""

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: str = "",
        timeout: int = 30,
        reasoning_effort: Optional[str] = None,
    ):
        super().__init__(api_key, base_url, model, timeout)
        self.reasoning_effort = reasoning_effort

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
        key = (self.api_key or "").strip()
        return bool(key and not (key.startswith("<<") and key.endswith(">>")))

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

        Compatible models can support response_format={"type": "json_object"}.
        """
        try:
            openai_messages = [
                {"role": msg.role, "content": msg.content} for msg in messages
            ]

            selected_model = model or self.model
            request_kwargs = {
                "model": selected_model,
                "messages": openai_messages,
            }
            if selected_model == "kimi-k3":
                request_kwargs["max_completion_tokens"] = max_tokens
                if self.reasoning_effort:
                    request_kwargs["reasoning_effort"] = self.reasoning_effort
            else:
                request_kwargs["temperature"] = temperature
                request_kwargs["max_tokens"] = max_tokens

            if response_format:
                request_kwargs["response_format"] = response_format

            try:
                response = await self.client.chat.completions.create(**request_kwargs)
            except APITimeoutError:
                raise
            except APIError as e:
                # Some compatible models only accept temperature=1.
                if getattr(e, "status_code", None) == 400 and "temperature" in str(e).lower():
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
            raise LLMProviderError(
                f"API error: {getattr(e, 'message', str(e))}",
                status_code=getattr(e, "status_code", None),
            )
        except Exception as e:
            raise LLMProviderError(f"Unexpected error: {str(e)}")


    async def generate_image(
        self,
        prompt: str,
        *,
        model: str = "openai/gpt-image-2",
        size: str = "1024x1024",
        quality: str = "standard",
    ) -> bytes:
        """Generate an image and return the raw image bytes."""
        if self.base_url and "openrouter.ai" in self.base_url:
            return await self._generate_openrouter_image(
                prompt=prompt,
                model=model,
                size=size,
                quality=quality,
            )

        try:
            response = await self.client.images.generate(
                model=model,
                prompt=prompt,
                n=1,
                size=size,
                response_format="b64_json",
            )
            image = response.data[0]
            b64 = getattr(image, "b64_json", None)
            if b64:
                return base64.b64decode(b64)
            image_url = getattr(image, "url", None)
            if image_url:
                async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
                    downloaded = await client.get(image_url)
                    downloaded.raise_for_status()
                    return downloaded.content
            raise LLMProviderError("Image API returned neither b64_json nor url")
        except APITimeoutError:
            raise LLMProviderError(f"Image generation timed out after {self.timeout}s")
        except APIConnectionError as e:
            raise LLMProviderError(f"Connection error during image generation: {str(e)}")
        except APIError as e:
            raise LLMProviderError(f"Image API error: {e.message}", status_code=e.status_code)
        except Exception as e:
            raise LLMProviderError(f"Unexpected error during image generation: {str(e)}")

    async def _generate_openrouter_image(
        self,
        *,
        prompt: str,
        model: str,
        size: str,
        quality: str,
    ) -> bytes:
        """Call OpenRouter's chat-completions image API."""
        base_url = (self.base_url or "https://openrouter.ai/api/v1").rstrip("/")
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "modalities": ["image", "text"],
            "stream": False,
        }
        image_config: Dict[str, Any] = {}
        image_size = self._openrouter_image_size(size)
        if image_size:
            image_config["image_size"] = image_size
        if quality and quality != "standard":
            image_config["quality"] = quality
        if image_config:
            payload["image_config"] = image_config

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        last_error: Optional[Exception] = None
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
                    response = await client.post(
                        f"{base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()

                message = (data.get("choices") or [{}])[0].get("message") or {}
                images = message.get("images") or []
                if not images:
                    content = str(message.get("content") or "").strip()
                    detail = f": {content[:200]}" if content else ""
                    raise LLMProviderError(
                        f"OpenRouter image response contained no images{detail}"
                    )

                image_url = (images[0].get("image_url") or {}).get("url")
                if not image_url:
                    raise LLMProviderError("OpenRouter image response missing image_url.url")
                return await self._image_url_to_bytes(image_url)
            except httpx.HTTPStatusError as e:
                body = e.response.text[:500] if e.response is not None else ""
                raise LLMProviderError(
                    f"OpenRouter image API error: {body}",
                    status_code=e.response.status_code if e.response is not None else None,
                )
            except httpx.TimeoutException as e:
                last_error = e
                if attempt == 1:
                    raise LLMProviderError(
                        f"OpenRouter image generation timed out after {self.timeout}s"
                    )
            except httpx.RequestError as e:
                last_error = e
                if attempt == 1:
                    raise LLMProviderError(
                        f"Connection error during OpenRouter image generation: {str(e)}"
                    )

        raise LLMProviderError(f"OpenRouter image generation failed: {last_error}")

    async def _image_url_to_bytes(self, image_url: str) -> bytes:
        if image_url.startswith("data:"):
            _, encoded = image_url.split(",", 1)
            return base64.b64decode(encoded)

        async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
            downloaded = await client.get(image_url)
            downloaded.raise_for_status()
            return downloaded.content

    def _openrouter_image_size(self, size: str) -> Optional[str]:
        """Map OpenAI image sizes to OpenRouter's image_size values."""
        if not size:
            return None
        if size in {"0.5K", "1K", "2K", "4K"}:
            return size
        if size in {"512x512", "768x768", "1024x1024"}:
            return "1K"
        if size in {"1536x1536", "2048x2048"}:
            return "2K"
        return None

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
            selected_model = model or self.model
            request_kwargs = {
                "model": selected_model,
                "messages": openai_messages,
                "stream": True,
            }
            if selected_model == "kimi-k3":
                request_kwargs["max_completion_tokens"] = max_tokens
                if self.reasoning_effort:
                    request_kwargs["reasoning_effort"] = self.reasoning_effort
            else:
                request_kwargs["temperature"] = temperature
                request_kwargs["max_tokens"] = max_tokens
            stream = await self.client.chat.completions.create(**request_kwargs)
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
            raise LLMProviderError(
                f"API error during stream: {getattr(e, 'message', str(e))}",
                status_code=getattr(e, "status_code", None),
            )
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
