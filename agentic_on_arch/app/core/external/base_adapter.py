"""ExternalDataAdapter — 外部数据源统一接口基类 + 查询缓存。

所有外部数据适配器（天眼查/信用中国等）继承此基类。
提供统一的查询接口、缓存机制、重试策略。
"""

import json
import logging
import sqlite3
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# 缓存数据库路径
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
CACHE_DB_PATH = os.path.join(_DATA_DIR, "external_cache", "external_cache.db")


@dataclass
class CompanyProfile:
    """企业基本信息"""
    name: str
    unified_credit_code: str = ""       # 统一社会信用代码
    legal_representative: str = ""      # 法定代表人
    registered_capital: str = ""        # 注册资本
    established_date: str = ""          # 成立日期
    business_status: str = ""           # 经营状态
    registered_address: str = ""        # 注册地址
    business_scope: str = ""            # 经营范围
    company_type: str = ""              # 企业类型
    social_security_count: int = 0      # 参保人数
    shareholders: List[Dict] = None     # 股东信息

    def __post_init__(self):
        if self.shareholders is None:
            self.shareholders = []


@dataclass
class CreditRecord:
    """信用记录"""
    record_type: str = ""    # dishonest(失信)/penalty(处罚)/abnormal(异常)
    title: str = ""
    detail: str = ""
    date: str = ""
    source: str = ""
    severity: str = "INFO"   # INFO/WARNING/CRITICAL


@dataclass
class CreditReport:
    """企业信用报告"""
    company_name: str
    has_dishonest: bool = False         # 是否有失信记录
    has_penalty: bool = False           # 是否有行政处罚
    has_abnormal: bool = False          # 是否经营异常
    records: List[CreditRecord] = None
    risk_level: str = "LOW"             # LOW/MEDIUM/HIGH

    def __post_init__(self):
        if self.records is None:
            self.records = []


class ExternalDataAdapter(ABC):
    """外部数据源适配器基类。

    所有外部数据源实现类必须继承此基类并实现以下方法。
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """数据源名称 (如 'tianyancha', 'credit_china')"""
        ...

    @abstractmethod
    async def query_company(self, company_name: str) -> Optional[CompanyProfile]:
        """查询企业基本信息"""
        ...

    @abstractmethod
    async def check_credit(self, company_name: str) -> Optional[CreditReport]:
        """查询企业信用状况"""
        ...

    async def check_shareholders_overlap(
        self, company_names: List[str]
    ) -> List[Dict[str, Any]]:
        """检查多家企业的股东/法人交叉（围标检测用）。

        Returns:
            交叉关系列表 [{company_a, company_b, overlap_type, detail}, ...]
        """
        # 默认实现：逐个查询后做交叉比对
        profiles = {}
        for name in company_names:
            profile = await self.query_company(name)
            if profile:
                profiles[name] = profile

        overlaps = []
        names = list(profiles.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = profiles[names[i]], profiles[names[j]]

                # 法人代表相同
                if a.legal_representative and a.legal_representative == b.legal_representative:
                    overlaps.append({
                        "company_a": names[i],
                        "company_b": names[j],
                        "overlap_type": "SAME_LEGAL_REP",
                        "detail": f"相同法定代表人: {a.legal_representative}",
                        "severity": "HIGH",
                    })

                # 注册地址相同
                if a.registered_address and a.registered_address == b.registered_address:
                    overlaps.append({
                        "company_a": names[i],
                        "company_b": names[j],
                        "overlap_type": "SAME_ADDRESS",
                        "detail": f"相同注册地址: {a.registered_address}",
                        "severity": "MEDIUM",
                    })

                # 股东交叉
                shareholders_a = {s.get("name") for s in a.shareholders if s.get("name")}
                shareholders_b = {s.get("name") for s in b.shareholders if s.get("name")}
                common = shareholders_a & shareholders_b
                if common:
                    overlaps.append({
                        "company_a": names[i],
                        "company_b": names[j],
                        "overlap_type": "SHARED_SHAREHOLDERS",
                        "detail": f"共同股东: {', '.join(common)}",
                        "severity": "HIGH",
                    })

        return overlaps


class ExternalQueryCache:
    """外部数据查询缓存 (SQLite)。

    默认缓存7天，避免重复查询浪费API调用次数。
    """

    def __init__(self, db_path: str = None, ttl_days: int = 7):
        self.db_path = db_path or CACHE_DB_PATH
        self.ttl_days = ttl_days
        self._ensure_db()

    def _ensure_db(self):
        """创建缓存数据库和表"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS external_queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    query_type TEXT NOT NULL,
                    result TEXT,
                    expires_at TEXT,
                    queried_at TEXT DEFAULT (datetime('now')),
                    UNIQUE(source, company_name, query_type)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_lookup
                ON external_queries(source, company_name, query_type)
            """)

    def get(self, source: str, company_name: str, query_type: str) -> Optional[Dict]:
        """获取缓存结果 (未过期的)"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """SELECT result, expires_at FROM external_queries
                   WHERE source=? AND company_name=? AND query_type=?""",
                (source, company_name, query_type)
            ).fetchone()

            if row and row[0]:
                expires = datetime.fromisoformat(row[1]) if row[1] else None
                if expires and datetime.now() < expires:
                    return json.loads(row[0])
                # 已过期，删除
                conn.execute(
                    """DELETE FROM external_queries
                       WHERE source=? AND company_name=? AND query_type=?""",
                    (source, company_name, query_type)
                )
        return None

    def set(self, source: str, company_name: str, query_type: str, result: Dict):
        """设置缓存结果"""
        expires_at = (datetime.now() + timedelta(days=self.ttl_days)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO external_queries
                   (source, company_name, query_type, result, expires_at, queried_at)
                   VALUES (?, ?, ?, ?, ?, datetime('now'))""",
                (source, company_name, query_type, json.dumps(result, ensure_ascii=False), expires_at)
            )
