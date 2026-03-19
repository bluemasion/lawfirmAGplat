"""Local LLM adapter — connects to Ollama or vLLM via OpenAI-compatible API.

Works with:
- Ollama (localhost:11434) — for Mac dev/testing
- vLLM (localhost:8081/8082) — for GB10 production deployment

Both expose the same OpenAI-compatible chat/completions endpoint.
"""

import asyncio
from typing import AsyncGenerator

import httpx

from app.core.llm.base import BaseLLM
from app.utils.logger import logger


class LocalLLM(BaseLLM):
    """Local LLM adapter using OpenAI-compatible API (Ollama / vLLM)."""

    def __init__(self, model: str = "qwen2.5:3b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")
        # Detect backend type from URL
        if "11434" in base_url:
            # Ollama uses /api/chat
            self.api_path = "/api/chat"
            self.backend = "ollama"
        else:
            # vLLM uses /v1/chat/completions (OpenAI-compatible)
            self.api_path = "/v1/chat/completions"
            self.backend = "vllm"

        logger.info(f"LocalLLM initialized: model={model}, backend={self.backend}, url={self.base_url}")

    async def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        """Generate a complete response (non-streaming)."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        url = f"{self.base_url}{self.api_path}"

        try:
            async with httpx.AsyncClient(timeout=1200.0) as client:
                if self.backend == "ollama":
                    resp = await client.post(url, json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                    })
                    resp.raise_for_status()
                    data = resp.json()
                    content = data.get("message", {}).get("content", "")
                    dur = data.get("total_duration", 0) / 1e9
                    logger.info(f"Ollama response: {len(content)} chars, {dur:.1f}s")
                    return content
                else:
                    # vLLM / OpenAI-compatible
                    resp = await client.post(url, json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": kwargs.get("temperature", 0.7),
                        "max_tokens": kwargs.get("max_tokens", 4096),
                    })
                    resp.raise_for_status()
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]

        except httpx.ConnectError:
            raise RuntimeError(
                f"Cannot connect to local LLM at {self.base_url}. "
                f"Is {'ollama serve' if self.backend == 'ollama' else 'vLLM'} running?"
            )
        except httpx.ReadTimeout:
            raise RuntimeError(
                f"Local LLM timeout after 1200s. Model={self.model}, "
                f"prompt too long for CPU? Try a smaller document or faster hardware."
            )
        except httpx.TimeoutException as e:
            raise RuntimeError(f"Local LLM timeout: {type(e).__name__}")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Local LLM error {e.response.status_code}: {e.response.text[:500]}")
        except Exception as e:
            err_msg = str(e) or type(e).__name__
            logger.error(f"LocalLLM unexpected error: {type(e).__name__}: {err_msg}")
            raise RuntimeError(f"Local LLM error ({type(e).__name__}): {err_msg}")

    async def stream(self, prompt: str, system: str = "", **kwargs) -> AsyncGenerator[str, None]:
        """Generate response chunks for SSE streaming."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        url = f"{self.base_url}{self.api_path}"

        try:
            async with httpx.AsyncClient(timeout=1200.0) as client:
                if self.backend == "ollama":
                    async with client.stream("POST", url, json={
                        "model": self.model,
                        "messages": messages,
                        "stream": True,
                    }) as resp:
                        import json
                        async for line in resp.aiter_lines():
                            if not line:
                                continue
                            try:
                                data = json.loads(line)
                                content = data.get("message", {}).get("content", "")
                                if content:
                                    yield content
                                if data.get("done", False):
                                    break
                            except (json.JSONDecodeError, KeyError):
                                continue
                else:
                    # vLLM / OpenAI-compatible SSE
                    async with client.stream("POST", url, json={
                        "model": self.model,
                        "messages": messages,
                        "stream": True,
                        "temperature": kwargs.get("temperature", 0.7),
                        "max_tokens": kwargs.get("max_tokens", 4096),
                    }) as resp:
                        import json
                        async for line in resp.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except (json.JSONDecodeError, KeyError, IndexError):
                                continue

        except httpx.ConnectError:
            raise RuntimeError(
                f"Cannot connect to local LLM at {self.base_url}. "
                f"Is {'ollama serve' if self.backend == 'ollama' else 'vLLM'} running?"
            )

    def get_model_name(self) -> str:
        return f"local/{self.model}"
