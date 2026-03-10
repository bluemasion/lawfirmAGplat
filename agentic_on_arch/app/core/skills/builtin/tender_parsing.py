"""Tender document parsing skill — extract structure from .docx files."""

from typing import Any, Dict, List, Optional
from docx import Document
from docx.table import Table

from app.core.skills.base import BaseSkill
from app.utils.logger import logger


class TenderSection:
    """Represents one section extracted from the tender document."""

    def __init__(self, order: int, title: str, level: int, content: str = "",
                 section_type: str = "narrative", tables: Optional[List[Dict]] = None):
        self.order = order
        self.title = title
        self.level = level  # 1, 2, 3 = Heading depth
        self.content = content
        self.section_type = section_type  # narrative | table | form | qualification
        self.tables = tables or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order": self.order,
            "title": self.title,
            "level": self.level,
            "content": self.content,
            "section_type": self.section_type,
            "tables": self.tables,
        }


def _extract_table_data(table: Table) -> Dict[str, Any]:
    """Extract table content as a list of rows."""
    rows = []
    headers = []
    for i, row in enumerate(table.rows):
        cells = [cell.text.strip() for cell in row.cells]
        if i == 0:
            headers = cells
        rows.append(cells)
    return {"headers": headers, "rows": rows}


def _guess_section_type(title: str, content: str, has_tables: bool) -> str:
    """Heuristically guess section type based on title and content."""
    title_lower = title.lower()

    # Table / form indicators
    table_keywords = ["一览表", "清单", "明细表", "情况表", "统计表", "报价表"]
    if any(kw in title_lower for kw in table_keywords) or has_tables:
        return "table"

    # Qualification / certificate indicators
    qual_keywords = ["资质", "证书", "执业", "许可", "授权", "委托", "身份证明",
                     "声明函", "承诺函", "营业执照", "审计报告"]
    if any(kw in title_lower for kw in qual_keywords):
        return "qualification"

    # Form indicators
    form_keywords = ["投标函", "法定代表人"]
    if any(kw in title_lower for kw in form_keywords):
        return "form"

    return "narrative"


class TenderParsingSkill(BaseSkill):
    """Parse a tender .docx file and extract its structure."""

    name = "tender_parsing"
    description = "解析招标文件(.docx)，提取标题结构、正文段落和表格内容"

    async def execute(self, params: Dict[str, Any]) -> Any:
        """
        Params:
            file_path (str): Path to the .docx file

        Returns:
            Dict with:
            - raw_text (str): Full text of the document
            - sections (List[Dict]): Structured sections
            - total_sections (int): Number of sections found
        """
        file_path = params.get("file_path", "")
        if not file_path:
            raise ValueError("file_path is required")

        logger.info(f"Parsing tender document: {file_path}")

        try:
            doc = Document(file_path)
        except Exception as e:
            logger.error(f"Failed to open document: {e}")
            raise ValueError(f"无法打开文档: {str(e)}")

        sections = []  # type: List[TenderSection]
        current_order = 0
        current_title = ""
        current_level = 0
        current_content_parts = []  # type: List[str]
        current_tables = []  # type: List[Dict]
        full_text_parts = []  # type: List[str]

        def _flush_section():
            """Save the current accumulated section."""
            nonlocal current_order, current_title, current_level
            nonlocal current_content_parts, current_tables
            if current_title:
                content = "\n".join(current_content_parts).strip()
                has_tables = len(current_tables) > 0
                sec_type = _guess_section_type(current_title, content, has_tables)
                sections.append(TenderSection(
                    order=current_order,
                    title=current_title,
                    level=current_level,
                    content=content,
                    section_type=sec_type,
                    tables=current_tables,
                ))
                current_content_parts = []
                current_tables = []

        # Iterate through document body elements (paragraphs + tables)
        for element in doc.element.body:
            # Handle paragraphs
            if element.tag.endswith('}p'):
                for para in doc.paragraphs:
                    if para._element is element:
                        text = para.text.strip()
                        full_text_parts.append(text)

                        # Check if this is a heading
                        style_name = para.style.name if para.style else ""
                        is_heading = style_name.startswith("Heading")

                        # Also detect headings by formatting patterns common in Chinese docs
                        if not is_heading and text:
                            # Pattern: "一、xxx" or "（一）xxx" or "1. xxx" or "第一章 xxx"
                            import re
                            cn_heading_patterns = [
                                r'^[一二三四五六七八九十]+[、.]',      # 一、
                                r'^（[一二三四五六七八九十]+）',         # （一）
                                r'^第[一二三四五六七八九十]+[章节部分]', # 第一章
                                r'^\d+[、.\s]',                       # 1、 or 1.
                            ]
                            for pattern in cn_heading_patterns:
                                if re.match(pattern, text):
                                    is_heading = True
                                    break

                        if is_heading and text:
                            # Flush previous section
                            _flush_section()

                            # Determine level
                            if style_name.startswith("Heading"):
                                try:
                                    current_level = int(style_name.split()[-1])
                                except (ValueError, IndexError):
                                    current_level = 1
                            else:
                                current_level = 2  # Default for pattern-detected headings

                            current_order += 1
                            current_title = text
                        elif text:
                            current_content_parts.append(text)
                        break

            # Handle tables
            elif element.tag.endswith('}tbl'):
                for table in doc.tables:
                    if table._element is element:
                        table_data = _extract_table_data(table)
                        current_tables.append(table_data)
                        # Also add table text to full text
                        for row in table_data["rows"]:
                            full_text_parts.append(" | ".join(row))
                        break

        # Flush last section
        _flush_section()

        # If no headings were found, treat entire document as one section
        if not sections:
            full_text = "\n".join(full_text_parts)
            sections.append(TenderSection(
                order=1,
                title="招标文件正文",
                level=1,
                content=full_text,
                section_type="narrative",
            ))

        result = {
            "raw_text": "\n".join(full_text_parts),
            "sections": [s.to_dict() for s in sections],
            "total_sections": len(sections),
        }

        logger.info(f"Parsed tender document: {len(sections)} sections, "
                     f"{len(full_text_parts)} paragraphs")
        return result
