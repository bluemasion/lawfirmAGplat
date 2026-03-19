"""LLM adapter layer — factory function to get the active LLM provider."""

from app.config import settings


def get_llm(provider: str = None, **kwargs):
    """Return an LLM adapter instance based on provider name.

    For local providers, kwargs can include:
        model (str): Model name (e.g. 'qwen2.5:3b' for Ollama, 'Qwen2.5-32B' for vLLM)
        base_url (str): API base URL (default varies by backend)
    """
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
    elif name in ("local", "ollama"):
        from app.core.llm.local import LocalLLM
        model = kwargs.get("model", "qwen2.5:3b")
        base_url = kwargs.get("base_url", "http://localhost:11434")
        return LocalLLM(model=model, base_url=base_url)
    elif name == "vllm":
        from app.core.llm.local import LocalLLM
        model = kwargs.get("model", "Qwen/Qwen2.5-32B-Instruct")
        base_url = kwargs.get("base_url", "http://localhost:8081")
        return LocalLLM(model=model, base_url=base_url)
    else:
        raise ValueError(f"Unknown LLM provider: {name}")

