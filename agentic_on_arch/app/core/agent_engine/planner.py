"""Task planner — breaks down complex requests into steps."""

from typing import List, Dict


class TaskPlanner:
    """Simple task planner for multi-step agent workflows."""

    async def plan(self, objective: str, available_skills: List[str]) -> List[Dict]:
        """
        Generate a plan of action for the given objective.
        Returns list of steps: [{"skill": "...", "input": "...", "description": "..."}]

        TODO: Use LLM to generate dynamic plans based on objective + available skills.
        Current: returns a single-step plan (direct LLM call).
        """
        return [{"skill": "direct_llm", "input": objective, "description": "直接调用 LLM 回答"}]
