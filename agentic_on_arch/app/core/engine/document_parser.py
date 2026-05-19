"""DocumentParser — 文档解析引擎包装层。

包装现有的 tender_parsing + bid_document_parser，提供统一接口。
采购方和投标方共用。
"""

import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class DocumentParser:
    """统一的文档解析接口。

    包装现有模块:
    - tender_parsing.py: 招标文件结构解析
    - bid_document_parser.py: 投标/响应文件解析
    """

    def __init__(self):
        self._tender_parser = None
        self._bid_parser = None

    def _get_tender_parser(self):
        """延迟加载 tender_parsing 模块"""
        if self._tender_parser is None:
            try:
                from app.core.skills.builtin import tender_parsing
                self._tender_parser = tender_parsing
            except ImportError:
                logger.warning("tender_parsing module not available")
        return self._tender_parser

    def _get_bid_parser(self):
        """延迟加载 bid_document_parser 模块"""
        if self._bid_parser is None:
            try:
                from app.core.skills.builtin import bid_document_parser
                self._bid_parser = bid_document_parser
            except ImportError:
                logger.warning("bid_document_parser module not available")
        return self._bid_parser

    async def parse_tender_document(self, file_path: str) -> Dict[str, Any]:
        """解析招标/采购文件结构。

        Returns:
            解析后的结构化数据 (章节树、元数据等)
        """
        parser = self._get_tender_parser()
        if parser and hasattr(parser, "parse_tender_file"):
            return await parser.parse_tender_file(file_path)
        raise NotImplementedError("tender_parsing.parse_tender_file not available")

    async def parse_response_document(self, file_path: str) -> Dict[str, Any]:
        """解析投标/响应文件。

        Returns:
            解析后的结构化数据 (章节、表格、资质信息等)
        """
        parser = self._get_bid_parser()
        if parser and hasattr(parser, "parse_bid_document"):
            return await parser.parse_bid_document(file_path)
        raise NotImplementedError("bid_document_parser.parse_bid_document not available")

    def extract_document_metadata(self, file_path: str) -> Dict[str, Any]:
        """提取文档元数据 (作者/创建时间/修改人等)。

        用于围标检测的文档指纹层。
        """
        try:
            from docx import Document
            doc = Document(file_path)
            props = doc.core_properties
            return {
                "author": props.author,
                "last_modified_by": props.last_modified_by,
                "created": str(props.created) if props.created else None,
                "modified": str(props.modified) if props.modified else None,
                "title": props.title,
                "subject": props.subject,
                "keywords": props.keywords,
                "revision": props.revision,
            }
        except Exception as e:
            logger.error(f"Failed to extract metadata from {file_path}: {e}")
            return {}
