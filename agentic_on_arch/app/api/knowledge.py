"""Knowledge base management API."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_db
from app.schemas.knowledge import KnowledgeBaseCreate, SearchRequest
from app.models.knowledge import KnowledgeBase
from app.utils.response import ok

router = APIRouter()


@router.get("/")
async def list_knowledge_bases(db: AsyncSession = Depends(get_db)):
    """List all knowledge bases."""
    result = await db.execute(select(KnowledgeBase))
    kbs = result.scalars().all()
    return ok(data=[{"id": k.id, "name": k.name, "doc_count": k.doc_count, "description": k.description} for k in kbs])


@router.post("/")
async def create_knowledge_base(req: KnowledgeBaseCreate, db: AsyncSession = Depends(get_db)):
    """Create a new knowledge base."""
    kb = KnowledgeBase(name=req.name, description=req.description, embedding_model=req.embedding_model, owner_id=1)
    db.add(kb)
    await db.flush()
    return ok(data={"id": kb.id, "name": kb.name})


@router.post("/search")
async def search(req: SearchRequest, db: AsyncSession = Depends(get_db)):
    """Semantic search within a knowledge base (pgvector)."""
    # TODO: embed query → pgvector cosine similarity search
    return ok(data={"results": [], "message": "向量检索待实现 — 需要 Embedding 模型"})
