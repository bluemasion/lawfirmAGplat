"""DOCX assembly skill — generate formatted Word document from sections."""

import os
import re
import time
from typing import Any, Dict, List

from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml

from app.core.skills.base import BaseSkill
from app.config import settings
from app.utils.logger import logger


def _set_font(run, font_name='仿宋', east_asia='仿宋', size=None, bold=False):
    """Helper to set font name, east-asia fallback, size and bold."""
    run.font.name = font_name
    if bold:
        run.bold = True
    if size:
        run.font.size = Pt(size)
    try:
        run.element.rPr.rFonts.set(qn('w:eastAsia'), east_asia)
    except Exception:
        pass


class DocxAssemblySkill(BaseSkill):
    """Assemble generated sections into a formatted .docx file."""

    name = "docx_assembly"
    description = "将生成的各章节内容组装为格式规范的 Word 文档 (.docx)"

    async def execute(self, params: Dict[str, Any]) -> Any:
        """
        Params:
            bid_title (str): Title of the bid document / project name
            company_name (str): Bidder company name
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
        company_name = params.get("company_name", "投标人")
        sections = params.get("sections", [])
        format_rules = params.get("format_rules", {})
        output_dir = params.get("output_dir", settings.UPLOAD_DIR)

        if not sections:
            raise ValueError("No sections to assemble")

        os.makedirs(output_dir, exist_ok=True)

        doc = Document()

        # Apply document-level formatting
        self._setup_document(doc, format_rules)

        # Add title / cover page
        self._add_cover_page(doc, bid_title, company_name)

        # Add table of contents
        self._add_toc(doc)

        # Add header/footer to all sections after cover
        self._add_header_footer(doc, bid_title)

        # Add each section
        sorted_sections = sorted(sections, key=lambda s: s.get("order", 0))
        for i, section in enumerate(sorted_sections):
            self._add_section(doc, section, chapter_num=i + 1)

        # Save document
        timestamp = int(time.time())
        filename = f"bid_document_{timestamp}.docx"
        file_path = os.path.join(output_dir, filename)
        doc.save(file_path)

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

    # ─── Document setup ───────────────────────────────────────────

    def _setup_document(self, doc: Document, format_rules: Dict):
        """Configure document-level settings: margins, paper, default font."""
        section = doc.sections[0]

        # Page margins (standard Chinese document)
        section.top_margin = Cm(format_rules.get("margin_top", 2.54))
        section.bottom_margin = Cm(format_rules.get("margin_bottom", 2.54))
        section.left_margin = Cm(format_rules.get("margin_left", 3.17))
        section.right_margin = Cm(format_rules.get("margin_right", 3.17))

        # A4 paper
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)

        # Default Normal style → 仿宋 12pt (小四)
        style = doc.styles['Normal']
        font = style.font
        font.name = '仿宋'
        font.size = Pt(12)
        try:
            style.element.rPr.rFonts.set(qn('w:eastAsia'), '仿宋')
        except Exception:
            pass

        # Line spacing 1.5
        pf = style.paragraph_format
        pf.line_spacing = 1.5

        # Configure heading styles
        for level, (name, size) in enumerate([
            ('黑体', 18),   # Heading 1
            ('黑体', 15),   # Heading 2
            ('黑体', 13),   # Heading 3
        ], start=1):
            try:
                h_style = doc.styles[f'Heading {level}']
                h_font = h_style.font
                h_font.name = name
                h_font.size = Pt(size)
                h_font.bold = True
                h_font.color.rgb = RGBColor(0, 0, 0)
                h_style.element.rPr.rFonts.set(qn('w:eastAsia'), name)
                # Space before/after headings
                h_pf = h_style.paragraph_format
                h_pf.space_before = Pt(12)
                h_pf.space_after = Pt(6)
            except Exception:
                pass

    # ─── Cover page ───────────────────────────────────────────────

    def _add_cover_page(self, doc: Document, title: str, company_name: str):
        """Add a professional cover page."""
        # Top spacing
        for _ in range(4):
            p = doc.add_paragraph("")
            p.paragraph_format.space_after = Pt(0)

        # Project name (large)
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(24)
        run = p.add_run(title)
        _set_font(run, '黑体', '黑体', size=26, bold=True)

        # Document type
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(60)
        run = p.add_run("投 标 文 件")
        _set_font(run, '黑体', '黑体', size=36, bold=True)

        # Subtitle
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(36)
        run = p.add_run("（商务技术部分）")
        _set_font(run, '仿宋', '仿宋', size=18)

        # Decorative line
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("━" * 30)
        run.font.color.rgb = RGBColor(180, 180, 180)
        run.font.size = Pt(10)

        # Spacing
        for _ in range(3):
            p = doc.add_paragraph("")
            p.paragraph_format.space_after = Pt(0)

        # Info block: company, date
        info_items = [
            ("投标人", company_name),
            ("日    期", time.strftime("%Y年%m月%d日")),
        ]
        for label, value in info_items:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(8)
            run = p.add_run(f"{label}：{value}")
            _set_font(run, '仿宋', '仿宋', size=16)

        # Page break
        doc.add_page_break()

    # ─── Table of contents ────────────────────────────────────────

    def _add_toc(self, doc: Document):
        """Add a real Word auto-updating TOC field."""
        # Title
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(20)
        run = p.add_run("目    录")
        _set_font(run, '黑体', '黑体', size=18, bold=True)

        # Insert TOC field code
        p = doc.add_paragraph()
        try:
            run = p.add_run()
            fldChar_begin = parse_xml(
                '<w:fldChar {} w:fldCharType="begin"/>'.format(nsdecls('w'))
            )
            run._r.append(fldChar_begin)

            run2 = p.add_run()
            instrText = parse_xml(
                '<w:instrText {} xml:space="preserve"> TOC \\o "1-3" \\h \\z \\u </w:instrText>'.format(
                    nsdecls('w')
                )
            )
            run2._r.append(instrText)

            run3 = p.add_run()
            fldChar_separate = parse_xml(
                '<w:fldChar {} w:fldCharType="separate"/>'.format(nsdecls('w'))
            )
            run3._r.append(fldChar_separate)

            # Placeholder text shown before user updates TOC in Word
            run4 = p.add_run("请在 Word 中右键点击此处，选择「更新域」以生成目录")
            run4.italic = True
            run4.font.color.rgb = RGBColor(128, 128, 128)
            run4.font.size = Pt(10)

            run5 = p.add_run()
            fldChar_end = parse_xml(
                '<w:fldChar {} w:fldCharType="end"/>'.format(nsdecls('w'))
            )
            run5._r.append(fldChar_end)
        except Exception as e:
            logger.warning(f"Failed to add TOC field, using placeholder: {e}")
            p.text = "[目录 — 请在 Word 中更新域以生成]"

        doc.add_page_break()

    # ─── Header / Footer ─────────────────────────────────────────

    def _add_header_footer(self, doc: Document, title: str):
        """Add page header (project name) and footer (page number)."""
        # Get or create a new section (to not affect cover page)
        section = doc.sections[-1]

        # Different first page (cover has no header/footer)
        section.different_first_page_header_footer = True

        # Header
        header = section.header
        header.is_linked_to_previous = False
        hp = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
        hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = hp.add_run(title)
        _set_font(run, '仿宋', '仿宋', size=9)
        run.font.color.rgb = RGBColor(128, 128, 128)
        # Add bottom border to header paragraph
        try:
            pPr = hp._p.get_or_add_pPr()
            pBdr = parse_xml(
                '<w:pBdr {}>'
                '<w:bottom w:val="single" w:sz="4" w:space="1" w:color="999999"/>'
                '</w:pBdr>'.format(nsdecls('w'))
            )
            pPr.append(pBdr)
        except Exception:
            pass

        # Footer with page number
        footer = section.footer
        footer.is_linked_to_previous = False
        fp = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = fp.add_run("— ")
        _set_font(run, 'Times New Roman', '仿宋', size=9)
        run.font.color.rgb = RGBColor(128, 128, 128)
        # Insert page number field
        try:
            fldChar_begin = parse_xml(
                '<w:fldChar {} w:fldCharType="begin"/>'.format(nsdecls('w'))
            )
            run2 = fp.add_run()
            run2._r.append(fldChar_begin)

            instrText = parse_xml(
                '<w:instrText {} xml:space="preserve"> PAGE </w:instrText>'.format(
                    nsdecls('w')
                )
            )
            run3 = fp.add_run()
            run3._r.append(instrText)

            fldChar_separate = parse_xml(
                '<w:fldChar {} w:fldCharType="separate"/>'.format(nsdecls('w'))
            )
            run4 = fp.add_run()
            run4._r.append(fldChar_separate)

            run5 = fp.add_run("1")  # placeholder page num
            _set_font(run5, 'Times New Roman', '仿宋', size=9)

            fldChar_end = parse_xml(
                '<w:fldChar {} w:fldCharType="end"/>'.format(nsdecls('w'))
            )
            run6 = fp.add_run()
            run6._r.append(fldChar_end)

            run7 = fp.add_run(" —")
            _set_font(run7, 'Times New Roman', '仿宋', size=9)
            run7.font.color.rgb = RGBColor(128, 128, 128)
        except Exception as e:
            logger.warning(f"Failed to add page number field: {e}")
            fp.add_run("- 页码 -")

    # ─── Section / Chapter ────────────────────────────────────────

    def _add_section(self, doc: Document, section: Dict, chapter_num: int = 1):
        """Add a single section as a chapter with heading + content."""
        title = section.get("title", "")
        content = section.get("content", "")

        # Chapter heading (Heading 1 with number)
        heading_text = f"第{self._to_chinese_num(chapter_num)}章  {title}"
        heading = doc.add_heading(heading_text, level=1)
        # Override heading font
        for run in heading.runs:
            _set_font(run, '黑体', '黑体', size=18, bold=True)

        # Parse and add content
        if content:
            self._add_markdown_content(doc, content)

    @staticmethod
    def _to_chinese_num(n):
        """Convert number to Chinese: 1→一, 2→二, etc."""
        nums = '零一二三四五六七八九十'
        if n <= 10:
            return nums[n]
        elif n < 20:
            return f'十{nums[n - 10]}' if n > 10 else '十'
        elif n < 100:
            tens = n // 10
            ones = n % 10
            return f'{nums[tens]}十{nums[ones]}' if ones else f'{nums[tens]}十'
        return str(n)

    # ─── Markdown content parser ──────────────────────────────────

    def _add_markdown_content(self, doc: Document, content: str):
        """Parse Markdown content and add formatted paragraphs to document."""
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
                if all(c in "-| :" for c in stripped):
                    continue
                cells = [c.strip() for c in stripped.split("|") if c.strip()]
                if cells:
                    table_rows.append(cells)
                    in_table = True
                continue

            # Flush pending table
            if in_table and table_rows:
                self._add_table(doc, table_rows)
                table_rows = []
                in_table = False

            # Sub-headings within section
            if stripped.startswith("### "):
                h = doc.add_heading(stripped[4:], level=3)
                for run in h.runs:
                    _set_font(run, '黑体', '黑体', size=13, bold=True)
            elif stripped.startswith("## "):
                h = doc.add_heading(stripped[3:], level=2)
                for run in h.runs:
                    _set_font(run, '黑体', '黑体', size=15, bold=True)
            elif stripped.startswith("# "):
                h = doc.add_heading(stripped[2:], level=1)
                for run in h.runs:
                    _set_font(run, '黑体', '黑体', size=18, bold=True)
            # Blockquote
            elif stripped.startswith("> "):
                para = doc.add_paragraph()
                para.style = 'List Bullet'
                run = para.add_run(stripped[2:])
                run.italic = True
                _set_font(run, '仿宋', '仿宋', size=12)
            # Checklist items
            elif stripped.startswith("- [ ] "):
                doc.add_paragraph("☐ " + stripped[6:], style='List Bullet')
            elif stripped.startswith("- [x] "):
                doc.add_paragraph("☑ " + stripped[6:], style='List Bullet')
            # Bullet list
            elif stripped.startswith("- "):
                para = doc.add_paragraph(style='List Bullet')
                self._add_styled_text(para, stripped[2:])
            # Numbered list
            elif len(stripped) > 2 and stripped[0].isdigit() and stripped[1] in ".、":
                para = doc.add_paragraph(style='List Number')
                self._add_styled_text(para, stripped)
            # Regular paragraph
            else:
                para = doc.add_paragraph()
                self._add_styled_text(para, stripped)
                para.paragraph_format.first_line_indent = Cm(0.74)  # 2 char indent

        # Flush remaining table
        if in_table and table_rows:
            self._add_table(doc, table_rows)

    def _add_styled_text(self, para, text: str):
        """Add text with Markdown bold and placeholder styling."""
        parts = re.split(r'(\*\*[^*]+\*\*|\[待补充[：:][^\]]+\])', text)
        for part in parts:
            if not part:
                continue
            if part.startswith("**") and part.endswith("**"):
                run = para.add_run(part[2:-2])
                _set_font(run, '仿宋', '仿宋', size=12, bold=True)
            elif part.startswith("[待补充"):
                run = para.add_run(part)
                _set_font(run, '仿宋', '仿宋', size=12, bold=True)
                run.font.color.rgb = RGBColor(255, 0, 0)
            else:
                run = para.add_run(part)
                _set_font(run, '仿宋', '仿宋', size=12)

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
                    cell.text = ""
                    p = cell.paragraphs[0]
                    run = p.add_run(cell_text)
                    _set_font(run, '仿宋', '仿宋', size=10.5)

                    # Bold + gray bg for header row
                    if i == 0:
                        run.bold = True
                        try:
                            shading = parse_xml(
                                '<w:shd {} w:fill="F2F2F2" w:val="clear"/>'.format(
                                    nsdecls('w')
                                )
                            )
                            cell._tc.get_or_add_tcPr().append(shading)
                        except Exception:
                            pass

        doc.add_paragraph("")  # spacing after table
