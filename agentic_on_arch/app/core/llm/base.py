"""Base LLM interface — all adapters must implement this."""

from abc import ABC, abstractmethod
from typing import AsyncGenerator


class BaseLLM(ABC):
    """Unified interface for all LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        """Generate a complete response (non-streaming)."""
        ...

    @abstractmethod
    async def stream(self, prompt: str, system: str = "", **kwargs) -> AsyncGenerator[str, None]:
        """Generate response chunks for SSE streaming."""
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the current model identifier."""
        ...
