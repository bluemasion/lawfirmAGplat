"""Pydantic schemas for knowledge base endpoints."""

from pydantic import BaseModel
from typing import Optional


class KnowledgeBaseCreate(BaseModel):
    name: str
    description: str = ""
    embedding_model: str = "text-embedding-3-small"


class DocumentUpload(BaseModel):
    title: str
    knowledge_base_id: int


class SearchRequest(BaseModel):
    query: str
    knowledge_base_id: int
    top_k: int = 5
