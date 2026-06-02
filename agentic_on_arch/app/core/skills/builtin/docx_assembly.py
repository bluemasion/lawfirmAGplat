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


def _set_font(run, font_name='宋体', east_asia='宋体', size=None, bold=False):
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
        format_spec = params.get("format_spec", {})
        output_dir = params.get("output_dir", settings.UPLOAD_DIR)

        if not sections:
            raise ValueError("No sections to assemble")

        os.makedirs(output_dir, exist_ok=True)

        # ── Store format_spec for use across methods ──
        self._format_spec = format_spec
        # Derive effective fonts from format_spec or defaults
        if format_spec.get('has_format_chapter'):
            fs = format_spec.get('font', {})
            self._body_font = fs.get('name', '宋体')
            self._body_size = fs.get('size', 12)
            self._title_font = fs.get('name', '黑体')  # titles use same font in tender-specified mode
            self._title_size = fs.get('title_size', 15)
            tfs = format_spec.get('table_font', {})
            self._table_font = tfs.get('name', '宋体')
            self._table_size = tfs.get('size', 10.5)
            self._section_numbering = format_spec.get('section_numbering', '章')
            logger.info(
                f"Format spec active: font={self._body_font}/{self._body_size}pt, "
                f"table={self._table_font}/{self._table_size}pt, "
                f"numbering={self._section_numbering}"
            )
        else:
            self._body_font = '宋体'
            self._body_size = 12
            self._title_font = '黑体'
            self._title_size = 16
            self._table_font = '宋体'
            self._table_size = 10.5
            self._section_numbering = '章'

        # ── Global dedup state: track images used across chapters ──
        # Maps image_path → chapter_title (first chapter that used it)
        self._used_images = {}  # type: Dict[str, str]
        self._current_chapter = ""  # set per-chapter in _add_section
        self._dedup_stats = {"total_images": 0, "deduped": 0}

        # ── Build section→table template mapping from format_spec ──
        # Maps section_title → list of table XML paths
        self._table_templates = {}  # type: Dict[str, List[Dict]]
        # Maps section_title → tender attachment ID (e.g. '附件4')
        self._attachment_ids = {}  # type: Dict[str, str]
        if format_spec.get('has_format_chapter'):
            self._build_table_template_map(format_spec, sections)

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
            # Page break before each chapter (except the first one,
            # which already starts on a new page after TOC)
            if i > 0:
                doc.add_page_break()
            # Use att_id from section (SectionPlanner) or from mapping
            title = section.get('title', '')
            att_id = section.get('att_id', '') or \
                self._attachment_ids.get(title, '')
            self._add_section(doc, section, att_id=att_id, chapter_num=i + 1)

        if self._dedup_stats["deduped"] > 0:
            logger.info(
                f"Image dedup: {self._dedup_stats['deduped']} duplicates removed "
                f"out of {self._dedup_stats['total_images']} total images"
            )

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
            "dedup_stats": self._dedup_stats,
        }

    # ─── Document setup ───────────────────────────────────────────

    def _setup_document(self, doc: Document, format_rules: Dict):
        """Configure document-level settings: margins, paper, default font.
        Uses self._body_font/size from format_spec if available."""
        section = doc.sections[0]

        # Page margins (standard Chinese document)
        section.top_margin = Cm(format_rules.get("margin_top", 2.54))
        section.bottom_margin = Cm(format_rules.get("margin_bottom", 2.54))
        section.left_margin = Cm(format_rules.get("margin_left", 3.17))
        section.right_margin = Cm(format_rules.get("margin_right", 3.17))

        # A4 paper
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)

        # Default Normal style — use format_spec font
        body_font = self._body_font
        body_size = self._body_size
        style = doc.styles['Normal']
        font = style.font
        font.name = body_font
        font.size = Pt(body_size)
        try:
            style.element.rPr.rFonts.set(qn('w:eastAsia'), body_font)
        except Exception:
            pass

        # Line spacing 1.5
        pf = style.paragraph_format
        pf.line_spacing = 1.5

        # Configure heading styles — use title_font from format_spec
        title_font = self._title_font
        h_sizes = [self._title_size, self._title_size - 1, self._title_size - 2]
        for level, size in enumerate(h_sizes, start=1):
            try:
                h_style = doc.styles[f'Heading {level}']
                h_font = h_style.font
                h_font.name = title_font
                h_font.size = Pt(size)
                h_font.bold = True
                h_font.color.rgb = RGBColor(0, 0, 0)
                h_style.element.rPr.rFonts.set(qn('w:eastAsia'), title_font)
                # Space before/after headings
                h_pf = h_style.paragraph_format
                h_pf.space_before = Pt(12)
                h_pf.space_after = Pt(6)
            except Exception:
                pass

    # ─── Cover page ───────────────────────────────────────────────

    def _add_cover_page(self, doc: Document, title: str, company_name: str):
        """Add a professional cover page."""
        bf = self._body_font
        # Top spacing
        for _ in range(4):
            p = doc.add_paragraph("")
            p.paragraph_format.space_after = Pt(0)

        # Project name (large)
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(24)
        run = p.add_run(title)
        # Use tender font for cover if format_spec active, else 方正小标宋
        cover_font = bf if self._format_spec.get('has_format_chapter') else '方正小标宋简体'
        _set_font(run, cover_font, cover_font, size=26, bold=True)

        # Document type
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(60)
        run = p.add_run("投 标 文 件")
        _set_font(run, cover_font, cover_font, size=36, bold=True)

        # Subtitle
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(36)
        run = p.add_run("（商务技术部分）")
        _set_font(run, bf, bf, size=18)

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
            _set_font(run, bf, bf, size=16)

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

        # Add section break (new page) to start a new Word section
        # This separates cover+TOC from content, allowing independent
        # header/footer control
        new_section = doc.add_section(WD_ORIENT.PORTRAIT)
        new_section.page_width = Cm(21.0)
        new_section.page_height = Cm(29.7)
        new_section.top_margin = Cm(2.54)
        new_section.bottom_margin = Cm(2.54)
        new_section.left_margin = Cm(3.17)
        new_section.right_margin = Cm(3.17)

    # ─── Header / Footer ─────────────────────────────────────────

    def _add_header_footer(self, doc: Document, title: str):
        """Add page header (project name) and footer (page number).
        
        Applies to the content section (after cover+TOC).
        The cover+TOC section (sections[0]) has no header/footer.
        """
        # Content section is the last section (after TOC section break)
        content_section = doc.sections[-1]
        
        # Ensure cover section has no header/footer
        cover_section = doc.sections[0]
        cover_section.different_first_page_header_footer = False
        # Clear any header/footer on cover section
        if cover_section.header.paragraphs:
            for p in cover_section.header.paragraphs:
                p.clear()
        if cover_section.footer.paragraphs:
            for p in cover_section.footer.paragraphs:
                p.clear()

        # --- Content section header ---
        content_section.different_first_page_header_footer = False
        header = content_section.header
        header.is_linked_to_previous = False
        hp = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
        hp.text = ""  # Clear default
        hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = hp.add_run(title)
        _set_font(run, self._body_font, self._body_font, size=9)
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

        # --- Content section footer with page number ---
        footer = content_section.footer
        footer.is_linked_to_previous = False
        fp = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        fp.text = ""  # Clear default
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = fp.add_run("— ")
        _set_font(run, 'Times New Roman', self._body_font, size=9)
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
            _set_font(run7, 'Times New Roman', self._body_font, size=9)
            run7.font.color.rgb = RGBColor(128, 128, 128)
        except Exception as e:
            logger.warning(f"Failed to add page number field: {e}")
            fp.add_run("- 页码 -")

        # --- Restart page numbering from 1 in content section ---
        try:
            sectPr = content_section._sectPr
            pgNumType = parse_xml(
                '<w:pgNumType {} w:start="1"/>'.format(nsdecls('w'))
            )
            sectPr.append(pgNumType)
        except Exception as e:
            logger.warning(f"Failed to restart page numbering: {e}")

    # ─── Table Template Cloning ───────────────────────────────────

    def _build_table_template_map(self, format_spec, sections):
        """Build mapping from bid section titles to tender table templates.

        Uses keyword matching between our section titles and tender
        attachment titles to find which tables belong to which section.
        """
        attachments = format_spec.get('attachments', [])
        section_titles = [s.get('title', '') for s in sections]

        logger.info(
            f"  Building table template map: "
            f"{len(attachments)} attachments, {len(section_titles)} sections"
        )
        atts_with_tables = [a for a in attachments if a.get('tables')]
        logger.info(
            f"  Attachments with tables: {len(atts_with_tables)}: "
            + ", ".join(f"{a['id']}({len(a['tables'])})" for a in atts_with_tables)
        )

        # Keyword map: tender attachment title keyword → our section title keywords
        _keyword_map = {
            '评标索引表':       ['评标索引', '索引表'],
            '投标函':           ['投标函'],
            '投标一览表':       ['投标一览', '一览表', '报价一览'],
            '商务条款响应':     ['商务偏离', '商务评分偏离', '商务条款'],
            '技术条款响应':     ['技术偏离', '技术评分偏离', '技术条款'],
            '业绩清单':         ['业绩清单', '律所业绩', '项目业绩', '业绩'],
            '授权书':           ['授权委托', '授权书'],
            '投标保证金':       ['投标保证金', '保证金'],
            '投标人情况表':     ['投标人情况', '项目团队', '团队配置'],
            '拟派实施人员':     ['拟派实施', '实施人员'],
            '拟派人员资历':     ['人员资历', '资历表'],
            '招标代理服务费':   ['代理服务费', '承诺书'],
            '服务响应方案':     ['服务响应', '详细的服务'],
        }

        # Map ALL attachments to sections (not just ones with tables)
        for att in attachments:
            att_title = att.get('title', '')
            att_id = att.get('id', '')
            att_tables = att.get('tables', [])

            matched = False
            for kw_group, section_kws in _keyword_map.items():
                if kw_group in att_title:
                    # Found the attachment type — find our section
                    for sec_title in section_titles:
                        if sec_title in self._attachment_ids:
                            continue  # already mapped
                        for skw in section_kws:
                            if skw in sec_title:
                                # Map attachment ID
                                self._attachment_ids[sec_title] = att_id
                                # Map table templates if any
                                if att_tables:
                                    self._table_templates[sec_title] = att_tables
                                    logger.info(
                                        f"  Table template mapped: "
                                        f"'{sec_title}' ← {att_id} "
                                        f"({len(att_tables)} tables)"
                                    )
                                else:
                                    logger.info(
                                        f"  Section mapped: "
                                        f"'{sec_title}' ← {att_id}"
                                    )
                                matched = True
                                break
                        if matched:
                            break
                    break

            if not matched:
                # Try direct title match
                for sec_title in section_titles:
                    if sec_title in self._attachment_ids:
                        continue
                    if att_title in sec_title or sec_title in att_title:
                        self._attachment_ids[sec_title] = att_id
                        if att_tables:
                            self._table_templates[sec_title] = att_tables
                        logger.info(
                            f"  Mapped (direct): '{sec_title}' ← {att_id}"
                        )
                        matched = True
                        break

        logger.info(
            f"Template mapping: {len(self._attachment_ids)} sections mapped to attachments, "
            f"{len(self._table_templates)} have table templates"
        )

    def _insert_cloned_table(self, doc, table_info):
        """Insert a cloned table from XML template into the document.

        Args:
            doc: The Document object
            table_info: Dict with 'xml_path', 'headers', 'cols', 'rows'
        """
        import os
        from lxml import etree
        from copy import deepcopy

        xml_path = table_info.get('xml_path', '')
        if not xml_path or not os.path.exists(xml_path):
            logger.warning(f"Table template XML not found: {xml_path}")
            return False

        try:
            with open(xml_path, 'r', encoding='utf-8') as f:
                xml_str = f.read()

            # Parse the XML
            tbl_element = etree.fromstring(xml_str)

            # Deep copy to avoid mutation
            new_tbl = deepcopy(tbl_element)

            # Insert after the last element in the document body
            # (which should be the heading paragraph just added)
            # Use add_paragraph + addnext pattern to ensure correct position
            spacer = doc.add_paragraph("")
            spacer._element.addnext(new_tbl)

            # Add spacing paragraph after table
            doc.add_paragraph("")

            logger.info(
                f"  Cloned table inserted: "
                f"{table_info.get('rows', '?')}x{table_info.get('cols', '?')} "
                f"from {os.path.basename(xml_path)}"
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to clone table from {xml_path}: {e}")
            return False

    # ─── Section / Chapter ────────────────────────────────────────

    def _add_section(self, doc: Document, section: Dict,
                     att_id: str = '', chapter_num: int = 1):
        """Add a single section as a chapter with heading + content."""
        title = section.get("title", "")
        content = section.get("content", "")

        # Track current chapter for cross-reference in dedup
        self._current_chapter = title

        tf = self._title_font or 'Arial'

        # Chapter heading — match tender Chapter 6 format exactly
        if att_id:
            # ── Tender attachment format ──
            # Line 1: "附件N：标题" — Arial/12pt, not bold, left-aligned
            att_title_p = doc.add_paragraph()
            att_title_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run1 = att_title_p.add_run(f"{att_id}：{title}")
            _set_font(run1, tf, tf, size=12, bold=False)

            # Line 2: "标题" subtitle — Arial/15pt, centered
            subtitle_p = doc.add_paragraph()
            subtitle_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run2 = subtitle_p.add_run(title)
            _set_font(run2, tf, tf, size=15, bold=False)
        elif self._section_numbering == '附件':
            # Unmapped section — just title as heading
            heading = doc.add_heading(title, level=1)
            heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in heading.runs:
                _set_font(run, tf, tf, size=self._title_size, bold=True)
        else:
            heading_text = f"第{self._to_chinese_num(chapter_num)}章  {title}"
            heading = doc.add_heading(heading_text, level=1)
            heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in heading.runs:
                _set_font(run, tf, tf, size=self._title_size, bold=True)

        # ── Check for cloned table templates ──
        has_cloned_tables = False
        if title in self._table_templates:
            table_templates = self._table_templates[title]
            for tpl in table_templates:
                if self._insert_cloned_table(doc, tpl):
                    has_cloned_tables = True

        # Parse and add content (skip LLM tables if we already cloned tender tables)
        if content:
            # Strip leading headings that duplicate the chapter title
            cleaned = content.strip()
            # Remove leading ## or # title lines that match section title
            for prefix in ['## ', '# ']:
                if cleaned.startswith(prefix):
                    first_line_end = cleaned.find('\n')
                    if first_line_end == -1:
                        # Content is just the heading, skip entirely
                        cleaned = ""
                    else:
                        first_line = cleaned[:first_line_end].strip()
                        heading_text_in_content = first_line[len(prefix):].strip()
                        # Only strip if the heading matches the section title
                        if (heading_text_in_content == title or
                                title in heading_text_in_content or
                                heading_text_in_content in title):
                            cleaned = cleaned[first_line_end + 1:].strip()
                    break
            if cleaned:
                if has_cloned_tables:
                    # Strip markdown tables from LLM content — we already have tender tables
                    cleaned = self._strip_markdown_tables(cleaned)
                if cleaned.strip():
                    self._add_markdown_content(doc, cleaned)

    @staticmethod
    def _strip_markdown_tables(content):
        """Remove markdown table blocks from content.

        Preserves non-table text (paragraphs, headings, lists, images).
        """
        lines = content.split('\n')
        result = []
        in_table = False
        for line in lines:
            stripped = line.strip()
            # Detect table row: starts/ends with | or is a separator
            if '|' in stripped and not stripped.startswith('!['):
                if all(c in '-| :' for c in stripped):
                    in_table = True
                    continue
                cells = [c.strip() for c in stripped.split('|') if c.strip()]
                if len(cells) >= 2:
                    in_table = True
                    continue
            if in_table and not stripped:
                in_table = False
                continue
            if not in_table:
                result.append(line)
        return '\n'.join(result)

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

            # Image embedding: ![caption](path)
            if stripped.startswith("!["):
                img_match = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', stripped)
                if img_match:
                    caption, img_path = img_match.groups()
                    # Resolve relative paths from project root
                    if not os.path.isabs(img_path):
                        project_root = os.path.join(
                            os.path.dirname(__file__),
                            "..", "..", "..", ".."
                        )
                        img_path = os.path.normpath(
                            os.path.join(project_root, img_path)
                        )

                    self._dedup_stats["total_images"] += 1

                    # ── Cross-chapter image dedup ──
                    norm_path = os.path.normpath(img_path)
                    if norm_path in self._used_images:
                        first_chapter = self._used_images[norm_path]
                        if first_chapter != self._current_chapter:
                            # Skip duplicate — add cross-reference instead
                            self._dedup_stats["deduped"] += 1
                            para = doc.add_paragraph()
                            ref_text = (
                                f"（{caption or '相关证明'}"
                                f"详见\u201c{first_chapter}\u201d章节）"
                            )
                            run = para.add_run(ref_text)
                            _set_font(run, self._body_font, self._body_font, size=10.5)
                            run.italic = True
                            run.font.color.rgb = RGBColor(100, 100, 100)
                            continue

                    if os.path.exists(img_path):
                        try:
                            doc.add_picture(img_path, width=Cm(14))
                            # Register this image as used by current chapter
                            self._used_images[norm_path] = self._current_chapter
                            # Add centered caption
                            if caption:
                                cap_para = doc.add_paragraph()
                                cap_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                cap_run = cap_para.add_run(caption)
                                _set_font(cap_run, self._body_font, self._body_font,
                                          size=10.5)
                                cap_run.font.color.rgb = RGBColor(
                                    100, 100, 100
                                )
                            logger.debug(f"Embedded image: {caption or img_path}")
                        except Exception as e:
                            # Fallback: show as text placeholder
                            para = doc.add_paragraph()
                            run = para.add_run(
                                f"[图片：{caption or '未命名'}]"
                            )
                            _set_font(run, self._body_font, self._body_font, size=self._body_size)
                            run.font.color.rgb = RGBColor(200, 0, 0)
                            logger.warning(
                                f"Failed to embed image {img_path}: {e}"
                            )
                    else:
                        para = doc.add_paragraph()
                        run = para.add_run(
                            f"[图片缺失：{caption or img_path}]"
                        )
                        _set_font(run, self._body_font, self._body_font, size=self._body_size)
                        run.font.color.rgb = RGBColor(200, 0, 0)
                    continue

            # Sub-headings within section
            if stripped.startswith("### "):
                h = doc.add_heading(stripped[4:], level=3)
                for run in h.runs:
                    _set_font(run, self._title_font, self._title_font, size=self._title_size - 2, bold=True)
            elif stripped.startswith("## "):
                h = doc.add_heading(stripped[3:], level=2)
                for run in h.runs:
                    _set_font(run, self._title_font, self._title_font, size=self._title_size - 1, bold=True)
            elif stripped.startswith("# "):
                h = doc.add_heading(stripped[2:], level=1)
                for run in h.runs:
                    _set_font(run, self._title_font, self._title_font, size=self._title_size, bold=True)
            # Blockquote
            elif stripped.startswith("> "):
                para = doc.add_paragraph()
                para.style = 'List Bullet'
                run = para.add_run(stripped[2:])
                run.italic = True
                _set_font(run, self._body_font, self._body_font, size=self._body_size)
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
        bf = self._body_font
        bs = self._body_size
        parts = re.split(r'(\*\*[^*]+\*\*|\[待补充[：:][^\]]+\])', text)
        for part in parts:
            if not part:
                continue
            if part.startswith("**") and part.endswith("**"):
                run = para.add_run(part[2:-2])
                _set_font(run, bf, bf, size=bs, bold=True)
            elif part.startswith("[待补充"):
                run = para.add_run(part)
                _set_font(run, bf, bf, size=bs, bold=True)
                run.font.color.rgb = RGBColor(255, 0, 0)
            else:
                run = para.add_run(part)
                _set_font(run, bf, bf, size=bs)

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
                    _set_font(run, self._table_font, self._table_font, size=self._table_size)

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
