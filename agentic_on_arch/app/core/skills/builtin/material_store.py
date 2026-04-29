"""Material store — SQLite-backed storage for extracted bid materials.

Manages the lifecycle of materials extracted from historical bid documents:
- Save structured data (resumes, projects, qualifications) to SQLite
- Vectorize narrative chunks with BGE embedding
- Search materials by type and relevance
"""

import json
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional

import numpy as np

from app.utils.logger import logger


# Default storage directory
MATERIAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "..", "..", "..", "data", "materials")

# Key field mapping per category
_KEY_FIELDS = {
    "resumes": "name",
    "projects": "project_name",
    "qualifications": "name",
}

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS companies (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    is_default  INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bid_projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, name)
);

CREATE TABLE IF NOT EXISTS materials (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id   INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    project_id   INTEGER REFERENCES bid_projects(id) ON DELETE SET NULL,
    category     TEXT NOT NULL,
    name         TEXT NOT NULL,
    entity_type  TEXT DEFAULT '',
    data         TEXT NOT NULL DEFAULT '{}',
    source_file  TEXT DEFAULT '',
    source_path  TEXT DEFAULT '',
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, category, name)
);

CREATE TABLE IF NOT EXISTS narrative_chunks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    project_id  INTEGER REFERENCES bid_projects(id) ON DELETE SET NULL,
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,
    source_file TEXT DEFAULT '',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pending_uploads (
    upload_id   TEXT PRIMARY KEY,
    data        TEXT NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS image_meta (
    image_hash   TEXT PRIMARY KEY,
    ocr_text     TEXT NOT NULL DEFAULT '',
    image_type   TEXT NOT NULL DEFAULT 'unknown',
    structured   TEXT NOT NULL DEFAULT '{}',
    confidence   REAL DEFAULT 0.0,
    line_count   INTEGER DEFAULT 0,
    image_path   TEXT DEFAULT '',
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reference_sections (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    company      TEXT NOT NULL DEFAULT '',
    section_type TEXT NOT NULL DEFAULT '',
    title        TEXT NOT NULL,
    content      TEXT NOT NULL,
    source_file  TEXT DEFAULT '',
    score_info   TEXT DEFAULT '',
    quality_rating INTEGER DEFAULT 0,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_materials_company ON materials(company_id);
CREATE INDEX IF NOT EXISTS idx_materials_project ON materials(project_id);
CREATE INDEX IF NOT EXISTS idx_materials_category ON materials(category);
CREATE INDEX IF NOT EXISTS idx_narratives_company ON narrative_chunks(company_id);
CREATE INDEX IF NOT EXISTS idx_image_meta_type ON image_meta(image_type);
CREATE INDEX IF NOT EXISTS idx_ref_sections_type ON reference_sections(section_type);
"""

# Migration SQL for existing databases (adds new columns/tables)
_MIGRATION_SQL = [
    "CREATE TABLE IF NOT EXISTS bid_projects (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE, name TEXT NOT NULL, description TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(company_id, name))",
    # entity_type column for qualification sub-classification
    "ALTER TABLE materials ADD COLUMN entity_type TEXT DEFAULT ''",
    "CREATE INDEX IF NOT EXISTS idx_materials_entity_type ON materials(entity_type)",
    # reference_sections for historical winning bid sections RAG
    "CREATE TABLE IF NOT EXISTS reference_sections (id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT NOT NULL DEFAULT '', section_type TEXT NOT NULL DEFAULT '', title TEXT NOT NULL, content TEXT NOT NULL, source_file TEXT DEFAULT '', score_info TEXT DEFAULT '', quality_rating INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
    "CREATE INDEX IF NOT EXISTS idx_ref_sections_type ON reference_sections(section_type)",
]

def _safe_add_column(conn, table, column, col_type, default=""):
    """Add column if it doesn't exist (SQLite has no IF NOT EXISTS for ALTER)."""
    try:
        default_clause = f" DEFAULT {default}" if default else ""
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}")
        logger.info(f"[migration] Added {table}.{column}")
    except sqlite3.OperationalError:
        pass  # column already exists


class MaterialStore:
    """Manage extracted materials from historical bid documents (SQLite)."""

    def __init__(self, base_dir: str = ""):
        self.base_dir = base_dir or MATERIAL_DIR
        os.makedirs(self.base_dir, exist_ok=True)

        self.db_path = os.path.join(self.base_dir, "materials.db")

        # In-memory vector index for narrative chunks
        self._narrative_vectors = None  # type: Optional[np.ndarray]
        self._narrative_chunks = []     # type: List[Dict]
        self._embedding_service = None

        # Initialize database
        self._init_db()

        # Auto-migrate from JSON if needed
        self._migrate_from_json()

    # ── Database Helpers ──

    def _get_conn(self) -> sqlite3.Connection:
        """Get a SQLite connection with foreign keys enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create tables if they don't exist, run migrations."""
        conn = self._get_conn()
        try:
            conn.executescript(_SCHEMA_SQL)
            # Run migrations for existing databases
            for sql in _MIGRATION_SQL:
                try:
                    conn.execute(sql)
                except sqlite3.OperationalError:
                    pass
            _safe_add_column(conn, "materials", "project_id",
                            "INTEGER REFERENCES bid_projects(id) ON DELETE SET NULL")
            _safe_add_column(conn, "narrative_chunks", "project_id",
                            "INTEGER REFERENCES bid_projects(id) ON DELETE SET NULL")
            conn.commit()
        finally:
            conn.close()

    def _get_or_create_company(self, conn: sqlite3.Connection,
                                company_name: str) -> int:
        """Get company id by name, creating if it doesn't exist."""
        row = conn.execute(
            "SELECT id FROM companies WHERE name = ?", (company_name,)
        ).fetchone()
        if row:
            return row[0]
        cur = conn.execute(
            "INSERT INTO companies (name) VALUES (?)", (company_name,)
        )
        return cur.lastrowid

    def _get_or_create_project(self, conn: sqlite3.Connection,
                                company_id: int, project_name: str) -> int:
        """Get project id by name under a company, creating if needed."""
        row = conn.execute(
            "SELECT id FROM bid_projects WHERE company_id = ? AND name = ?",
            (company_id, project_name)
        ).fetchone()
        if row:
            return row[0]
        cur = conn.execute(
            "INSERT INTO bid_projects (company_id, name) VALUES (?, ?)",
            (company_id, project_name)
        )
        return cur.lastrowid

    # ── Project CRUD ──

    def get_projects_for_company(self, company: str) -> List[Dict]:
        """List all bid projects under a company."""
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT p.id, p.name, p.description, p.created_at,
                       (SELECT COUNT(*) FROM materials m
                        WHERE m.project_id = p.id) as material_count
                FROM bid_projects p
                JOIN companies c ON p.company_id = c.id
                WHERE c.name = ?
                ORDER BY p.created_at DESC
            """, (company,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def create_project(self, company: str, project_name: str,
                       description: str = "") -> Dict:
        """Create a new bid project under a company."""
        conn = self._get_conn()
        try:
            company_id = self._get_or_create_company(conn, company)
            cur = conn.execute("""
                INSERT INTO bid_projects (company_id, name, description)
                VALUES (?, ?, ?)
            """, (company_id, project_name, description))
            conn.commit()
            return {"id": cur.lastrowid, "name": project_name,
                    "company": company}
        finally:
            conn.close()

    def delete_project(self, company: str, project_name: str) -> bool:
        """Delete a bid project and all its materials."""
        conn = self._get_conn()
        try:
            # Find the project id
            row = conn.execute("""
                SELECT p.id FROM bid_projects p
                JOIN companies c ON p.company_id = c.id
                WHERE c.name = ? AND p.name = ?
            """, (company, project_name)).fetchone()
            if not row:
                return False
            pid = row[0]
            # Delete all materials under this project
            conn.execute("DELETE FROM materials WHERE project_id = ?", (pid,))
            conn.execute("DELETE FROM narrative_chunks WHERE project_id = ?", (pid,))
            conn.execute("DELETE FROM bid_projects WHERE id = ?", (pid,))
            conn.commit()
            return True
        finally:
            conn.close()

    # ── JSON Migration ──

    def _migrate_from_json(self):
        """Auto-import data from old JSON files if they exist."""
        json_files = {
            "resumes": os.path.join(self.base_dir, "resumes.json"),
            "projects": os.path.join(self.base_dir, "projects.json"),
            "qualifications": os.path.join(self.base_dir, "qualifications.json"),
        }
        narratives_file = os.path.join(self.base_dir, "narrative_chunks.json")
        config_file = os.path.join(self.base_dir, "config.json")

        # Check if any JSON file exists
        has_json = any(os.path.isfile(f) for f in json_files.values())
        has_json = has_json or os.path.isfile(narratives_file)
        if not has_json:
            return

        # Check if DB already has data (avoid re-migration)
        conn = self._get_conn()
        try:
            count = conn.execute("SELECT COUNT(*) FROM materials").fetchone()[0]
            if count > 0:
                logger.info("SQLite already has data, skipping JSON migration")
                return
        finally:
            conn.close()

        logger.info("Migrating JSON data to SQLite...")

        # Load config for default company
        default_company = ""
        if os.path.isfile(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                default_company = cfg.get("default_company", "")
            except Exception:
                pass

        conn = self._get_conn()
        try:
            total = 0

            # Migrate materials (resumes, projects, qualifications)
            for category, filepath in json_files.items():
                if not os.path.isfile(filepath):
                    continue
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        items = json.load(f)
                except Exception:
                    continue
                if not isinstance(items, list):
                    continue

                key_field = _KEY_FIELDS[category]
                for item in items:
                    company = item.pop("_company", "") or default_company or "未分类"
                    name = item.get(key_field, "")
                    if not name:
                        continue
                    company_id = self._get_or_create_company(conn, company)
                    source_file = item.pop("_source_file", "")
                    source_path = item.pop("_source_path", "")
                    conn.execute("""
                        INSERT OR REPLACE INTO materials
                        (company_id, category, name, data, source_file, source_path)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (company_id, category, name,
                          json.dumps(item, ensure_ascii=False),
                          source_file, source_path))
                    total += 1

                # Rename to .bak
                bak = filepath + ".bak"
                os.rename(filepath, bak)
                logger.info(f"  Migrated {filepath} → {bak}")

            # Migrate narrative chunks
            if os.path.isfile(narratives_file):
                try:
                    with open(narratives_file, "r", encoding="utf-8") as f:
                        chunks = json.load(f)
                except Exception:
                    chunks = []
                if isinstance(chunks, list):
                    for chunk in chunks:
                        company = chunk.pop("_company", "") or default_company or "未分类"
                        company_id = self._get_or_create_company(conn, company)
                        conn.execute("""
                            INSERT INTO narrative_chunks
                            (company_id, title, content, source_file)
                            VALUES (?, ?, ?, ?)
                        """, (company_id,
                              chunk.get("title", ""),
                              chunk.get("content", ""),
                              chunk.get("_source_file", "")))
                        total += 1
                bak = narratives_file + ".bak"
                os.rename(narratives_file, bak)

            # Migrate default company
            if default_company:
                self.set_default_company(default_company, conn=conn)

            conn.commit()
            logger.info(f"JSON→SQLite migration complete: {total} items imported")

            # Backup config
            if os.path.isfile(config_file):
                os.rename(config_file, config_file + ".bak")

        except Exception as e:
            conn.rollback()
            logger.error(f"JSON migration failed: {e}")
        finally:
            conn.close()

    # ── Save Methods ──

    # ── Entity type classification for qualifications ──
    # (keywords, entity_type) — first match wins
    _ENTITY_TYPE_RULES = [
        # Ranking proof with images (screenshots)
        (['排名证明'], 'ranking_proof'),
        # Rankings/ratings from authoritative sources
        (['Legal 500', 'LEGALBAND', 'IFLR', '钱伯斯', 'Chambers',
          'ALB', '亚洲法律', '榜单', '排名', '等'], 'ranking'),
        # Awards and honors
        (['优秀律师事务所', '先进集体', '荣誉', '奖', '表彰',
          '破产管理人考核'], 'award'),
        # Firm-level qualifications
        (['营业执照', '执业许可', '律所证'], 'firm_license'),
        # Financial audit reports
        (['审计', '财务', '报表', '审计报告'], 'firm_audit'),
        # Personal certificates (mixed into qualifications)
        (['身份证', '学历', '执业证', '资格证', '社保', '实习证',
          '律师执照', '年检'], 'personal_cert'),
        # Financial/payment related
        (['保证金', '缴费'], 'financial_proof'),
    ]

    @classmethod
    def _classify_entity_type(cls, name, item=None):
        """Classify a qualification record into a sub-type.

        Args:
            name: Material name/title
            item: Full item dict (optional, for issuer-based hints)

        Returns:
            entity_type string like 'award', 'ranking', 'firm_license', etc.
        """
        # Combine name + issuer for broader keyword matching
        text = name
        if item:
            issuer = item.get('issuer', '') or ''
            text = f"{name} {issuer}"

        for keywords, etype in cls._ENTITY_TYPE_RULES:
            if any(kw in text for kw in keywords):
                return etype

        return 'other_qual'

    # ── Image certificate type classification rules ──
    _CERT_TYPE_RULES = [
        # (keywords_in_name, cert_type, label)
        (['身份证'], 'id_card', '身份证'),
        (['学历', '毕业证', '学位'], 'degree', '学历证书'),
        (['执业证', '律师证'], 'practice_cert', '律师执业证'),
        (['资格证', '法律职业'], 'bar_cert', '法律职业资格证'),
        (['社保', '社会保险'], 'social_security', '社保证明'),
        (['实习证', '实习'], 'intern_cert', '实习证'),
    ]

    @classmethod
    def _classify_cert_type(cls, name_or_title):
        """Classify certificate type from a record name or section title."""
        for keywords, cert_type, label in cls._CERT_TYPE_RULES:
            if any(kw in name_or_title for kw in keywords):
                return cert_type, label
        return 'other', '其他证件'

    @classmethod
    def _extract_person_name_from_record(cls, record_name):
        """Try to extract a real person name from an artifact record name.
        E.g., '身份证扫描件-钟雨' → '钟雨', '范彩云-硕士毕业证书' → '范彩云'
        """
        import re
        name = record_name.strip()

        # Remove leading numbers like "1. " "2. "
        name = re.sub(r'^[\d]+[.、\s]+', '', name)

        # Keywords that indicate a part is a document type, NOT a person name
        _DOC_KEYWORDS = [
            '身份证', '学历', '毕业证', '学位', '执业证', '资格证',
            '证书', '扫描件', '副本', '许可证', '社保', '实习证',
            '律师', '平台', '律所', '事务所', '信息', '记录',
        ]

        def _is_person_part(part):
            """Check if a part looks like a Chinese person name."""
            if not (2 <= len(part) <= 4):
                return False
            if not all('\u4e00' <= c <= '\u9fff' for c in part):
                return False
            # Reject if it contains document keywords
            if any(kw in part for kw in _DOC_KEYWORDS):
                return False
            return True

        # Common patterns: "XXX-人名" or "人名-XXX" or "人名 - XXX"
        # Split by common separators
        for sep in ['-', '—', '_', ' ']:
            parts = [p.strip() for p in name.split(sep) if p.strip()]
            if len(parts) >= 2:
                for part in parts:
                    if _is_person_part(part):
                        return part

        return None

    def _consolidate_person_images(self, materials):
        """Post-process extracted materials: merge artifact records' images
        into their parent person records. Acts as a safety net for data
        that was not pre-consolidated by the parser.

        For example:
          "身份证扫描件-钟雨" (has 1 image) + "学历证书-钟雨" (has 1 image)
          → merge images into "钟雨" record → remove artifact records

        Also converts _images from flat list to typed list:
          ["hash1.png", "hash2.png"]
          → [{"file": "hash1.png", "type": "id_card", "label": "身份证"}, ...]
        """
        resumes = materials.get('resumes', [])
        if not resumes:
            return

        # Step 1: Separate real people from artifact records
        real_people = {}     # name → resume dict
        artifacts = []       # records to merge + remove

        # Non-person keywords (same as MaterialMatcher)
        _NON_PERSON_KW = [
            '身份证', '学历', '毕业证', '学位证', '实习证', '执业证',
            '资格证', '社保', '证书', '许可证', '平台', '律师事务所',
            '副本', '扫描件', '法律职业', '信息公示',
        ]

        for resume in resumes:
            name = (resume.get('name') or '').strip()
            if not name:
                continue

            is_artifact = (
                name[0].isdigit()
                or any(kw in name for kw in _NON_PERSON_KW)
                or len(name) > 6
            )

            if is_artifact:
                artifacts.append(resume)
            else:
                real_people[name] = resume

        if not artifacts:
            # No artifacts to merge - but still tag existing images
            for resume in resumes:
                self._tag_images(resume, resume.get('_source_section', ''))
            return

        # Step 2: For each artifact, find the parent person and merge images
        merged_count = 0
        removed = set()

        for artifact in artifacts:
            art_name = (artifact.get('name') or '').strip()
            art_images = artifact.get('_images', [])
            if not art_images:
                removed.add(art_name)  # No images, just remove
                continue

            # Extract person name from artifact name
            person_name = self._extract_person_name_from_record(art_name)
            if not person_name or person_name not in real_people:
                # Can't find parent - keep as is
                continue

            # Classify cert type
            cert_type, cert_label = self._classify_cert_type(art_name)

            # Merge images into parent
            parent = real_people[person_name]
            parent_images = parent.get('_images', [])

            # Convert to typed format if needed
            if parent_images and isinstance(parent_images[0], str):
                parent_images = [
                    {'file': f, 'type': 'other', 'label': '证件'}
                    for f in parent_images
                ]

            for img_file in art_images:
                if isinstance(img_file, str):
                    img_entry = {
                        'file': img_file,
                        'type': cert_type,
                        'label': cert_label,
                    }
                else:
                    img_entry = img_file
                # Dedup
                existing_files = {
                    (e['file'] if isinstance(e, dict) else e)
                    for e in parent_images
                }
                if img_entry.get('file', img_file) not in existing_files:
                    parent_images.append(img_entry)

            parent['_images'] = parent_images
            removed.add(art_name)
            merged_count += 1

            logger.info(
                f"  Consolidated: '{art_name}' → '{person_name}' "
                f"({len(art_images)} images, type={cert_type})"
            )

        # Step 3: Remove merged artifact records from resumes list
        if removed:
            materials['resumes'] = [
                r for r in resumes
                if (r.get('name') or '').strip() not in removed
            ]
            logger.info(
                f"  Consolidation complete: merged {merged_count} artifact records, "
                f"removed {len(removed)} entries, "
                f"{len(materials['resumes'])} resumes remaining"
            )

        # Step 4: Tag remaining images with cert_type
        for resume in materials.get('resumes', []):
            self._tag_images(resume, resume.get('_source_section', ''))

    @classmethod
    def _tag_images(cls, item, source_hint=''):
        """Convert flat _images list to typed format if not already."""
        images = item.get('_images', [])
        if not images:
            return
        if images and isinstance(images[0], dict):
            return  # Already typed

        # Convert to typed format using source hint
        cert_type, cert_label = cls._classify_cert_type(source_hint)
        item['_images'] = [
            {'file': f, 'type': cert_type, 'label': cert_label}
            for f in images
        ]

    def save_materials(self, materials: Dict[str, Any],
                       company: str = "",
                       project: str = "") -> Dict[str, int]:
        """Save extracted materials to SQLite, merging with existing data.

        Args:
            materials: Dict with resumes, projects, qualifications, narrative_chunks
            company: Company name to tag on every item (uses default if empty)
            project: Optional bid project name (if set, materials are project-level)

        Returns dict with counts of items saved per type.
        """
        company = company or self.get_default_company() or "未分类"
        counts = {}

        # ── Pre-save: consolidate person images ──
        self._consolidate_person_images(materials)

        conn = self._get_conn()
        try:
            company_id = self._get_or_create_company(conn, company)
            project_id = None
            if project:
                project_id = self._get_or_create_project(
                    conn, company_id, project)

            for category in ["resumes", "projects", "qualifications"]:
                items = materials.get(category, [])
                if not items:
                    continue
                key_field = _KEY_FIELDS[category]
                saved = 0
                for idx, item in enumerate(items):
                    name = item.get(key_field) or ""
                    if not name:
                        # Generate fallback name from available fields
                        name = (item.get("_source_section")
                                or item.get("title")
                                or item.get("description", "")[:30]
                                or f"{category}_{idx+1}")
                        item[key_field] = name
                        logger.info(f"[save] Generated fallback name for "
                                    f"{category}: '{name}'")
                    # Auto-classify entity_type for qualifications
                    entity_type = ""
                    if category == "qualifications":
                        entity_type = self._classify_entity_type(name, item)

                    # Remove internal fields before storing
                    clean = {k: v for k, v in item.items()
                             if not k.startswith("_") or k == "_images"}
                    source_file = item.get("_source_file", "")
                    source_path = item.get("_source_path", "")
                    conn.execute("""
                        INSERT OR REPLACE INTO materials
                        (company_id, project_id, category, name, entity_type,
                         data, source_file, source_path, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (company_id, project_id, category, name,
                          entity_type,
                          json.dumps(clean, ensure_ascii=False),
                          source_file, source_path))
                    saved += 1
                counts[category] = saved

            # Save narrative chunks
            chunks = materials.get("narrative_chunks", [])
            if chunks:
                saved = 0
                for chunk in chunks:
                    conn.execute("""
                        INSERT INTO narrative_chunks
                        (company_id, project_id, title, content, source_file)
                        VALUES (?, ?, ?, ?, ?)
                    """, (company_id, project_id,
                          chunk.get("title", ""),
                          chunk.get("content", ""),
                          chunk.get("_source_file", "")))
                    saved += 1
                counts["narrative_chunks"] = saved

            conn.commit()
        finally:
            conn.close()

        project_info = f", project={project}" if project else ""
        logger.info(f"Materials saved: {counts} (company={company}{project_info})")
        return counts

    # ── Load Methods ──

    def _rows_to_dicts(self, rows, category: str) -> List[Dict]:
        """Convert DB rows to dicts matching old JSON format."""
        key_field = _KEY_FIELDS.get(category, "name")
        results = []
        for row in rows:
            data = json.loads(row["data"]) if row["data"] else {}
            data[key_field] = row["name"]
            data["_company"] = row["company_name"]
            # Include entity_type for sub-classification filtering
            et = row["entity_type"] if "entity_type" in row.keys() else ""
            if et:
                data["_entity_type"] = et
            if row["source_file"]:
                data["_source_file"] = row["source_file"]
            if row["source_path"]:
                data["_source_path"] = row["source_path"]
            results.append(data)
        return results

    def _get_materials(self, category: str,
                       company: str = "",
                       project_id: int = None) -> List[Dict]:
        """Get materials by category, optionally filtered by company or project."""
        conn = self._get_conn()
        try:
            if project_id:
                rows = conn.execute("""
                    SELECT m.*, c.name as company_name
                    FROM materials m JOIN companies c ON m.company_id = c.id
                    WHERE m.category = ? AND m.project_id = ?
                    ORDER BY m.name
                """, (category, project_id)).fetchall()
            elif company:
                rows = conn.execute("""
                    SELECT m.*, c.name as company_name
                    FROM materials m JOIN companies c ON m.company_id = c.id
                    WHERE m.category = ? AND c.name = ?
                    ORDER BY m.name
                """, (category, company)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT m.*, c.name as company_name
                    FROM materials m JOIN companies c ON m.company_id = c.id
                    WHERE m.category = ?
                    ORDER BY m.name
                """, (category,)).fetchall()
            return self._rows_to_dicts(rows, category)
        finally:
            conn.close()

    def get_resumes(self, company: str = "", project_id: int = None) -> List[Dict]:
        """Get stored resumes, optionally filtered by company or project."""
        return self._get_materials("resumes", company, project_id)

    def get_projects(self, company: str = "", project_id: int = None) -> List[Dict]:
        """Get stored projects, optionally filtered by company or project."""
        return self._get_materials("projects", company, project_id)

    def get_qualifications(self, company: str = "", project_id: int = None,
                           entity_type: str = "") -> List[Dict]:
        """Get stored qualifications, optionally filtered by company, project,
        or entity_type (award/firm_license/firm_audit/personal_cert/ranking)."""
        all_quals = self._get_materials("qualifications", company, project_id)
        if entity_type:
            # Support comma-separated types: "award,ranking"
            types = set(t.strip() for t in entity_type.split(','))
            all_quals = [q for q in all_quals if q.get('_entity_type', '') in types]
        return all_quals

    def get_narrative_chunks(self, company: str = "") -> List[Dict]:
        """Get stored narrative chunks, optionally filtered by company."""
        conn = self._get_conn()
        try:
            if company:
                rows = conn.execute("""
                    SELECT n.*, c.name as company_name
                    FROM narrative_chunks n
                    JOIN companies c ON n.company_id = c.id
                    WHERE c.name = ?
                    ORDER BY n.id
                """, (company,)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT n.*, c.name as company_name
                    FROM narrative_chunks n
                    JOIN companies c ON n.company_id = c.id
                    ORDER BY n.id
                """).fetchall()
            return [{"title": r["title"], "content": r["content"],
                     "_company": r["company_name"],
                     "_source_file": r["source_file"] or ""}
                    for r in rows]
        finally:
            conn.close()

    def get_all_materials(self, company: str = "",
                          project_id: int = None) -> Dict[str, Any]:
        """Get all materials as a dict, optionally filtered by company or project."""
        return {
            "resumes": self.get_resumes(company, project_id),
            "projects": self.get_projects(company, project_id),
            "qualifications": self.get_qualifications(company, project_id),
            "narrative_chunks": self.get_narrative_chunks(company),
        }

    def get_summary(self, company: str = "",
                    project_id: int = None) -> Dict[str, int]:
        """Get count summary, optionally filtered by company or project."""
        conn = self._get_conn()
        try:
            result = {"resumes": 0, "projects": 0, "qualifications": 0,
                      "narrative_chunks": 0}
            if project_id:
                rows = conn.execute("""
                    SELECT m.category, COUNT(*) as cnt
                    FROM materials m
                    WHERE m.project_id = ?
                    GROUP BY m.category
                """, (project_id,)).fetchall()
                nc = conn.execute("""
                    SELECT COUNT(*) FROM narrative_chunks
                    WHERE project_id = ?
                """, (project_id,)).fetchone()[0]
            elif company:
                rows = conn.execute("""
                    SELECT m.category, COUNT(*) as cnt
                    FROM materials m JOIN companies c ON m.company_id = c.id
                    WHERE c.name = ?
                    GROUP BY m.category
                """, (company,)).fetchall()
                nc = conn.execute("""
                    SELECT COUNT(*) FROM narrative_chunks n
                    JOIN companies c ON n.company_id = c.id
                    WHERE c.name = ?
                """, (company,)).fetchone()[0]
            else:
                rows = conn.execute("""
                    SELECT category, COUNT(*) as cnt
                    FROM materials GROUP BY category
                """).fetchall()
                nc = conn.execute(
                    "SELECT COUNT(*) FROM narrative_chunks"
                ).fetchone()[0]

            for r in rows:
                result[r["category"]] = r["cnt"]
            result["narrative_chunks"] = nc
            return result
        finally:
            conn.close()

    # ── Company Management ──

    def get_companies(self) -> List[Dict]:
        """Get list of all companies with item counts."""
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT c.name,
                    COALESCE(SUM(CASE WHEN m.category='resumes' THEN 1 END), 0) as resumes,
                    COALESCE(SUM(CASE WHEN m.category='projects' THEN 1 END), 0) as projects,
                    COALESCE(SUM(CASE WHEN m.category='qualifications' THEN 1 END), 0) as qualifications,
                    COUNT(m.id) as total
                FROM companies c
                LEFT JOIN materials m ON m.company_id = c.id
                GROUP BY c.id, c.name
                ORDER BY c.name
            """).fetchall()
            return [{"name": r["name"], "total": r["total"],
                     "resumes": r["resumes"], "projects": r["projects"],
                     "qualifications": r["qualifications"]}
                    for r in rows]
        finally:
            conn.close()

    # ── Image OCR Metadata ──

    def save_image_meta(self, ocr_results: List[Dict]) -> int:
        """Save batch OCR results to image_meta table.
        
        Args:
            ocr_results: List of dicts from image_ocr.ocr_image()
        
        Returns:
            Number of records saved
        """
        if not ocr_results:
            return 0

        conn = self._get_conn()
        saved = 0
        try:
            for r in ocr_results:
                if r.get("error") and not r.get("ocr_text"):
                    continue
                conn.execute("""
                    INSERT OR REPLACE INTO image_meta
                    (image_hash, ocr_text, image_type, structured,
                     confidence, line_count, image_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    r.get("image_hash", ""),
                    r.get("ocr_text", ""),
                    r.get("image_type", "unknown"),
                    json.dumps(r.get("structured", {}), ensure_ascii=False),
                    r.get("confidence", 0.0),
                    r.get("line_count", 0),
                    r.get("image_path", ""),
                ))
                saved += 1
            conn.commit()
        finally:
            conn.close()

        logger.info(f"Saved {saved} image OCR results")
        return saved

    def get_image_meta(self, image_hash: str) -> Optional[Dict]:
        """Get OCR metadata for a single image."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM image_meta WHERE image_hash = ?",
                (image_hash,)
            ).fetchone()
            if not row:
                return None
            return {
                "image_hash": row["image_hash"],
                "ocr_text": row["ocr_text"],
                "image_type": row["image_type"],
                "structured": json.loads(row["structured"] or "{}"),
                "confidence": row["confidence"],
                "line_count": row["line_count"],
                "image_path": row["image_path"],
            }
        finally:
            conn.close()

    def get_all_image_meta(self) -> List[Dict]:
        """Get all image OCR metadata."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM image_meta ORDER BY image_type, image_hash"
            ).fetchall()
            return [{
                "image_hash": r["image_hash"],
                "ocr_text": r["ocr_text"],
                "image_type": r["image_type"],
                "structured": json.loads(r["structured"] or "{}"),
                "confidence": r["confidence"],
                "line_count": r["line_count"],
                "image_path": r["image_path"],
            } for r in rows]
        finally:
            conn.close()

    def get_processed_image_hashes(self) -> set:
        """Get set of image hashes already OCR-processed."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT image_hash FROM image_meta"
            ).fetchall()
            return {r["image_hash"] for r in rows}
        finally:
            conn.close()

    def get_images_for_material(self, material_name: str,
                                company: str = "") -> List[Dict]:
        """Get image metadata for a specific material's _images.
        
        Looks up the material's _images field, then joins with image_meta
        to return enriched image info (with OCR data).
        """
        conn = self._get_conn()
        try:
            if company:
                row = conn.execute("""
                    SELECT m.data FROM materials m
                    JOIN companies c ON m.company_id = c.id
                    WHERE m.name = ? AND c.name = ?
                """, (material_name, company)).fetchone()
            else:
                row = conn.execute("""
                    SELECT data FROM materials WHERE name = ?
                """, (material_name,)).fetchone()

            if not row:
                return []

            data = json.loads(row["data"] or "{}")
            image_files = data.get("_images", [])
            if not image_files:
                return []

            # Get OCR metadata for each image
            results = []
            for img_file in image_files:
                img_hash = os.path.splitext(img_file)[0]
                meta = self.get_image_meta(img_hash)
                if meta:
                    results.append(meta)
                else:
                    # No OCR data yet, return basic info
                    results.append({
                        "image_hash": img_hash,
                        "image_path": os.path.join(
                            self.images_dir, img_file
                        ) if hasattr(self, 'images_dir') else img_file,
                        "ocr_text": "",
                        "image_type": "unknown",
                        "structured": {},
                    })
            return results
        finally:
            conn.close()

    def get_default_company(self) -> str:
        """Get default company name."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT name FROM companies WHERE is_default = 1 LIMIT 1"
            ).fetchone()
            return row["name"] if row else ""
        finally:
            conn.close()

    def set_default_company(self, company: str,
                            conn: sqlite3.Connection = None):
        """Set default company name."""
        own_conn = conn is None
        if own_conn:
            conn = self._get_conn()
        try:
            conn.execute("UPDATE companies SET is_default = 0")
            company_id = self._get_or_create_company(conn, company)
            conn.execute(
                "UPDATE companies SET is_default = 1 WHERE id = ?",
                (company_id,)
            )
            if own_conn:
                conn.commit()
            logger.info(f"Default company set to: {company}")
        finally:
            if own_conn:
                conn.close()

    def delete_company(self, company: str) -> Dict[str, int]:
        """Delete all materials belonging to a company."""
        conn = self._get_conn()
        try:
            # Get counts before delete
            row = conn.execute(
                "SELECT id FROM companies WHERE name = ?", (company,)
            ).fetchone()
            if not row:
                return {"resumes": 0, "projects": 0, "qualifications": 0,
                        "narrative_chunks": 0}

            company_id = row["id"]
            deleted = {}
            for cat in ["resumes", "projects", "qualifications"]:
                cnt = conn.execute("""
                    SELECT COUNT(*) FROM materials
                    WHERE company_id = ? AND category = ?
                """, (company_id, cat)).fetchone()[0]
                deleted[cat] = cnt

            nc = conn.execute("""
                SELECT COUNT(*) FROM narrative_chunks
                WHERE company_id = ?
            """, (company_id,)).fetchone()[0]
            deleted["narrative_chunks"] = nc

            # CASCADE will delete materials and narrative_chunks
            conn.execute("DELETE FROM companies WHERE id = ?", (company_id,))
            conn.commit()
            logger.info(f"Company '{company}' deleted: {deleted}")
            return deleted
        finally:
            conn.close()

    def migrate_company(self, company: str) -> Dict[str, int]:
        """No-op for SQLite (kept for API compatibility)."""
        logger.info(f"migrate_company called for '{company}' — no-op in SQLite mode")
        return {"resumes": 0, "projects": 0, "qualifications": 0,
                "narrative_chunks": 0}

    # ── Pending Uploads ──

    def save_pending(self, upload_id: str, data: dict):
        """Save pending upload data to SQLite."""
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO pending_uploads (upload_id, data)
                VALUES (?, ?)
            """, (upload_id, json.dumps(data, ensure_ascii=False)))
            conn.commit()
        finally:
            conn.close()

    def pop_pending(self, upload_id: str) -> Optional[dict]:
        """Get and remove pending upload data."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT data FROM pending_uploads WHERE upload_id = ?",
                (upload_id,)
            ).fetchone()
            if not row:
                return None
            conn.execute(
                "DELETE FROM pending_uploads WHERE upload_id = ?",
                (upload_id,)
            )
            conn.commit()
            return json.loads(row["data"])
        finally:
            conn.close()

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
                                 top_k: int = 5,
                                 company: str = "") -> List[Dict]:
        """Semantic search narrative chunks using BGE embedding.

        Args:
            query: Search query text
            top_k: Number of results to return
            company: If provided, only search chunks belonging to this company
        """
        chunks = self.get_narrative_chunks(company=company)
        if not chunks:
            return []

        try:
            if self._embedding_service is None:
                from app.core.rag.embedding_service import EmbeddingService
                self._embedding_service = EmbeddingService()

            # Rebuild vector index when chunks change (different company or new data)
            chunks_key = tuple(c.get("content", "")[:50] for c in chunks)
            if (self._narrative_vectors is None
                    or len(self._narrative_chunks) != len(chunks)
                    or getattr(self, '_narrative_chunks_key', None) != chunks_key):
                self._narrative_chunks = chunks
                self._narrative_chunks_key = chunks_key
                texts = [c.get("content", "") for c in chunks]
                self._narrative_vectors = self._embedding_service.encode(texts)
                logger.info(f"Vectorized {len(texts)} narrative chunks"
                            f"{f' (company={company})' if company else ''}")

            query_vec = self._embedding_service.encode([query])
            scores = np.dot(self._narrative_vectors, query_vec.T).flatten()
            top_indices = np.argsort(scores)[::-1][:top_k]

            results = []
            for idx in top_indices:
                if scores[idx] > 0.3:
                    chunk = chunks[idx].copy()
                    chunk["similarity"] = float(scores[idx])
                    results.append(chunk)
            return results

        except Exception as e:
            logger.warning(f"Semantic search failed, falling back to keyword: {e}")
            q = query.lower()
            scored = [c for c in chunks if q in c.get("content", "").lower()]
            return scored[:top_k]

    # ── Reference Sections (historical winning bid sections) ──

    def save_reference_section(self, company, section_type, title,
                               content, source_file="", score_info=""):
        # type: (str, str, str, str, str, str) -> bool
        """Save a generated narrative section as reference for future RAG.

        Deduplicates by (company, section_type, title): updates if exists.
        Only saves sections with substantial content (>500 chars).
        """
        if len(content) < 500:
            return False
        conn = self._get_conn()
        try:
            c = conn.cursor()
            c.execute(
                "SELECT id FROM reference_sections "
                "WHERE company = ? AND section_type = ? AND title = ?",
                (company, section_type, title)
            )
            existing = c.fetchone()
            if existing:
                c.execute(
                    "UPDATE reference_sections SET content = ?, "
                    "source_file = ?, score_info = ?, created_at = CURRENT_TIMESTAMP "
                    "WHERE id = ?",
                    (content, source_file, score_info, existing[0])
                )
            else:
                c.execute(
                    "INSERT INTO reference_sections "
                    "(company, section_type, title, content, source_file, score_info) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (company, section_type, title, content, source_file, score_info)
                )
            conn.commit()
            logger.info(
                f"Reference section saved: [{section_type}] {title} "
                f"({len(content)}字, {'updated' if existing else 'new'})"
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to save reference section: {e}")
            return False

    def search_reference_sections(self, section_type="", query="",
                                  top_k=2, company=""):
        # type: (str, str, int, str) -> List[Dict]
        """Search reference sections by type and optional query.

        Returns top_k most relevant sections, preferring same company.
        """
        conn = self._get_conn()
        try:
            c = conn.cursor()
            if section_type:
                c.execute(
                    "SELECT id, company, section_type, title, content, "
                    "score_info, created_at FROM reference_sections "
                    "WHERE section_type = ? ORDER BY created_at DESC LIMIT ?",
                    (section_type, top_k * 3)
                )
            else:
                c.execute(
                    "SELECT id, company, section_type, title, content, "
                    "score_info, created_at FROM reference_sections "
                    "ORDER BY created_at DESC LIMIT ?",
                    (top_k * 3,)
                )
            rows = c.fetchall()
            if not rows:
                return []

            results = []
            for row in rows:
                results.append({
                    "id": row[0],
                    "company": row[1],
                    "section_type": row[2],
                    "title": row[3],
                    "content": row[4],
                    "score_info": row[5],
                    "created_at": row[6],
                })

            # Prioritize same company
            if company:
                same = [r for r in results if r["company"] == company]
                other = [r for r in results if r["company"] != company]
                results = same + other

            return results[:top_k]

        except Exception as e:
            logger.warning(f"Reference section search failed: {e}")
            return []

    # ── Update / Delete Methods ──

    def update_resume(self, name: str, updates: Dict) -> bool:
        """Update a resume by name."""
        conn = self._get_conn()
        try:
            row = conn.execute("""
                SELECT id, data FROM materials
                WHERE category = 'resumes' AND name = ?
            """, (name,)).fetchone()
            if not row:
                return False
            data = json.loads(row["data"])
            data.update(updates)
            conn.execute("""
                UPDATE materials SET data = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (json.dumps(data, ensure_ascii=False), row["id"]))
            conn.commit()
            return True
        finally:
            conn.close()

    def update_project(self, project_name: str, updates: Dict) -> bool:
        """Update a project by name."""
        conn = self._get_conn()
        try:
            row = conn.execute("""
                SELECT id, data FROM materials
                WHERE category = 'projects' AND name = ?
            """, (project_name,)).fetchone()
            if not row:
                return False
            data = json.loads(row["data"])
            data.update(updates)
            conn.execute("""
                UPDATE materials SET data = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (json.dumps(data, ensure_ascii=False), row["id"]))
            conn.commit()
            return True
        finally:
            conn.close()

    def delete_material(self, category: str, name: str,
                        company: str = "") -> bool:
        """Delete a material by category and name, optionally scoped to company."""
        conn = self._get_conn()
        try:
            if company:
                cur = conn.execute("""
                    DELETE FROM materials
                    WHERE category = ? AND name = ?
                      AND company_id = (SELECT id FROM companies WHERE name = ?)
                """, (category, name, company))
            else:
                cur = conn.execute("""
                    DELETE FROM materials
                    WHERE category = ? AND name = ?
                """, (category, name))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def delete_resume(self, name: str) -> bool:
        """Delete a resume by name (legacy compat)."""
        return self.delete_material("resumes", name)

    def clear_all(self):
        """Clear all materials."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM materials")
            conn.execute("DELETE FROM narrative_chunks")
            conn.execute("DELETE FROM companies")
            conn.execute("DELETE FROM pending_uploads")
            conn.commit()
        finally:
            conn.close()
        self._narrative_vectors = None
        self._narrative_chunks = []
        logger.info("All materials cleared")

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
            existing = {r.get("name", ""): r for r in self.get_resumes()
                        if r.get("name")}
            diff["resumes"] = self._diff_items(new_resumes, existing, "name")

        # Diff projects
        new_projects = new_materials.get("projects", [])
        if new_projects:
            existing = {p.get("project_name", ""): p for p in self.get_projects()
                        if p.get("project_name")}
            diff["projects"] = self._diff_items(
                new_projects, existing, "project_name")

        # Diff qualifications
        new_quals = new_materials.get("qualifications", [])
        if new_quals:
            existing = {q.get("name", ""): q for q in self.get_qualifications()
                        if q.get("name")}
            diff["qualifications"] = self._diff_items(
                new_quals, existing, "name")

        # Narrative chunks: always "new"
        new_narratives = new_materials.get("narrative_chunks", [])
        if new_narratives:
            diff["narrative_chunks"] = [
                {"title": c.get("title", ""), "action": "new",
                 "preview": c.get("content", "")[:100]}
                for c in new_narratives
            ]

        return diff

    def _diff_items(self, new_items: List[Dict],
                    existing_map: Dict[str, Dict],
                    key_field: str) -> List[Dict]:
        """Compare new items against existing by key field (with fuzzy matching)."""
        from difflib import SequenceMatcher

        _SKIP_FIELDS = {"_source", "_extracted_at", "_source_file",
                        "_source_path", "_source_section", "_company"}

        def _find_best_match(name, candidates):
            if not name:
                return None
            if name in candidates:
                return name
            best_ratio, best_key = 0, None
            for candidate_key in candidates:
                ratio = SequenceMatcher(None, name, candidate_key).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_key = candidate_key
            if best_ratio >= 0.7:
                logger.info(
                    f"Fuzzy match: '{name}' → '{best_key}' "
                    f"(similarity={best_ratio:.2f})")
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
                results.append(
                    {"action": "new", key_field: key, "data": item})
            else:
                old = existing_map[matched_key]
                changes = {}
                for field, new_val in item.items():
                    if field in _SKIP_FIELDS:
                        continue
                    if field == "_images":
                        old_imgs = set(old.get("_images") or [])
                        new_imgs = set(new_val or [])
                        if old_imgs != new_imgs:
                            added = new_imgs - old_imgs
                            removed = old_imgs - new_imgs
                            desc_parts = []
                            if added:
                                desc_parts.append(f"{len(added)}张新增")
                            if removed:
                                desc_parts.append(f"{len(removed)}张移除")
                            old_desc = f"{len(old_imgs)}张图片"
                            new_desc = (f"{len(new_imgs)}张图片"
                                        f"({', '.join(desc_parts)})")
                            changes["_images"] = [old_desc, new_desc]
                        continue
                    old_val = old.get(field)
                    if old_val != new_val and new_val:
                        if old_val:
                            changes[field] = [
                                str(old_val)[:80], str(new_val)[:80]]
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
