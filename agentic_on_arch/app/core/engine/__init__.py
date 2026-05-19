"""共享引擎层 — 包装现有投标系统的通用能力，供采购方和投标方共用。

不移动、不修改现有代码，只做 import 包装 + 统一接口。
"""

from app.core.engine.document_parser import DocumentParser
from app.core.engine.scoring_extractor import ScoringExtractor
from app.core.engine.doc_assembler import DocAssembler
from app.core.engine.compliance_checker import ComplianceChecker

__all__ = [
    "DocumentParser",
    "ScoringExtractor",
    "DocAssembler",
    "ComplianceChecker",
]
