"""Claude (Anthropic) LLM adapter."""

from typing import AsyncGenerator
from app.core.llm.base import BaseLLM
from app.config import settings


class ClaudeLLM(BaseLLM):
    def __init__(self):
        import anthropic
        self.client = anthropic.AsyncAnthropic(api_key=settings.CLAUDE_API_KEY)
        self.model = settings.CLAUDE_MODEL

    async def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        messages = [{"role": "user", "content": prompt}]
        response = await self.client.messages.create(
            model=self.model, max_tokens=4096, system=system or "你是律所AI助手。", messages=messages, **kwargs,
        )
        return response.content[0].text

    async def stream(self, prompt: str, system: str = "", **kwargs) -> AsyncGenerator[str, None]:
        messages = [{"role": "user", "content": prompt}]
        async with self.client.messages.stream(
            model=self.model, max_tokens=4096, system=system or "你是律所AI助手。", messages=messages, **kwargs,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    def get_model_name(self) -> str:
        return self.model
