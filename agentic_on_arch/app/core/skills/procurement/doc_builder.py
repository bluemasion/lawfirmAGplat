"""DocBuilder — 采购文件 Word 组装器。

将结构化的模板数据组装为正式的 Word 采购文件。
基于现有 docx_assembly 的排版经验，针对采购文件格式定制。
"""

import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# 输出目录
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
OUTPUT_DIR = os.path.join(_DATA_DIR, "procurement", "documents")


class DocBuilder:
    """采购文件 Word 组装器。

    输入: TemplateEngine.fill_template() 的输出
    输出: 格式化的 .docx 文件
    """

    def __init__(self):
        self.output_dir = OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    def build(self, document: Dict[str, Any], output_name: str = None) -> str:
        """组装采购文件 Word。

        Args:
            document: fill_template() 的结构化输出
            output_name: 输出文件名(不含扩展名)

        Returns:
            生成的文件路径
        """
        try:
            from docx import Document
            from docx.shared import Pt, Cm, Inches, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from docx.enum.table import WD_TABLE_ALIGNMENT
            from docx.enum.section import WD_ORIENT
        except ImportError:
            raise RuntimeError("python-docx is required: pip install python-docx")

        doc = Document()
        metadata = document.get("metadata", {})
        parameters = document.get("parameters", {})
        chapters = document.get("chapters", [])
        scoring = document.get("scoring_criteria", {})
        eval_template = document.get("eval_template", {})

        # --- 页面设置 ---
        section = doc.sections[0]
        section.page_width = Cm(21)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(3.17)
        section.right_margin = Cm(3.17)

        # --- 封面 ---
        self._add_cover(doc, metadata, parameters)

        # --- 目录占位 ---
        doc.add_page_break()
        toc_heading = doc.add_paragraph("目  录")
        toc_heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        self._set_run_font(toc_heading.runs[0], "黑体", 18, bold=True)
        doc.add_paragraph("")  # 目录内容由Word自动生成
        doc.add_paragraph("（请在Word中右键→更新域→更新整个目录）")

        # --- 各章节 ---
        for chapter in chapters:
            doc.add_page_break()
            ch_title = chapter.get("title", "")
            ch_content = chapter.get("content", "")

            # 章标题
            heading = doc.add_heading(ch_title, level=1)
            for run in heading.runs:
                self._set_run_font(run, "黑体", 16, bold=True)

            # 章内容
            if ch_content:
                self._add_content(doc, ch_content)

            # 第三章特殊处理: 评分标准表格
            if chapter.get("id") == "ch3" and scoring:
                self._add_scoring_tables(doc, scoring, eval_template)

        # --- 须知前附表 (插入到第二章后) ---
        # 已在 ch2 content 里生成文本，这里额外加表格形式
        # (可在后续迭代中优化为表格)

        # --- 保存 ---
        if not output_name:
            project_name = metadata.get("project_name", "采购文件")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"{project_name}_{timestamp}"

        # 清理文件名中的非法字符
        safe_name = "".join(c for c in output_name if c.isalnum() or c in "._-（）() 中文")
        if not safe_name:
            safe_name = f"procurement_{uuid.uuid4().hex[:8]}"

        output_path = os.path.join(self.output_dir, f"{safe_name}.docx")
        doc.save(output_path)
        logger.info(f"采购文件已生成: {output_path}")
        return output_path

    def _add_cover(self, doc, metadata: Dict, parameters: Dict):
        """添加封面"""
        from docx.shared import Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        # 空行
        for _ in range(4):
            doc.add_paragraph("")

        # 标题
        purchaser = metadata.get("purchaser_name", parameters.get("purchaser_name", ""))
        project_name = metadata.get("project_name", parameters.get("project_name", ""))
        project_code = metadata.get("project_code", parameters.get("project_code", ""))

        title1 = doc.add_paragraph(purchaser)
        title1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if title1.runs:
            self._set_run_font(title1.runs[0], "方正小标宋简体", 26, bold=True)

        doc.add_paragraph("")

        title2 = doc.add_paragraph(project_name)
        title2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if title2.runs:
            self._set_run_font(title2.runs[0], "方正小标宋简体", 22, bold=True)

        doc.add_paragraph("")

        subtitle = doc.add_paragraph("招  标  文  件")
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if subtitle.runs:
            self._set_run_font(subtitle.runs[0], "黑体", 36, bold=True)

        # 空行
        for _ in range(4):
            doc.add_paragraph("")

        # 项目编号
        code_para = doc.add_paragraph(f"项目编号：{project_code}")
        code_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if code_para.runs:
            self._set_run_font(code_para.runs[0], "仿宋", 14)

        # 日期
        date_str = datetime.now().strftime("%Y年%m月")
        date_para = doc.add_paragraph(date_str)
        date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if date_para.runs:
            self._set_run_font(date_para.runs[0], "仿宋", 14)

    def _add_content(self, doc, content: str):
        """添加文本内容"""
        from docx.shared import Pt

        lines = content.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                doc.add_paragraph("")
                continue

            para = doc.add_paragraph(line)
            for run in para.runs:
                self._set_run_font(run, "仿宋", 12)

    def _add_scoring_tables(self, doc, scoring: Dict, eval_template: Dict):
        """添加评分标准表格"""
        from docx.shared import Pt, Cm
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        # 评分构成
        dist = scoring.get("score_distribution", {})
        if dist:
            doc.add_paragraph("")
            heading = doc.add_paragraph("评分构成（总分100分）")
            for run in heading.runs:
                self._set_run_font(run, "黑体", 14, bold=True)

            table = doc.add_table(rows=1, cols=3)
            table.style = "Table Grid"
            # Header
            for i, label in enumerate(["评分类别", "分值", "说明"]):
                cell = table.rows[0].cells[i]
                cell.text = label
                for run in cell.paragraphs[0].runs:
                    self._set_run_font(run, "黑体", 11, bold=True)

            label_map = {"commercial": "商务评分", "technical": "技术评分", "price": "价格评分"}
            for key, score in dist.items():
                row = table.add_row()
                row.cells[0].text = label_map.get(key, key)
                row.cells[1].text = str(score)
                row.cells[2].text = ""

        # 商务评分项
        commercial_items = scoring.get("commercial_items", [])
        # Resolve string IDs to full objects if needed
        if commercial_items and isinstance(commercial_items[0], str):
            commercial_items = self._resolve_items(commercial_items)
        if commercial_items:
            doc.add_paragraph("")
            heading = doc.add_paragraph("商务评分标准")
            for run in heading.runs:
                self._set_run_font(run, "黑体", 14, bold=True)

            table = doc.add_table(rows=1, cols=4)
            table.style = "Table Grid"
            for i, label in enumerate(["序号", "评分项", "分值", "评分标准"]):
                cell = table.rows[0].cells[i]
                cell.text = label
                for run in cell.paragraphs[0].runs:
                    self._set_run_font(run, "黑体", 11, bold=True)

            for idx, item in enumerate(commercial_items, 1):
                if not isinstance(item, dict):
                    continue
                row = table.add_row()
                row.cells[0].text = str(idx)
                row.cells[1].text = item.get("name", "")
                row.cells[2].text = str(item.get("default_score", ""))
                row.cells[3].text = item.get("scoring_guide", item.get("description", ""))

        # 技术评分项
        technical_items = scoring.get("technical_items", [])
        # Resolve string IDs to full objects if needed
        if technical_items and isinstance(technical_items[0], str):
            technical_items = self._resolve_items(technical_items)
        if technical_items:
            doc.add_paragraph("")
            heading = doc.add_paragraph("技术评分标准")
            for run in heading.runs:
                self._set_run_font(run, "黑体", 14, bold=True)

            table = doc.add_table(rows=1, cols=4)
            table.style = "Table Grid"
            for i, label in enumerate(["序号", "评分项", "分值", "评分标准"]):
                cell = table.rows[0].cells[i]
                cell.text = label
                for run in cell.paragraphs[0].runs:
                    self._set_run_font(run, "黑体", 11, bold=True)

            for idx, item in enumerate(technical_items, 1):
                if not isinstance(item, dict):
                    continue
                row = table.add_row()
                row.cells[0].text = str(idx)
                row.cells[1].text = item.get("name", "")
                row.cells[2].text = str(item.get("default_score", ""))
                row.cells[3].text = item.get("scoring_guide", item.get("description", ""))

        # 价格评分公式
        price_formula = scoring.get("price_formula", {})
        # Resolve string ID to full formula dict if needed
        if isinstance(price_formula, str) and price_formula:
            try:
                from app.core.skills.procurement.scoring_template import PRICE_FORMULA_TEMPLATES
                price_formula = PRICE_FORMULA_TEMPLATES.get(price_formula, {})
            except Exception:
                price_formula = {}
        if price_formula and isinstance(price_formula, dict):
            doc.add_paragraph("")
            heading = doc.add_paragraph("价格评分方法")
            for run in heading.runs:
                self._set_run_font(run, "黑体", 14, bold=True)

            for key in ["name", "description", "formula", "deviation_formula", "scoring_rule"]:
                val = price_formula.get(key, "")
                if val:
                    para = doc.add_paragraph(val)
                    for run in para.runs:
                        self._set_run_font(run, "仿宋", 12)

    @staticmethod
    def _resolve_items(item_ids):
        """Resolve string IDs to full scoring item dicts."""
        try:
            from app.core.skills.procurement.scoring_template import (
                COMMERCIAL_SCORING_ITEMS, TECHNICAL_SCORING_ITEMS,
            )
            all_items = {item["id"]: item for items in [COMMERCIAL_SCORING_ITEMS, TECHNICAL_SCORING_ITEMS] for item in items}
            return [all_items[i] for i in item_ids if i in all_items]
        except Exception:
            return []

    def _set_run_font(self, run, font_name: str, size: int, bold: bool = False):
        """设置run的字体"""
        from docx.shared import Pt
        run.font.name = font_name
        run.font.size = Pt(size)
        run.font.bold = bold
        # 中文字体
        run._element.rPr.rFonts.set(
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia",
            font_name
        )
