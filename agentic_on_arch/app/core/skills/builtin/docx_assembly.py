"""DOCX assembly skill — generate formatted Word document from sections."""

import os
from typing import Any, Dict, List

from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT

from app.core.skills.base import BaseSkill
from app.config import settings
from app.utils.logger import logger


class DocxAssemblySkill(BaseSkill):
    """Assemble generated sections into a formatted .docx file."""

    name = "docx_assembly"
    description = "将生成的各章节内容组装为格式规范的 Word 文档 (.docx)"

    async def execute(self, params: Dict[str, Any]) -> Any:
        """
        Params:
            bid_title (str): Title of the bid document
            sections (List[Dict]): Generated sections
                [{title, content, order, type}]
            format_rules (Dict, optional): Format requirements
            output_dir (str, optional): Output directory

        Returns:
            Dict with:
            - file_path (str): Path to generated .docx
            - page_count_estimate (int): Estimated number of pages
            - section_count (int): Number of sections assembled
        """
        bid_title = params.get("bid_title", "投标文件")
        sections = params.get("sections", [])
        format_rules = params.get("format_rules", {})
        output_dir = params.get("output_dir", settings.UPLOAD_DIR)

        if not sections:
            raise ValueError("No sections to assemble")

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        doc = Document()

        # Apply document-level formatting
        self._setup_document(doc, format_rules)

        # Add title page
        self._add_title_page(doc, bid_title)

        # Add table of contents placeholder
        self._add_toc_placeholder(doc)

        # Add each section
        for section in sorted(sections, key=lambda s: s.get("order", 0)):
            self._add_section(doc, section)

        # Save document
        import time
        timestamp = int(time.time())
        filename = f"bid_document_{timestamp}.docx"
        file_path = os.path.join(output_dir, filename)
        doc.save(file_path)

        # Estimate page count (rough: ~500 chars per page)
        total_chars = sum(len(s.get("content", "")) for s in sections)
        page_estimate = max(1, total_chars // 500)

        logger.info(f"Document assembled: {file_path} ({len(sections)} sections, "
                     f"~{page_estimate} pages)")

        return {
            "file_path": file_path,
            "filename": filename,
            "page_count_estimate": page_estimate,
            "section_count": len(sections),
        }

    def _setup_document(self, doc: Document, format_rules: Dict):
        """Configure document-level settings."""
        section = doc.sections[0]

        # Page margins (default: standard Chinese document margins)
        margin_top = format_rules.get("margin_top", 2.54)
        margin_bottom = format_rules.get("margin_bottom", 2.54)
        margin_left = format_rules.get("margin_left", 3.17)
        margin_right = format_rules.get("margin_right", 3.17)

        section.top_margin = Cm(margin_top)
        section.bottom_margin = Cm(margin_bottom)
        section.left_margin = Cm(margin_left)
        section.right_margin = Cm(margin_right)

        # Paper size: A4
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)

        # Default paragraph style
        style = doc.styles['Normal']
        font = style.font
        font.name = '宋体'
        font.size = Pt(12)  # 四号 = 14pt, but 12pt is safer for compatibility

        # Set Chinese font fallback
        try:
            from docx.oxml.ns import qn
            style.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
        except Exception:
            pass  # Font fallback is nice-to-have

    def _add_title_page(self, doc: Document, title: str):
        """Add a title page."""
        # Add some spacing before title
        for _ in range(6):
            doc.add_paragraph("")

        # Main title
        title_para = doc.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title_para.add_run(title)
        run.bold = True
        run.font.size = Pt(22)  # 二号字
        try:
            run.font.name = '黑体'
            from docx.oxml.ns import qn
            run.element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
        except Exception:
            pass

        # Subtitle line
        doc.add_paragraph("")
        subtitle = doc.add_paragraph()
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sub_run = subtitle.add_run("（商务/技术部分）")
        sub_run.font.size = Pt(16)

        # Add page break after title
        doc.add_page_break()

    def _add_toc_placeholder(self, doc: Document):
        """Add a table of contents placeholder."""
        toc_title = doc.add_paragraph()
        toc_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = toc_title.add_run("目  录")
        run.bold = True
        run.font.size = Pt(16)
        try:
            run.font.name = '黑体'
            from docx.oxml.ns import qn
            run.element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
        except Exception:
            pass

        doc.add_paragraph("")
        note = doc.add_paragraph()
        note.add_run("[目录将在最终版中自动生成]").italic = True

        doc.add_page_break()

    def _add_section(self, doc: Document, section: Dict):
        """Add a single section to the document."""
        title = section.get("title", "")
        content = section.get("content", "")
        level = section.get("level", 2)

        # Add section heading
        if level == 1:
            heading = doc.add_heading(title, level=1)
            # Style level 1 heading
            for run in heading.runs:
                run.font.size = Pt(18)
                run.bold = True
        else:
            heading = doc.add_heading(title, level=min(level, 3))

        # Parse and add content
        if content:
            self._add_markdown_content(doc, content)

        # Add spacing after section
        doc.add_paragraph("")

    def _add_markdown_content(self, doc: Document, content: str):
        """Parse simple Markdown and add to document."""
        lines = content.split("\n")
        in_table = False
        table_rows = []  # type: List[List[str]]

        for line in lines:
            stripped = line.strip()

            # Skip empty lines
            if not stripped:
                if in_table and table_rows:
                    self._add_table(doc, table_rows)
                    table_rows = []
                    in_table = False
                continue

            # Markdown table row
            if "|" in stripped and not stripped.startswith("!["):
                # Skip separator rows (---|---|---)
                if all(c in "-| " for c in stripped):
                    continue
                cells = [c.strip() for c in stripped.split("|") if c.strip()]
                if cells:
                    table_rows.append(cells)
                    in_table = True
                continue

            # Flush table if we were in one
            if in_table and table_rows:
                self._add_table(doc, table_rows)
                table_rows = []
                in_table = False

            # Headings
            if stripped.startswith("### "):
                doc.add_heading(stripped[4:], level=3)
            elif stripped.startswith("## "):
                doc.add_heading(stripped[3:], level=2)
            elif stripped.startswith("# "):
                doc.add_heading(stripped[2:], level=1)
            # Blockquote (used for warnings)
            elif stripped.startswith("> "):
                para = doc.add_paragraph()
                para.style = 'List Bullet'
                run = para.add_run(stripped[2:])
                run.italic = True
            # Checklist items
            elif stripped.startswith("- [ ] "):
                para = doc.add_paragraph(stripped[6:], style='List Bullet')
            elif stripped.startswith("- [x] "):
                para = doc.add_paragraph("✅ " + stripped[6:], style='List Bullet')
            # Bullet list
            elif stripped.startswith("- "):
                doc.add_paragraph(stripped[2:], style='List Bullet')
            # Numbered list
            elif len(stripped) > 2 and stripped[0].isdigit() and stripped[1] in ".、":
                doc.add_paragraph(stripped, style='List Number')
            # Regular paragraph
            else:
                para = doc.add_paragraph()
                # Handle bold markers
                self._add_styled_text(para, stripped)

                # First-line indent for regular paragraphs
                para.paragraph_format.first_line_indent = Cm(0.74)  # 2 characters

        # Flush remaining table
        if in_table and table_rows:
            self._add_table(doc, table_rows)

    def _add_styled_text(self, para, text: str):
        """Add text with basic Markdown bold/placeholder styling."""
        import re
        # Split by bold markers and [待补充] markers
        parts = re.split(r'(\*\*[^*]+\*\*|\[待补充[：:][^\]]+\])', text)
        for part in parts:
            if part.startswith("**") and part.endswith("**"):
                run = para.add_run(part[2:-2])
                run.bold = True
            elif part.startswith("[待补充"):
                run = para.add_run(part)
                run.font.color.rgb = RGBColor(255, 0, 0)  # Red for placeholders
                run.bold = True
            else:
                para.add_run(part)

    def _add_table(self, doc: Document, rows: List[List[str]]):
        """Add a formatted table to the document."""
        if not rows:
            return

        max_cols = max(len(r) for r in rows)
        table = doc.add_table(rows=len(rows), cols=max_cols, style='Table Grid')
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        for i, row_data in enumerate(rows):
            row = table.rows[i]
            for j, cell_text in enumerate(row_data):
                if j < max_cols:
                    cell = row.cells[j]
                    cell.text = cell_text

                    # Bold header row
                    if i == 0:
                        for para in cell.paragraphs:
                            for run in para.runs:
                                run.bold = True

        doc.add_paragraph("")  # Spacing after table
