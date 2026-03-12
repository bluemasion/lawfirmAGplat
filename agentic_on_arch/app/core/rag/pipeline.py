"""RAG pipeline — document chunking, embedding, and retrieval."""

from typing import List, Dict
from app.utils.logger import logger


class RAGPipeline:
    """Full RAG pipeline: chunk → embed → store → retrieve → augment."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64, top_k: int = 5):
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
        """Generate embeddings using local BGE model."""
        try:
            from app.core.rag.embedding_service import embedding_service
            vectors = embedding_service.encode(texts)
            logger.info(f"Embedded {len(texts)} texts → dim={vectors.shape[1]}")
            return vectors.tolist()
        except Exception as e:
            logger.error(f"Embedding failed, falling back to zero vectors: {e}")
            return [[0.0] * 512 for _ in texts]

    async def retrieve(self, query: str, knowledge_base_id: int) -> List[Dict]:
        """Retrieve relevant chunks via embedding similarity.

        TODO: Implement actual vector store (pgvector/ChromaDB).
        Currently returns empty — will be connected to vector DB in Phase 3.
        """
        logger.warning("Vector store not connected — retrieval returns empty")
        return []

    def augment_prompt(self, query: str, retrieved_chunks: List[Dict]) -> str:
        """Build RAG-augmented prompt with retrieved context."""
        if not retrieved_chunks:
            return query
        context = "\n---\n".join([c.get("content", "") for c in retrieved_chunks])
        return f"根据以下参考资料回答问题。必须引用原文段落作为依据。\n\n参考资料：\n{context}\n\n问题：{query}"

