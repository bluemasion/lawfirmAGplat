"""RAG pipeline — document chunking, embedding, and retrieval."""

from typing import List, Dict
from app.utils.logger import logger


class RAGPipeline:
    """Full RAG pipeline: chunk → embed → store → retrieve → augment."""

    def __init__(self, embedding_model: str = "text-embedding-3-small", chunk_size: int = 512, chunk_overlap: int = 64, top_k: int = 5):
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.top_k = top_k

    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end])
            start += self.chunk_size - self.chunk_overlap
        logger.debug(f"Chunked text into {len(chunks)} chunks")
        return chunks

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for text chunks. TODO: call actual embedding API."""
        logger.warning("Embedding not implemented — returning zero vectors")
        return [[0.0] * 1536 for _ in texts]

    async def retrieve(self, query: str, knowledge_base_id: int) -> List[Dict]:
        """Retrieve relevant chunks from pgvector. TODO: implement actual search."""
        logger.warning("Retrieval not implemented")
        return []

    def augment_prompt(self, query: str, retrieved_chunks: List[Dict]) -> str:
        """Build RAG-augmented prompt with retrieved context."""
        if not retrieved_chunks:
            return query
        context = "\n---\n".join([c.get("content", "") for c in retrieved_chunks])
        return f"根据以下参考资料回答问题。必须引用原文段落作为依据。\n\n参考资料：\n{context}\n\n问题：{query}"
