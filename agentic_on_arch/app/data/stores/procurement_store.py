"""ProcurementStore — 采购项目数据存储。

管理: 采购项目、采购文件、供应商响应、评审会、评审打分。
"""

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DB_PATH = os.path.join(_DATA_DIR, "procurement", "procurement.db")


class ProcurementStore:
    """采购项目数据存储 (SQLite)。"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self._ensure_db()

    def _ensure_db(self):
        """创建数据库和表"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- 采购项目
                CREATE TABLE IF NOT EXISTS procurement_projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    budget REAL,
                    method TEXT NOT NULL DEFAULT 'open_bidding',
                    industry TEXT DEFAULT '',
                    description TEXT DEFAULT '',
                    status TEXT DEFAULT 'draft',
                    created_by TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                );

                -- 采购文件
                CREATE TABLE IF NOT EXISTS procurement_documents (
                    id TEXT PRIMARY KEY,
                    project_id TEXT REFERENCES procurement_projects(id),
                    version INTEGER DEFAULT 1,
                    content TEXT DEFAULT '{}',
                    template_id TEXT DEFAULT '',
                    parameters TEXT DEFAULT '{}',
                    review_result TEXT DEFAULT '{}',
                    file_path TEXT DEFAULT '',
                    status TEXT DEFAULT 'draft',
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                );

                -- 供应商响应文件
                CREATE TABLE IF NOT EXISTS supplier_responses (
                    id TEXT PRIMARY KEY,
                    project_id TEXT REFERENCES procurement_projects(id),
                    supplier_name TEXT NOT NULL,
                    file_path TEXT DEFAULT '',
                    parsed_content TEXT DEFAULT '{}',
                    qualification_result TEXT DEFAULT '{}',
                    compliance_result TEXT DEFAULT '{}',
                    deviation_table TEXT DEFAULT '{}',
                    collusion_signals TEXT DEFAULT '{}',
                    status TEXT DEFAULT 'imported',
                    created_at TEXT DEFAULT (datetime('now'))
                );

                -- 评审会
                CREATE TABLE IF NOT EXISTS review_sessions (
                    id TEXT PRIMARY KEY,
                    project_id TEXT REFERENCES procurement_projects(id),
                    status TEXT DEFAULT 'pending',
                    drawn_experts TEXT DEFAULT '[]',
                    scoring_rules TEXT DEFAULT '{}',
                    summary TEXT DEFAULT '{}',
                    report_path TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now')),
                    completed_at TEXT
                );

                -- 评审打分
                CREATE TABLE IF NOT EXISTS review_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT REFERENCES review_sessions(id),
                    expert_id TEXT,
                    response_id TEXT REFERENCES supplier_responses(id),
                    scores TEXT DEFAULT '{}',
                    reason TEXT DEFAULT '',
                    warnings TEXT DEFAULT '[]',
                    submitted_at TEXT DEFAULT (datetime('now'))
                );
            """)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # --- 采购项目 CRUD ---

    def create_project(self, name: str, method: str = "open_bidding",
                       budget: float = 0, **kwargs) -> Dict[str, Any]:
        """创建采购项目"""
        project_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO procurement_projects
                   (id, name, budget, method, industry, description, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'draft', ?, ?)""",
                (project_id, name, budget, method,
                 kwargs.get("industry", ""), kwargs.get("description", ""),
                 now, now)
            )
        return self.get_project(project_id)

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """获取采购项目详情"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM procurement_projects WHERE id=?", (project_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_projects(self, status: str = None) -> List[Dict[str, Any]]:
        """列出采购项目"""
        with self._conn() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM procurement_projects WHERE status=? ORDER BY created_at DESC",
                    (status,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM procurement_projects ORDER BY created_at DESC"
                ).fetchall()
            return [dict(r) for r in rows]

    def update_project(self, project_id: str, **kwargs) -> Optional[Dict]:
        """更新采购项目"""
        fields = []
        values = []
        for key in ["name", "budget", "method", "industry", "description", "status"]:
            if key in kwargs:
                fields.append(f"{key}=?")
                values.append(kwargs[key])
        if not fields:
            return self.get_project(project_id)
        fields.append("updated_at=?")
        values.append(datetime.now().isoformat())
        values.append(project_id)
        with self._conn() as conn:
            conn.execute(
                f"UPDATE procurement_projects SET {', '.join(fields)} WHERE id=?",
                values
            )
        return self.get_project(project_id)

    # --- 供应商响应 ---

    def add_response(self, project_id: str, supplier_name: str,
                     file_path: str = "") -> Dict[str, Any]:
        """添加供应商响应文件"""
        response_id = str(uuid.uuid4())[:8]
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO supplier_responses
                   (id, project_id, supplier_name, file_path, status)
                   VALUES (?, ?, ?, ?, 'imported')""",
                (response_id, project_id, supplier_name, file_path)
            )
        return self.get_response(response_id)

    def get_response(self, response_id: str) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM supplier_responses WHERE id=?", (response_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_responses(self, project_id: str) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM supplier_responses WHERE project_id=? ORDER BY created_at",
                (project_id,)
            ).fetchall()
            return [dict(r) for r in rows]


# 全局单例
_store: Optional[ProcurementStore] = None


def get_procurement_store() -> ProcurementStore:
    global _store
    if _store is None:
        _store = ProcurementStore()
    return _store
