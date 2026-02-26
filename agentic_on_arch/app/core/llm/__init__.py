"""LLM adapter layer — factory function to get the active LLM provider."""

from app.config import settings


def get_llm(provider: str = None):
    """Return an LLM adapter instance based on provider name."""
    name = provider or settings.DEFAULT_LLM

    if name == "claude":
        from app.core.llm.claude import ClaudeLLM
        return ClaudeLLM()
    elif name == "qwen":
        from app.core.llm.qwen import QwenLLM
        return QwenLLM()
    elif name == "glm":
        from app.core.llm.glm import GLMLLM
        return GLMLLM()
    else:
        raise ValueError(f"Unknown LLM provider: {name}")
