"""Material store — storage and retrieval for extracted bid materials.

Manages the lifecycle of materials extracted from historical bid documents:
- Save structured data (resumes, projects, qualifications) to JSON
- Vectorize narrative chunks with BGE embedding
- Search materials by type and relevance
"""

import json
import os
import time
from typing import Any, Dict, List, Optional

import numpy as np

from app.utils.logger import logger


# Default storage directory
MATERIAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "..", "..", "..", "data", "materials")


class MaterialStore:
    """Manage extracted materials from historical bid documents."""

    def __init__(self, base_dir: str = ""):
        self.base_dir = base_dir or MATERIAL_DIR
        os.makedirs(self.base_dir, exist_ok=True)

        # JSON file paths
        self.resumes_file = os.path.join(self.base_dir, "resumes.json")
        self.projects_file = os.path.join(self.base_dir, "projects.json")
        self.qualifications_file = os.path.join(self.base_dir, "qualifications.json")
        self.narratives_file = os.path.join(self.base_dir, "narrative_chunks.json")

        # In-memory vector index for narrative chunks
        self._narrative_vectors = None  # type: Optional[np.ndarray]
        self._narrative_chunks = []     # type: List[Dict]
        self._embedding_service = None

    # ── Save Methods ──

    def save_materials(self, materials: Dict[str, Any]) -> Dict[str, int]:
        """Save extracted materials to JSON files, merging with existing data.

        Returns dict with counts of items saved per type.
        """
        counts = {}

        # Save resumes
        resumes = materials.get("resumes", [])
        if resumes:
            existing = self._load_json(self.resumes_file)
            existing.extend(resumes)
            existing = self._dedup_by_field(existing, "name")
            self._save_json(self.resumes_file, existing)
            counts["resumes"] = len(resumes)

        # Save projects
        projects = materials.get("projects", [])
        if projects:
            existing = self._load_json(self.projects_file)
            existing.extend(projects)
            existing = self._dedup_by_field(existing, "project_name")
            self._save_json(self.projects_file, existing)
            counts["projects"] = len(projects)

        # Save qualifications
        qualifications = materials.get("qualifications", [])
        if qualifications:
            existing = self._load_json(self.qualifications_file)
            existing.extend(qualifications)
            existing = self._dedup_by_field(existing, "name")
            self._save_json(self.qualifications_file, existing)
            counts["qualifications"] = len(qualifications)

        # Save narrative chunks
        narrative_chunks = materials.get("narrative_chunks", [])
        if narrative_chunks:
            existing = self._load_json(self.narratives_file)
            existing.extend(narrative_chunks)
            self._save_json(self.narratives_file, existing)
            counts["narrative_chunks"] = len(narrative_chunks)

        logger.info(f"Materials saved: {counts}")
        return counts

    # ── Load Methods ──

    def get_resumes(self) -> List[Dict]:
        """Get all stored resumes."""
        return self._load_json(self.resumes_file)

    def get_projects(self) -> List[Dict]:
        """Get all stored projects."""
        return self._load_json(self.projects_file)

    def get_qualifications(self) -> List[Dict]:
        """Get all stored qualifications."""
        return self._load_json(self.qualifications_file)

    def get_narrative_chunks(self) -> List[Dict]:
        """Get all stored narrative chunks."""
        return self._load_json(self.narratives_file)

    def get_all_materials(self) -> Dict[str, Any]:
        """Get all materials as a dict."""
        return {
            "resumes": self.get_resumes(),
            "projects": self.get_projects(),
            "qualifications": self.get_qualifications(),
            "narrative_chunks": self.get_narrative_chunks(),
        }

    def get_summary(self) -> Dict[str, int]:
        """Get count summary of all materials."""
        return {
            "resumes": len(self.get_resumes()),
            "projects": len(self.get_projects()),
            "qualifications": len(self.get_qualifications()),
            "narrative_chunks": len(self.get_narrative_chunks()),
        }

    # ── Search Methods ──

    def search_resumes(self, query: str = "",
                       specialty: str = "") -> List[Dict]:
        """Search resumes by name or specialty keyword."""
        resumes = self.get_resumes()
        if not query and not specialty:
            return resumes

        results = []
        query_lower = query.lower()
        spec_lower = specialty.lower()

        for r in resumes:
            name = (r.get("name") or "").lower()
            spec = (r.get("specialty") or "").lower()
            bio = (r.get("brief_bio") or "").lower()

            if query_lower and query_lower in name:
                results.append(r)
            elif spec_lower and spec_lower in spec:
                results.append(r)
            elif query_lower and (query_lower in spec or query_lower in bio):
                results.append(r)

        return results

    def search_projects(self, query: str = "",
                        project_type: str = "") -> List[Dict]:
        """Search projects by name or type."""
        projects = self.get_projects()
        if not query and not project_type:
            return projects

        results = []
        for p in projects:
            name = (p.get("project_name") or "").lower()
            ptype = (p.get("project_type") or "").lower()
            desc = (p.get("description") or "").lower()
            q = query.lower()

            if q and (q in name or q in desc):
                results.append(p)
            elif project_type and project_type.lower() in ptype:
                results.append(p)

        return results

    async def search_narratives(self, query: str,
                                 top_k: int = 5) -> List[Dict]:
        """Semantic search narrative chunks using BGE embedding."""
        chunks = self.get_narrative_chunks()
        if not chunks:
            return []

        # Try to use embedding service for semantic search
        try:
            if self._embedding_service is None:
                from app.core.rag.embedding_service import EmbeddingService
                self._embedding_service = EmbeddingService()

            # Build vectors if not cached
            if self._narrative_vectors is None or len(self._narrative_chunks) != len(chunks):
                self._narrative_chunks = chunks
                texts = [c.get("content", "") for c in chunks]
                self._narrative_vectors = self._embedding_service.encode(texts)
                logger.info(f"Vectorized {len(texts)} narrative chunks")

            # Encode query
            query_vec = self._embedding_service.encode([query])

            # Cosine similarity
            scores = np.dot(self._narrative_vectors, query_vec.T).flatten()
            top_indices = np.argsort(scores)[::-1][:top_k]

            results = []
            for idx in top_indices:
                if scores[idx] > 0.3:  # minimum similarity threshold
                    chunk = chunks[idx].copy()
                    chunk["similarity"] = float(scores[idx])
                    results.append(chunk)

            return results

        except Exception as e:
            logger.warning(f"Semantic search failed, falling back to keyword: {e}")
            # Fallback: keyword search
            q = query.lower()
            scored = []
            for c in chunks:
                content = c.get("content", "").lower()
                if q in content:
                    scored.append(c)
            return scored[:top_k]

    # ── Update / Delete Methods ──

    def update_resume(self, name: str, updates: Dict) -> bool:
        """Update a resume by name."""
        resumes = self.get_resumes()
        for r in resumes:
            if r.get("name") == name:
                r.update(updates)
                self._save_json(self.resumes_file, resumes)
                return True
        return False

    def update_project(self, project_name: str, updates: Dict) -> bool:
        """Update a project by name."""
        projects = self.get_projects()
        for p in projects:
            if p.get("project_name") == project_name:
                p.update(updates)
                self._save_json(self.projects_file, projects)
                return True
        return False

    def delete_resume(self, name: str) -> bool:
        """Delete a resume by name."""
        resumes = self.get_resumes()
        new_resumes = [r for r in resumes if r.get("name") != name]
        if len(new_resumes) < len(resumes):
            self._save_json(self.resumes_file, new_resumes)
            return True
        return False

    def clear_all(self):
        """Clear all materials."""
        for f in [self.resumes_file, self.projects_file,
                  self.qualifications_file, self.narratives_file]:
            if os.path.exists(f):
                os.remove(f)
        self._narrative_vectors = None
        self._narrative_chunks = []
        logger.info("All materials cleared")

    # ── Internal Helpers ──

    def _load_json(self, path: str) -> List[Dict]:
        """Load JSON array from file, returning empty list if missing."""
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, IOError):
            return []

    def _save_json(self, path: str, data: List[Dict]):
        """Save JSON array to file."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _dedup_by_field(self, items: List[Dict],
                         field: str) -> List[Dict]:
        """Remove duplicates by a specific field, keeping the last occurrence."""
        seen = {}  # type: Dict[str, Dict]
        for item in items:
            key = item.get(field, "")
            if key:
                seen[key] = item
            else:
                # Items without the field are always kept
                seen[id(item)] = item
        return list(seen.values())

    # ── Change Detection ──

    def diff_materials(self, new_materials: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """Compare new materials against existing store, return per-item diff.

        Returns dict like:
        {
          "resumes": [
            {"name": "王大明", "action": "new", "data": {...}},
            {"name": "李文华", "action": "updated", "changes": {"years": [15, 17]}, "data": {...}},
            {"name": "陈强", "action": "unchanged", "data": {...}},
          ],
          "projects": [...],
          "qualifications": [...]
        }
        """
        diff = {}

        # Diff resumes
        new_resumes = new_materials.get("resumes", [])
        if new_resumes:
            existing = {r.get("name", ""): r for r in self.get_resumes() if r.get("name")}
            diff["resumes"] = self._diff_items(new_resumes, existing, "name")

        # Diff projects
        new_projects = new_materials.get("projects", [])
        if new_projects:
            existing = {p.get("project_name", ""): p for p in self.get_projects() if p.get("project_name")}
            diff["projects"] = self._diff_items(new_projects, existing, "project_name")

        # Diff qualifications
        new_quals = new_materials.get("qualifications", [])
        if new_quals:
            existing = {q.get("name", ""): q for q in self.get_qualifications() if q.get("name")}
            diff["qualifications"] = self._diff_items(new_quals, existing, "name")

        # Narrative chunks: always "new" (no dedup for text chunks)
        new_narratives = new_materials.get("narrative_chunks", [])
        if new_narratives:
            diff["narrative_chunks"] = [
                {"title": c.get("title", ""), "action": "new",
                 "preview": c.get("content", "")[:100]}
                for c in new_narratives
            ]

        return diff

    def _diff_items(self, new_items: List[Dict], existing_map: Dict[str, Dict],
                    key_field: str) -> List[Dict]:
        """Compare new items against existing by key field (with fuzzy matching)."""
        from difflib import SequenceMatcher

        # Internal fields to skip in diff comparison
        _SKIP_FIELDS = {"_source", "_extracted_at", "_source_file", "_source_path",
                        "_source_section", "_images"}

        def _find_best_match(name: str, candidates: Dict[str, Dict]) -> Optional[str]:
            """Find best fuzzy match for a name in candidates (threshold 0.7)."""
            if not name:
                return None
            # Exact match first
            if name in candidates:
                return name
            # Fuzzy match
            best_ratio, best_key = 0, None
            for candidate_key in candidates:
                ratio = SequenceMatcher(None, name, candidate_key).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_key = candidate_key
            if best_ratio >= 0.7:
                logger.info(f"Fuzzy match: '{name}' → '{best_key}' (similarity={best_ratio:.2f})")
                return best_key
            return None

        results = []
        for item in new_items:
            key = item.get(key_field, "")
            if not key:
                results.append({"action": "new", "data": item})
                continue

            matched_key = _find_best_match(key, existing_map)

            if matched_key is None:
                results.append({"action": "new", key_field: key, "data": item})
            else:
                old = existing_map[matched_key]
                changes = {}
                for field, new_val in item.items():
                    if field in _SKIP_FIELDS:
                        continue
                    old_val = old.get(field)
                    if old_val != new_val and new_val:
                        if old_val:
                            changes[field] = [str(old_val)[:80], str(new_val)[:80]]
                        else:
                            changes[field] = [None, str(new_val)[:80]]

                if changes:
                    results.append({
                        "action": "updated", key_field: key,
                        "changes": changes, "data": item,
                    })
                else:
                    results.append({
                        "action": "unchanged", key_field: key, "data": item,
                    })
        return results


# Singleton instance
_store = None  # type: Optional[MaterialStore]


def get_material_store(base_dir: str = "") -> MaterialStore:
    """Get singleton MaterialStore instance."""
    global _store
    if _store is None:
        _store = MaterialStore(base_dir)
    return _store
