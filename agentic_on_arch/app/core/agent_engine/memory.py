"""Agent memory management."""

from typing import List, Dict
from collections import deque


class AgentMemory:
    """Sliding-window memory for agent conversations."""

    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self._messages: deque = deque(maxlen=max_turns * 2)

    def add(self, role: str, content: str):
        self._messages.append({"role": role, "content": content})

    def get_messages(self) -> List[Dict[str, str]]:
        return list(self._messages)

    def clear(self):
        self._messages.clear()

    def token_estimate(self) -> int:
        """Rough token count estimate (Chinese ~ 1 char per token)."""
        return sum(len(m["content"]) for m in self._messages)
