"""
Bidding Task Store — SQLite persistence for bid tasks.

Uses a separate `bidding.db` file alongside `materials.db`.
Stores task metadata, requirements (JSON), generation state etc.
"""

import json
import os
import sqlite3
import time
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

BIDDING_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "..", "..", "..", "data", "bidding")

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS bid_tasks (
    task_id          TEXT PRIMARY KEY,
    status           TEXT NOT NULL DEFAULT 'parsed',
    tender_filename  TEXT DEFAULT '',
    tender_file_path TEXT DEFAULT '',
    requirements     TEXT NOT NULL DEFAULT '{}',
    parse_result     TEXT DEFAULT '{}',
    company_name     TEXT DEFAULT '',
    section_checked  TEXT DEFAULT '{}',
    generated_sections TEXT DEFAULT '[]',
    output_file      TEXT DEFAULT '',
    created_at       REAL NOT NULL,
    confirmed_at     REAL,
    completed_at     REAL
);

CREATE INDEX IF NOT EXISTS idx_bid_tasks_status ON bid_tasks(status);
CREATE INDEX IF NOT EXISTS idx_bid_tasks_created ON bid_tasks(created_at);
"""


class BiddingStore:
    """Persistent storage for bidding tasks using SQLite."""

    def __init__(self, base_dir: str = ""):
        self.base_dir = base_dir or BIDDING_DIR
        os.makedirs(self.base_dir, exist_ok=True)
        self.db_path = os.path.join(self.base_dir, "bidding.db")
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
        try:
            conn.executescript(_SCHEMA_SQL)
            conn.commit()
            logger.info(f"BiddingStore initialized: {self.db_path}")
        finally:
            conn.close()

    # ── CRUD ──

    def save_task(self, task_data: dict):
        """Insert or update a bid task."""
        task_id = task_data["task_id"]
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT INTO bid_tasks
                    (task_id, status, tender_filename, tender_file_path,
                     requirements, parse_result, company_name,
                     section_checked, generated_sections, output_file,
                     created_at, confirmed_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    status=excluded.status,
                    tender_filename=excluded.tender_filename,
                    tender_file_path=excluded.tender_file_path,
                    requirements=excluded.requirements,
                    parse_result=excluded.parse_result,
                    company_name=excluded.company_name,
                    section_checked=excluded.section_checked,
                    generated_sections=excluded.generated_sections,
                    output_file=excluded.output_file,
                    confirmed_at=excluded.confirmed_at,
                    completed_at=excluded.completed_at
            """, (
                task_id,
                task_data.get("status", "parsed"),
                task_data.get("tender_filename", ""),
                task_data.get("tender_file_path", ""),
                json.dumps(task_data.get("requirements", {}), ensure_ascii=False),
                json.dumps(task_data.get("parse_result", {}), ensure_ascii=False),
                task_data.get("company_name", ""),
                json.dumps(task_data.get("section_checked", {}), ensure_ascii=False),
                json.dumps(task_data.get("generated_sections", []), ensure_ascii=False),
                task_data.get("output_file", ""),
                task_data.get("created_at", time.time()),
                task_data.get("confirmed_at"),
                task_data.get("completed_at"),
            ))
            conn.commit()
            logger.info(f"Saved bid task {task_id} (status={task_data.get('status')})")
        finally:
            conn.close()

    def get_task(self, task_id: str) -> Optional[dict]:
        """Get a single task by ID, with JSON fields parsed."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM bid_tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_dict(row)
        finally:
            conn.close()

    def list_tasks(self, limit: int = 50) -> List[dict]:
        """List all tasks, newest first."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM bid_tasks ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]
        finally:
            conn.close()

    def update_status(self, task_id: str, status: str, **kwargs):
        """Update task status and optional extra fields."""
        conn = self._get_conn()
        try:
            sets = ["status = ?"]
            vals = [status]

            if "company_name" in kwargs:
                sets.append("company_name = ?")
                vals.append(kwargs["company_name"])
            if "output_file" in kwargs:
                sets.append("output_file = ?")
                vals.append(kwargs["output_file"])
            if "generated_sections" in kwargs:
                sets.append("generated_sections = ?")
                vals.append(json.dumps(kwargs["generated_sections"], ensure_ascii=False))
            if status == "confirmed":
                sets.append("confirmed_at = ?")
                vals.append(time.time())
            if status == "done":
                sets.append("completed_at = ?")
                vals.append(time.time())
            if "section_checked" in kwargs:
                sets.append("section_checked = ?")
                vals.append(json.dumps(kwargs["section_checked"], ensure_ascii=False))

            vals.append(task_id)
            conn.execute(
                f"UPDATE bid_tasks SET {', '.join(sets)} WHERE task_id = ?",
                vals
            )
            conn.commit()
            logger.info(f"Updated bid task {task_id} → {status}")
        finally:
            conn.close()

    def delete_task(self, task_id: str):
        """Delete a task."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM bid_tasks WHERE task_id = ?", (task_id,))
            conn.commit()
        finally:
            conn.close()

    # ── Helpers ──

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        """Convert a DB row to a dict with JSON fields parsed."""
        d = dict(row)
        for json_field in ("requirements", "parse_result",
                           "section_checked", "generated_sections"):
            if json_field in d and isinstance(d[json_field], str):
                try:
                    d[json_field] = json.loads(d[json_field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d


# ── Singleton ──

_store_instance: Optional[BiddingStore] = None


def get_bidding_store() -> BiddingStore:
    """Get or create the singleton BiddingStore."""
    global _store_instance
    if _store_instance is None:
        _store_instance = BiddingStore()
    return _store_instance
