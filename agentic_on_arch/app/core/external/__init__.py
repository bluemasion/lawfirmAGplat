"""外部数据适配层 — 统一接口对接天眼查/信用中国等外部数据源。"""

from app.core.external.base_adapter import ExternalDataAdapter, ExternalQueryCache

__all__ = ["ExternalDataAdapter", "ExternalQueryCache"]
