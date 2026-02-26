"""Pydantic schemas for chat endpoints."""

from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None
    agent_id: Optional[int] = None
    stream: bool = True


class ChatMessage(BaseModel):
    role: str
    content: str
    metadata: dict = {}
