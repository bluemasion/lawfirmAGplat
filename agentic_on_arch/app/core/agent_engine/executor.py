"""Agent executor — runs agent loop (plan → execute skill → respond)."""

from typing import Dict, Any
from app.core.agent_engine.base import BaseAgent
from app.core.llm import get_llm
from app.core.skills.registry import skill_registry
from app.utils.logger import logger


class AgentExecutor(BaseAgent):
    """Default agent executor implementing ReAct-style loop."""

    async def run(self, user_input: str, context: Dict[str, Any] = None) -> str:
        self.add_to_memory("user", user_input)
        llm = get_llm(self.llm_provider)

        # Build prompt with context
        prompt = self._build_prompt(user_input, context)

        # Call LLM
        response = await llm.generate(prompt, system=self.system_prompt)
        self.add_to_memory("assistant", response)

        logger.info(f"Agent [{self.name}] responded: {len(response)} chars")
        return response

    def _build_prompt(self, user_input: str, context: Dict[str, Any] = None) -> str:
        parts = []

        # Add available skills info
        if self.skills:
            skills_info = skill_registry.describe_skills(self.skills)
            parts.append(f"你拥有以下技能可以调用：\n{skills_info}\n")

        # Add context
        if context:
            parts.append(f"上下文信息：\n{context}\n")

        # Add conversation history
        if len(self.memory) > 1:
            history = "\n".join([f"{m['role']}: {m['content']}" for m in self.memory[:-1]])
            parts.append(f"对话历史：\n{history}\n")

        parts.append(f"用户问题：{user_input}")
        return "\n".join(parts)
