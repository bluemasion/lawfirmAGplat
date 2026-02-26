"""Agent base class."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseAgent(ABC):
    """Base class for all agents."""

    def __init__(self, name: str, llm_provider: str = "qwen", system_prompt: str = "", skills: List[str] = None):
        self.name = name
        self.llm_provider = llm_provider
        self.system_prompt = system_prompt
        self.skills = skills or []
        self.memory: List[Dict[str, str]] = []

    @abstractmethod
    async def run(self, user_input: str, context: Dict[str, Any] = None) -> str:
        """Execute the agent with user input and optional context."""
        ...

    def add_to_memory(self, role: str, content: str):
        self.memory.append({"role": role, "content": content})

    def get_memory(self) -> List[Dict[str, str]]:
        return self.memory

    def clear_memory(self):
        self.memory.clear()
