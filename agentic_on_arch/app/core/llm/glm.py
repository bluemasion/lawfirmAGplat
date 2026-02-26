"""GLM-4 (ZhipuAI / 智谱) LLM adapter."""

from typing import AsyncGenerator
from app.core.llm.base import BaseLLM
from app.config import settings


class GLMLLM(BaseLLM):
    def __init__(self):
        from zhipuai import ZhipuAI
        self.client = ZhipuAI(api_key=settings.GLM_API_KEY)
        self.model = settings.GLM_MODEL

    async def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system or "你是律所AI助手。"},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content

    async def stream(self, prompt: str, system: str = "", **kwargs) -> AsyncGenerator[str, None]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system or "你是律所AI助手。"},
                {"role": "user", "content": prompt},
            ],
            stream=True,
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def get_model_name(self) -> str:
        return self.model
