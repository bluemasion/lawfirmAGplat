"""Encrypted mapping store for De-ID / Re-ID sessions."""

import hashlib
import json
from typing import Dict, Optional
from app.utils.logger import logger


class MappingStore:
    """
    Session-scoped encrypted mapping store.
    In production, this should use Redis or DB with AES-256 encryption.
    Currently uses in-memory dict for development.
    """

    def __init__(self):
        self._sessions: Dict[str, Dict[str, str]] = {}

    def _session_key(self, user_id: int, conversation_id: int) -> str:
        return hashlib.sha256(f"{user_id}:{conversation_id}".encode()).hexdigest()

    def store(self, user_id: int, conversation_id: int, mapping: Dict[str, str]):
        key = self._session_key(user_id, conversation_id)
        self._sessions[key] = mapping
        logger.debug(f"NER mapping stored: {len(mapping)} entities for session {key[:8]}...")

    def retrieve(self, user_id: int, conversation_id: int) -> Optional[Dict[str, str]]:
        key = self._session_key(user_id, conversation_id)
        return self._sessions.get(key)

    def clear(self, user_id: int, conversation_id: int):
        key = self._session_key(user_id, conversation_id)
        self._sessions.pop(key, None)


# Global singleton
mapping_store = MappingStore()
