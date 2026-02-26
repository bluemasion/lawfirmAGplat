"""Skill definition model."""

from sqlalchemy import Column, Integer, String, Text, JSON
from app.models import Base, TimestampMixin


class Skill(Base, TimestampMixin):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), unique=True, nullable=False)
    description = Column(Text, default="")
    skill_type = Column(String(64), nullable=False)  # builtin | custom
    module_path = Column(String(256), nullable=False)  # e.g. app.core.skills.builtin.securities_audit
    parameters_schema = Column(JSON, default={})  # JSON Schema for skill parameters
    is_active = Column(Integer, default=1)
