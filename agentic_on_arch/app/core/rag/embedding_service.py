"""Embedding service — local BGE model for text vectorization.

Uses BAAI/bge-small-zh-v1.5 (95MB) for:
1. RAG text embedding (vector search)
2. Similarity scoring (template matching)

Lazy-loads model on first call. Thread-safe singleton.
"""

import os
import threading
from typing import List, Optional, Union

import numpy as np

from app.utils.logger import logger


# Model selection — can switch to bge-large-zh-v1.5 for better quality
DEFAULT_MODEL = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
# Cache directory for downloaded models
MODEL_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "models")


class EmbeddingService:
    """Singleton embedding service with lazy model loading."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._model = None
                    cls._instance._model_name = DEFAULT_MODEL
                    cls._instance._dimension = None
        return cls._instance

    def _load_model(self):
        """Load the sentence-transformer model (lazy, first call only)."""
        if self._model is not None:
            return

        logger.info(f"Loading embedding model: {self._model_name} ...")
        try:
            # Set HF mirror for China if not already set
            if not os.environ.get("HF_ENDPOINT"):
                os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

            from sentence_transformers import SentenceTransformer

            os.makedirs(MODEL_CACHE_DIR, exist_ok=True)
            self._model = SentenceTransformer(
                self._model_name,
                cache_folder=MODEL_CACHE_DIR,
            )
            # Get dimension from a test encoding
            test_vec = self._model.encode(["test"], normalize_embeddings=True)
            self._dimension = test_vec.shape[1]
            logger.info(f"Embedding model loaded: dim={self._dimension}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    @property
    def dimension(self) -> int:
        """Get embedding dimension (loads model if needed)."""
        self._load_model()
        return self._dimension

    def encode(self, texts: Union[str, List[str]], normalize: bool = True) -> np.ndarray:
        """Encode text(s) into embedding vectors.

        Args:
            texts: Single string or list of strings
            normalize: If True, normalize to unit vectors (for cosine similarity)

        Returns:
            numpy array of shape (n, dim)
        """
        self._load_model()

        if isinstance(texts, str):
            texts = [texts]

        embeddings = self._model.encode(
            texts,
            normalize_embeddings=normalize,
            show_progress_bar=False,
        )
        return embeddings

    def similarity(self, text_a: str, text_b: str) -> float:
        """Compute cosine similarity between two texts.

        Returns: float in [-1, 1], higher = more similar
        """
        vecs = self.encode([text_a, text_b])
        return float(np.dot(vecs[0], vecs[1]))

    def similarity_matrix(self, texts_a: List[str], texts_b: List[str]) -> np.ndarray:
        """Compute pairwise cosine similarity matrix.

        Returns: numpy array of shape (len(texts_a), len(texts_b))
        """
        vecs_a = self.encode(texts_a)
        vecs_b = self.encode(texts_b)
        return np.dot(vecs_a, vecs_b.T)

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._model is not None


# Global singleton
embedding_service = EmbeddingService()
