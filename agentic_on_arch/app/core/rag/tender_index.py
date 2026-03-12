"""Tender document index — in-memory vector store for self-RAG.

Chunks the uploaded tender document, embeds with BGE, and provides
semantic search so that narrative generation can reference specific
tender requirements.

Lifecycle: one index per task, lives in memory, released when task completes.
"""

import re
from typing import List, Optional, Tuple

import numpy as np

from app.core.rag.embedding_service import embedding_service
from app.utils.logger import logger


class TenderIndex:
    """In-memory vector index for a single tender document."""

    def __init__(self, chunk_size: int = 400, chunk_overlap: int = 80):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._chunks: List[str] = []
        self._embeddings: Optional[np.ndarray] = None  # (n, dim)
        self._built = False

    def build(self, raw_text: str, sections: Optional[List[dict]] = None) -> int:
        """Build vector index from tender document text.

        Args:
            raw_text: Full text of the tender document
            sections: Optional parsed sections (used for smarter chunking)

        Returns:
            Number of chunks indexed
        """
        if not raw_text or len(raw_text) < 50:
            logger.warning("Tender text too short to index")
            return 0

        # Smart chunking: prefer section boundaries over fixed-size
        if sections and len(sections) > 3:
            self._chunks = self._chunk_by_sections(sections)
        else:
            self._chunks = self._chunk_by_size(raw_text)

        if not self._chunks:
            return 0

        # Embed all chunks
        logger.info(f"Indexing {len(self._chunks)} tender chunks...")
        self._embeddings = embedding_service.encode(self._chunks)
        self._built = True

        logger.info(f"Tender index built: {len(self._chunks)} chunks, "
                     f"dim={self._embeddings.shape[1]}")
        return len(self._chunks)

    def search(self, query: str, top_k: int = 5) -> List[str]:
        """Search for chunks most relevant to a query.

        Args:
            query: Search query (usually section title + content hints)
            top_k: Number of results to return

        Returns:
            List of relevant text chunks, sorted by relevance
        """
        if not self._built or len(self._chunks) == 0:
            return []

        query_vec = embedding_service.encode(query)  # (1, dim)
        similarities = np.dot(query_vec, self._embeddings.T)[0]  # (n,)

        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            sim = float(similarities[idx])
            if sim < 0.3:  # Skip very low similarity
                continue
            results.append(self._chunks[idx])

        return results

    def search_with_scores(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Search with similarity scores (for debugging)."""
        if not self._built or len(self._chunks) == 0:
            return []

        query_vec = embedding_service.encode(query)
        similarities = np.dot(query_vec, self._embeddings.T)[0]

        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            sim = float(similarities[idx])
            if sim < 0.3:
                continue
            results.append((self._chunks[idx], sim))

        return results

    def verify_structure(self, extracted_titles: List[str]) -> List[dict]:
        """Verify that extracted section titles cover tender requirements.

        Searches the tender text for requirement-like phrases and checks
        if each is covered by the extracted structure.

        Returns:
            List of {requirement, covered, best_match, similarity}
        """
        if not self._built:
            return []

        # Extract requirement phrases from chunks
        requirement_phrases = self._extract_requirement_phrases()
        if not requirement_phrases:
            return []

        # Embed all titles
        if not extracted_titles:
            return []

        title_vecs = embedding_service.encode(extracted_titles)
        req_vecs = embedding_service.encode(requirement_phrases)

        # For each requirement, find best matching title
        sim_matrix = np.dot(req_vecs, title_vecs.T)  # (reqs, titles)

        results = []
        for i, req in enumerate(requirement_phrases):
            best_idx = int(np.argmax(sim_matrix[i]))
            best_sim = float(sim_matrix[i, best_idx])
            results.append({
                "requirement": req,
                "covered": best_sim > 0.6,
                "best_match": extracted_titles[best_idx],
                "similarity": round(best_sim, 3),
            })

        # Sort: uncovered first
        results.sort(key=lambda x: (x["covered"], -x["similarity"]))
        return results

    # ── Internal helpers ──

    def _chunk_by_sections(self, sections: List[dict]) -> List[str]:
        """Chunk using parsed section boundaries (smarter)."""
        chunks = []
        for sec in sections:
            title = sec.get("title", "")
            content = sec.get("content", "")
            if not content:
                continue

            # Prepend title to content for context
            full = f"【{title}】\n{content}" if title else content

            # If section is still too long, split further
            if len(full) > self.chunk_size * 2:
                sub_chunks = self._chunk_by_size(full)
                chunks.extend(sub_chunks)
            else:
                chunks.append(full)

        return chunks

    def _chunk_by_size(self, text: str) -> List[str]:
        """Fixed-size chunking with overlap."""
        chunks = []
        # Try to split on sentence boundaries (。！？\n)
        sentences = re.split(r'(?<=[。！？\n])', text)

        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                # Start new chunk with overlap
                overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                current_chunk = current_chunk[overlap_start:] + sentence
            else:
                current_chunk += sentence

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return [c for c in chunks if len(c) > 20]  # Filter tiny chunks

    def _extract_requirement_phrases(self) -> List[str]:
        """Extract requirement-like phrases from tender chunks."""
        patterns = [
            r'(?:投标文件应|须|需要|必须)(?:包含|提供|附|提交)(.{5,40})',
            r'(?:投标人应|投标人须)(?:提供|提交|说明|具备)(.{5,40})',
            r'第[一二三四五六七八九十\d]+(?:部分|章|节)[：:]?\s*(.{3,30})',
        ]
        phrases = set()
        for chunk in self._chunks:
            for pattern in patterns:
                matches = re.findall(pattern, chunk)
                for m in matches:
                    cleaned = m.strip().rstrip('。，；、')
                    if len(cleaned) > 3:
                        phrases.add(cleaned)

        return list(phrases)[:30]  # Cap at 30 to avoid noise

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    @property
    def is_built(self) -> bool:
        return self._built
