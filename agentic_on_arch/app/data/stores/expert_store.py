"""ExpertStore — 评审专家库数据存储。"""

import json
import logging
import os
import sqlite3
import uuid
import random
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DB_PATH = os.path.join(_DATA_DIR, "expert", "expert.db")


class ExpertStore:
    """评审专家库 (SQLite)。"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self._ensure_db()

    def _ensure_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS experts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    organization TEXT DEFAULT '',
                    title TEXT DEFAULT '',
                    categories TEXT DEFAULT '[]',
                    certifications TEXT DEFAULT '[]',
                    phone TEXT DEFAULT '',
                    email TEXT DEFAULT '',
                    status TEXT DEFAULT 'active',
                    total_reviews INTEGER DEFAULT 0,
                    avg_rating REAL DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS expert_draws (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    expert_id TEXT REFERENCES experts(id),
                    category TEXT DEFAULT '',
                    avoided_suppliers TEXT DEFAULT '[]',
                    drawn_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS expert_evaluations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    expert_id TEXT REFERENCES experts(id),
                    session_id TEXT,
                    rating INTEGER DEFAULT 0,
                    comment TEXT DEFAULT '',
                    evaluated_at TEXT DEFAULT (datetime('now'))
                );
            """)

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def add_expert(self, name: str, **kwargs) -> Dict:
        expert_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO experts
                   (id, name, organization, title, categories, certifications,
                    phone, email, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)""",
                (expert_id, name,
                 kwargs.get("organization", ""),
                 kwargs.get("title", ""),
                 json.dumps(kwargs.get("categories", []), ensure_ascii=False),
                 json.dumps(kwargs.get("certifications", []), ensure_ascii=False),
                 kwargs.get("phone", ""),
                 kwargs.get("email", ""),
                 now, now)
            )
        return self.get_expert(expert_id)

    def get_expert(self, expert_id: str) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM experts WHERE id=?", (expert_id,)).fetchone()
            if row:
                d = dict(row)
                d["categories"] = json.loads(d.get("categories", "[]"))
                d["certifications"] = json.loads(d.get("certifications", "[]"))
                return d
            return None

    def list_experts(self, category: str = None, status: str = "active") -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM experts WHERE status=? ORDER BY name", (status,)
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["categories"] = json.loads(d.get("categories", "[]"))
                d["certifications"] = json.loads(d.get("certifications", "[]"))
                if category and category not in d["categories"]:
                    continue
                result.append(d)
            return result

    def draw_experts(self, category: str, count: int,
                     avoid_suppliers: List[str] = None,
                     session_id: str = "") -> List[Dict]:
        """按专业分类随机抽取专家"""
        candidates = self.list_experts(category=category)
        if len(candidates) <= count:
            drawn = candidates
        else:
            drawn = random.sample(candidates, count)

        # 记录抽取
        with self._conn() as conn:
            for expert in drawn:
                conn.execute(
                    """INSERT INTO expert_draws
                       (session_id, expert_id, category, avoided_suppliers)
                       VALUES (?, ?, ?, ?)""",
                    (session_id, expert["id"], category,
                     json.dumps(avoid_suppliers or [], ensure_ascii=False))
                )

        return drawn


_store: Optional[ExpertStore] = None


def get_expert_store() -> ExpertStore:
    global _store
    if _store is None:
        _store = ExpertStore()
    return _store
