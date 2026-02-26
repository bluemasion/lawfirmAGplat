"""User model."""

from sqlalchemy import Column, Integer, String, Boolean
from app.models import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(128), unique=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    display_name = Column(String(64), default="")
    role = Column(String(32), default="user")  # admin | partner | lawyer | assistant | user
    firm_name = Column(String(128), default="")
    is_active = Column(Boolean, default=True)
