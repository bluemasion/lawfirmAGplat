"""Pydantic schemas for agent endpoints."""

from pydantic import BaseModel
from typing import Optional, List


class AgentCreate(BaseModel):
    name: str
    description: str = ""
    agent_type: str = "custom"
    llm_provider: str = "qwen"
    llm_model: str = ""
    system_prompt: str = ""
    skills: List[str] = []
    config: dict = {}


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    system_prompt: Optional[str] = None
    skills: Optional[List[str]] = None
    config: Optional[dict] = None
