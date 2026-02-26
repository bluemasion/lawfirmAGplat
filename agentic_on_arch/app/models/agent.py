"""Agent configuration model."""

from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey
from app.models import Base, TimestampMixin


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, default="")
    agent_type = Column(String(64), nullable=False)  # securities | translation | conflict | bidding | custom
    llm_provider = Column(String(32), default="qwen")  # claude | qwen | glm
    llm_model = Column(String(128), default="")
    system_prompt = Column(Text, default="")
    skills = Column(JSON, default=[])  # list of skill IDs bound to this agent
    config = Column(JSON, default={})  # extra config (temperature, top_p, etc.)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Integer, default=1)
