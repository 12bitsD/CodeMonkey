"""Abstract base class for LLM providers"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class LLMMessage:
    """Standardized message format"""

    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMResponse:
    """Standardized response format"""

    content: str
    usage: Optional[Dict[str, int]] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None


class BaseLLMProvider(ABC):
    """Abstract base for LLM providers"""

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: str = "",
        timeout: int = 30,
    ):
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
        """
        Send chat completion request.

        Args:
            messages: List of messages
            temperature: Sampling temperature
            response_format: Optional JSON schema for structured output

        Returns:
            LLMResponse with content and metadata
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is properly configured and available"""
        pass
