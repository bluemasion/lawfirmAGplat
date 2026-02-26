"""Conversation and message models."""

from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey
from app.models import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(256), default="新对话")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    metadata_ = Column("metadata", JSON, default={})


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String(32), nullable=False)  # user | assistant | system | tool
    content = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)
    metadata_ = Column("metadata", JSON, default={})  # tool results, citations, etc.
