"""Qwen (DashScope / 通义千问) LLM adapter."""

from typing import AsyncGenerator
from app.core.llm.base import BaseLLM
from app.config import settings


class QwenLLM(BaseLLM):
    def __init__(self):
        import dashscope
        dashscope.api_key = settings.QWEN_API_KEY
        self.model = settings.QWEN_MODEL

    async def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        from dashscope import Generation
        response = Generation.call(
            model=self.model,
            messages=[
                {"role": "system", "content": system or "你是律所AI助手。"},
                {"role": "user", "content": prompt},
            ],
            result_format="message",
        )
        return response.output.choices[0].message.content

    async def stream(self, prompt: str, system: str = "", **kwargs) -> AsyncGenerator[str, None]:
        from dashscope import Generation
        responses = Generation.call(
            model=self.model,
            messages=[
                {"role": "system", "content": system or "你是律所AI助手。"},
                {"role": "user", "content": prompt},
            ],
            result_format="message",
            stream=True,
            incremental_output=True,
        )
        for response in responses:
            if response.output and response.output.choices:
                yield response.output.choices[0].message.content

    def get_model_name(self) -> str:
        return self.model
