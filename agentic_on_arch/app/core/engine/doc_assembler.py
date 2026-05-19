"""DocAssembler — 文档组装引擎包装层。

包装现有的 docx_assembly，提供统一接口。
- 投标方: 组装投标文件 Word
- 采购方: 组装采购文件 Word / 评审报告 Word
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DocAssembler:
    """统一的文档组装接口。

    包装现有模块:
    - docx_assembly.py: Word文档组装
    """

    def __init__(self):
        self._assembler = None

    def _get_assembler(self):
        """延迟加载 docx_assembly 模块"""
        if self._assembler is None:
            try:
                from app.core.skills.builtin import docx_assembly
                self._assembler = docx_assembly
            except ImportError:
                logger.warning("docx_assembly module not available")
        return self._assembler

    async def assemble_procurement_document(
        self,
        template_content: Dict[str, Any],
        parameters: Dict[str, Any],
        output_path: str,
    ) -> str:
        """组装采购文件 Word 文档。

        Args:
            template_content: 模板结构 (章节+条款)
            parameters: 须知前附表参数
            output_path: 输出路径

        Returns:
            生成的文件路径
        """
        # Phase 1 实现具体逻辑
        raise NotImplementedError("Phase 1: 采购文件组装待实现")

    async def assemble_review_report(
        self,
        review_data: Dict[str, Any],
        output_path: str,
    ) -> str:
        """组装评审报告 Word 文档。

        Args:
            review_data: 评审汇总数据 (评分/排名/专家意见)
            output_path: 输出路径

        Returns:
            生成的文件路径
        """
        # Phase 3 实现具体逻辑
        raise NotImplementedError("Phase 3: 评审报告组装待实现")
