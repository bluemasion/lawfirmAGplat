"""Qwen (DashScope / 通义千问) LLM adapter."""

import asyncio
from typing import AsyncGenerator
from app.core.llm.base import BaseLLM
from app.config import settings


class QwenLLM(BaseLLM):
    def __init__(self):
        import dashscope
        dashscope.api_key = settings.QWEN_API_KEY
        self.model = settings.QWEN_MODEL

    async def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        """Non-streaming generation — run blocking SDK call in a thread."""
        loop = asyncio.get_running_loop()
        def _call():
            from dashscope import Generation
            response = Generation.call(
                model=self.model,
                messages=[
                    {"role": "system", "content": system or "你是律所AI助手。"},
                    {"role": "user", "content": prompt},
                ],
                result_format="message",
            )
            # Safety: check for errors first
            if response.status_code != 200:
                raise RuntimeError(f"Qwen API error {response.status_code}: {response.message}")
            if not response.output:
                raise RuntimeError(f"Qwen returned empty output. Full response: {response}")
            # Handle both response formats:
            # Newer SDK: output.text (choices=null)
            # Older SDK: output.choices[0].message.content
            if response.output.choices:
                return response.output.choices[0].message.content
            if hasattr(response.output, 'text') and response.output.text:
                return response.output.text
            raise RuntimeError(f"Qwen response has no text or choices: {response.output}")
        return await loop.run_in_executor(None, _call)

    async def stream(self, prompt: str, system: str = "", **kwargs) -> AsyncGenerator[str, None]:
        """Streaming generation — offload synchronous SDK iterator to a thread,
        push chunks into an asyncio.Queue so the event loop stays unblocked."""
        queue: asyncio.Queue = asyncio.Queue()
        sentinel = object()  # marks end of stream

        # Capture the running event loop BEFORE entering the background thread
        loop = asyncio.get_running_loop()

        def _stream_in_thread():
            from dashscope import Generation
            try:
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
                    if response.output:
                        if response.output.choices:
                            chunk = response.output.choices[0].message.content
                        elif response.output.text:
                            chunk = response.output.text
                        else:
                            continue
                        loop.call_soon_threadsafe(queue.put_nowait, chunk)
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, f"[错误] {str(e)}")
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, sentinel)

        # Start blocking iteration in background thread
        loop.run_in_executor(None, _stream_in_thread)

        # Yield chunks as they arrive
        while True:
            item = await queue.get()
            if item is sentinel:
                break
            yield item

    def get_model_name(self) -> str:
        return self.model

