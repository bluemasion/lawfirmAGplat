"""File record model."""

from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey
from app.models import Base, TimestampMixin


class FileRecord(Base, TimestampMixin):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    original_name = Column(String(256), nullable=False)
    stored_name = Column(String(256), nullable=False)  # UUID-based
    file_path = Column(String(512), nullable=False)
    file_type = Column(String(32), default="")
    file_size = Column(BigInteger, default=0)  # bytes
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
