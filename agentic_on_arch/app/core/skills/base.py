"""Skill base class."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseSkill(ABC):
    """Base class for all skills."""

    name: str = ""
    description: str = ""

    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Any:
        """Execute the skill with given parameters."""
        ...
