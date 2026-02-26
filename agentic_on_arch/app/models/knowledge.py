"""Knowledge base and document models with pgvector embeddings."""

from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey
from pgvector.sqlalchemy import Vector
from app.models import Base, TimestampMixin


class KnowledgeBase(Base, TimestampMixin):
    __tablename__ = "knowledge_bases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, default="")
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doc_count = Column(Integer, default=0)
    embedding_model = Column(String(128), default="text-embedding-3-small")
    config = Column(JSON, default={})


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False, index=True)
    title = Column(String(256), nullable=False)
    file_path = Column(String(512), default="")
    file_type = Column(String(32), default="")  # pdf | docx | txt | md
    content = Column(Text, default="")
    chunk_count = Column(Integer, default=0)
    metadata_ = Column("metadata", JSON, default={})


class DocumentChunk(Base, TimestampMixin):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536))  # OpenAI text-embedding-3-small dimension
    token_count = Column(Integer, default=0)
    metadata_ = Column("metadata", JSON, default={})
