"""Skill registry — register and discover skills."""

from typing import Dict, List, Optional
from app.core.skills.base import BaseSkill
from app.utils.logger import logger


class SkillRegistry:
    """Central registry for all available skills."""

    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill):
        self._skills[skill.name] = skill
        logger.info(f"Skill registered: {skill.name}")

    def get(self, name: str) -> Optional[BaseSkill]:
        return self._skills.get(name)

    def list_skills(self) -> List[str]:
        return list(self._skills.keys())

    def describe_skills(self, names: List[str] = None) -> str:
        """Return human-readable skill descriptions for LLM prompt."""
        target = names or list(self._skills.keys())
        lines = []
        for name in target:
            skill = self._skills.get(name)
            if skill:
                lines.append(f"- {skill.name}: {skill.description}")
        return "\n".join(lines) if lines else "无可用技能"


# Global singleton
skill_registry = SkillRegistry()
