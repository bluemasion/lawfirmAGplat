"""Historical bid document parser — extract materials from past bid documents.

Parse historical bid documents (.docx) to automatically extract:
- Team member resumes (name, title, specialty, years, cases)
- Project history (name, client, amount, period, description)
- Qualifications (name, number, valid_until)
- Narrative chunks (for RAG vector store)
"""

import json
import re
from typing import Any, Dict, List, Optional

from docx import Document

from app.core.skills.base import BaseSkill
from app.core.llm import get_llm
from app.utils.logger import logger


# ── LLM Prompts ──

MATERIAL_CLASSIFY_SYSTEM = """你是法律投标文件分析专家。你的任务是识别投标文件中各章节包含的素材类型。
你必须输出严格的 JSON 格式，不要包含任何其他内容。"""

MATERIAL_CLASSIFY_PROMPT = """以下是一份历史投标文件中的章节列表。
请为每个章节标注它包含什么类型的素材：

类型说明：
- resume: 包含人员简历、团队介绍、律师信息
- project: 包含项目业绩、案例、成功经验
- qualification: 包含资质证书、营业执照、执业证
- narrative: 包含方案、说明、承诺等叙述性内容
- form: 包含表单、函件（投标函、声明函等）
- other: 其他类型（目录、封面等，不需要提取）

【章节列表】
{section_list}

请输出 JSON 数组：
[
  {{"order": 1, "title": "原始标题", "material_type": "resume|project|qualification|narrative|form|other"}}
]

只输出 JSON，不要额外文字。"""

EXTRACT_RESUMES_SYSTEM = """你是专业的人力资源文档分析师。从投标文件中精确提取人员信息。
你必须输出严格的 JSON 格式。只提取文档中明确提到的信息，不要编造。"""

EXTRACT_RESUMES_PROMPT = """请从以下投标文件章节中提取所有人员简历信息。

【章节内容】
{content}

请提取每位人员的以下信息（没有的字段写 null）：
[
  {{
    "name": "姓名",
    "title": "职称/职位（如：高级合伙人、资深律师）",
    "license_number": "执业证号",
    "specialty": "专业领域",
    "education": "学历",
    "years_of_practice": "执业年限（数字）",
    "role_in_project": "在本项目中的角色（如：项目负责人、主办律师）",
    "representative_cases": ["代表案例1", "代表案例2"],
    "brief_bio": "简要介绍（1-2句话概括核心经历）"
  }}
]

注意：
- 只提取文档中明确提到的人员
- 如果是表格形式的简历，按表格行提取
- 代表案例尽量完整记录
- 只输出 JSON 数组"""

EXTRACT_PROJECTS_SYSTEM = """你是专业的项目业绩文档分析师。从投标文件中精确提取项目信息。
你必须输出严格的 JSON 格式。只提取文档中明确提到的信息，不要编造。"""

EXTRACT_PROJECTS_PROMPT = """请从以下投标文件章节中提取所有项目业绩信息。

【章节内容】
{content}

请提取每个项目的以下信息（没有的字段写 null）：
[
  {{
    "project_name": "项目名称",
    "client": "委托方/甲方名称",
    "project_type": "项目类型（如：法律顾问、诉讼代理、合规咨询）",
    "amount": "合同金额",
    "period": "服务期间",
    "description": "项目简要描述",
    "outcome": "项目成果/结果"
  }}
]

注意：
- 只提取文档中明确提到的项目
- 金额保留原文格式
- 只输出 JSON 数组"""

EXTRACT_QUALIFICATIONS_SYSTEM = """你是专业的资质文档分析师。从投标文件中精确提取资质信息。
你必须输出严格的 JSON 格式。只提取文档中明确提到的信息，不要编造。"""

EXTRACT_QUALIFICATIONS_PROMPT = """请从以下投标文件章节中提取所有资质/证书信息。

【章节内容】
{content}

请提取每个资质的以下信息（没有的字段写 null）：
[
  {{
    "name": "资质/证书名称",
    "number": "证书编号",
    "issuer": "颁发机构",
    "valid_from": "生效日期",
    "valid_until": "有效期至",
    "holder": "持有人/单位名称"
  }}
]

只输出 JSON 数组"""


def _safe_parse_json(text: str) -> Any:
    """Parse JSON from LLM output, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        for pattern in [r'\[\s*\{[\s\S]*\}\s*\]', r'\{[\s\S]*\}']:
            match = re.search(pattern, text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    continue
        logger.error(f"Failed to parse JSON: {text[:200]}...")
        return None


class BidDocumentParserSkill(BaseSkill):
    """Parse historical bid documents to extract reusable materials."""

    name = "bid_document_parser"
    description = "从历史投标文件中提取简历、业绩、资质等可复用素材"

    MAX_CHUNK_SIZE = 6000  # Max chars per LLM call

    async def execute(self, params: Dict[str, Any]) -> Any:
        """
        Params:
            file_path (str): Path to historical bid document (.docx)
            llm_provider (str): LLM to use (default: "qwen")

        Returns:
            Dict with extracted materials:
            - resumes: List[Dict]
            - projects: List[Dict]
            - qualifications: List[Dict]
            - narrative_chunks: List[Dict] (title + content for RAG)
            - source_file: str
            - total_sections: int
        """
        file_path = params.get("file_path", "")
        llm_provider = params.get("llm_provider", "qwen")

        if not file_path:
            raise ValueError("file_path is required")

        logger.info(f"Parsing historical bid document: {file_path}")

        # Step 1: Parse document structure (reuse tender_parsing logic)
        sections = self._parse_docx(file_path)
        logger.info(f"Parsed {len(sections)} sections from bid document")

        # Step 2: Classify sections by material type
        llm = get_llm(llm_provider)
        classified = await self._classify_sections(llm, sections)

        # Step 2.5: Filename-based heuristic override
        # If file name strongly hints at a type but LLM missed it, force-classify
        import os
        filename = os.path.basename(file_path)
        filename_type = self._detect_type_from_filename(filename)
        if filename_type:
            typed_sections = [s for s in classified
                             if s.get("material_type") == filename_type]
            if not typed_sections:
                logger.info(f"Filename '{filename}' suggests type '{filename_type}' "
                            f"but LLM found 0 such sections. Forcing classification.")
                for sec in classified:
                    if sec.get("material_type") in ("narrative", "other"):
                        sec["material_type"] = filename_type

        # Step 3: Extract materials by type
        resumes = []      # type: List[Dict]
        projects = []     # type: List[Dict]
        qualifications = []  # type: List[Dict]
        narrative_chunks = []  # type: List[Dict]

        for sec in classified:
            material_type = sec.get("material_type", "other")
            title = sec.get("title", "")
            content = sec.get("content", "")

            if not content.strip():
                continue

            if material_type == "resume":
                extracted = await self._extract_resumes(llm, title, content)
                resumes.extend(extracted)
                logger.info(f"  Extracted {len(extracted)} resumes from '{title}'")

            elif material_type == "project":
                extracted = await self._extract_projects(llm, title, content)
                projects.extend(extracted)
                logger.info(f"  Extracted {len(extracted)} projects from '{title}'")

            elif material_type == "qualification":
                extracted = await self._extract_qualifications(llm, title, content)
                qualifications.extend(extracted)
                logger.info(f"  Extracted {len(extracted)} qualifications from '{title}'")

            elif material_type == "narrative":
                # Keep narrative chunks for RAG vectorization
                chunks = self._split_narrative(title, content)
                narrative_chunks.extend(chunks)

        logger.info(f"Extraction complete: {len(resumes)} resumes, "
                     f"{len(projects)} projects, {len(qualifications)} qualifications, "
                     f"{len(narrative_chunks)} narrative chunks")

        return {
            "resumes": resumes,
            "projects": projects,
            "qualifications": qualifications,
            "narrative_chunks": narrative_chunks,
            "source_file": file_path,
            "total_sections": len(sections),
        }

    def _parse_docx(self, file_path: str) -> List[Dict]:
        """Parse .docx file into sections (simplified version of tender_parsing)."""
        try:
            doc = Document(file_path)
        except Exception as e:
            raise ValueError(f"无法打开文档: {str(e)}")

        sections = []
        current_title = ""
        current_content_parts = []  # type: List[str]
        current_tables = []  # type: List[str]

        cn_heading_patterns = [
            r'^[一二三四五六七八九十]+[、.]',
            r'^（[一二三四五六七八九十]+）',
            r'^第[一二三四五六七八九十]+[章节部分]',
            r'^\d+[、.\s]',
        ]

        def _flush():
            nonlocal current_title, current_content_parts, current_tables
            if current_title:
                content = "\n".join(current_content_parts + current_tables).strip()
                sections.append({
                    "title": current_title,
                    "content": content,
                })
                current_content_parts = []
                current_tables = []

        for element in doc.element.body:
            if element.tag.endswith('}p'):
                for para in doc.paragraphs:
                    if para._element is element:
                        text = para.text.strip()
                        if not text:
                            break

                        style_name = para.style.name if para.style else ""
                        is_heading = style_name.startswith("Heading")

                        if not is_heading:
                            for pattern in cn_heading_patterns:
                                if re.match(pattern, text) and len(text) <= 60:
                                    is_heading = True
                                    break

                        if is_heading:
                            _flush()
                            current_title = text
                        else:
                            current_content_parts.append(text)
                        break

            elif element.tag.endswith('}tbl'):
                for table in doc.tables:
                    if table._element is element:
                        rows_text = []
                        for row in table.rows:
                            cells = [cell.text.strip() for cell in row.cells]
                            rows_text.append(" | ".join(cells))
                        current_tables.append("\n".join(rows_text))
                        break

        _flush()

        # If no sections found, treat whole document as one section
        # Include BOTH paragraph text AND table content
        if not sections:
            parts = []
            for p in doc.paragraphs:
                if p.text.strip():
                    parts.append(p.text.strip())
            for table in doc.tables:
                rows_text = []
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    rows_text.append(" | ".join(cells))
                parts.append("\n".join(rows_text))
            full_text = "\n".join(parts)
            title = "投标文件正文"
            # Use first non-empty paragraph or table row as title if available
            if parts:
                first_line = parts[0].split("\n")[0][:60]
                if first_line:
                    title = first_line
            sections.append({"title": title, "content": full_text})

        return sections

    async def _classify_sections(self, llm, sections: List[Dict]) -> List[Dict]:
        """Use LLM to classify each section's material type."""
        section_lines = []
        for i, sec in enumerate(sections, 1):
            title = sec.get("title", f"第{i}节")
            section_lines.append(f"{i}. {title}")

        prompt = MATERIAL_CLASSIFY_PROMPT.format(
            section_list="\n".join(section_lines)
        )

        try:
            response = await llm.generate(prompt, system=MATERIAL_CLASSIFY_SYSTEM)
            classifications = _safe_parse_json(response)
        except Exception as e:
            logger.error(f"LLM section classification failed: {e}")
            classifications = None

        # Build lookup map
        type_map = {}  # type: Dict[str, str]
        if classifications and isinstance(classifications, list):
            for item in classifications:
                title = item.get("title", "")
                if title:
                    type_map[title] = item.get("material_type", "other")
            logger.info(f"Classified {len(type_map)}/{len(sections)} sections")

        # Merge classification into sections
        result = []
        for sec in sections:
            title = sec.get("title", "")
            sec["material_type"] = type_map.get(title, self._guess_material_type(title))
            result.append(sec)

        # Log distribution
        dist = {}  # type: Dict[str, int]
        for sec in result:
            t = sec.get("material_type", "other")
            dist[t] = dist.get(t, 0) + 1
        logger.info(f"Material type distribution: {dist}")

        return result

    def _guess_material_type(self, title: str) -> str:
        """Heuristic fallback for section type classification."""
        resume_kw = ["简历", "团队", "人员", "律师", "项目负责人", "主办"]
        project_kw = ["业绩", "案例", "经验", "项目", "成功"]
        qual_kw = ["资质", "执照", "证书", "执业", "许可", "证明"]
        form_kw = ["投标函", "声明", "承诺", "授权"]

        for kw in resume_kw:
            if kw in title:
                return "resume"
        for kw in project_kw:
            if kw in title:
                return "project"
        for kw in qual_kw:
            if kw in title:
                return "qualification"
        for kw in form_kw:
            if kw in title:
                return "form"
        return "narrative"

    @staticmethod
    def detect_document_type(filename: str, content_preview: str = "") -> dict:
        """Detect document type using filename + content preview (rule-based).

        Returns:
            {"doc_type": str, "material_hint": str|None, "confidence": float, "reason": str}

        doc_type values:
            - "tender"         招标文件
            - "bid_document"   完整投标文件 (含多类素材)
            - "material"       单项素材 (简历/业绩/资质)
            - "unknown"        未知

        material_hint: "resume" | "project" | "qualification" | None
        """
        fn = filename.lower()
        cp = content_preview[:800] if content_preview else ""

        # ── Layer 1: 招标文件 ──
        tender_fn_kw = ["招标", "磋商", "询价", "采购文件", "竞争性"]
        tender_content_kw = ["投标人须知", "评标办法", "投标截止", "开标时间",
                             "招标公告", "采购需求", "供应商资格"]
        if any(k in fn for k in tender_fn_kw):
            return {"doc_type": "tender", "material_hint": None,
                    "confidence": 0.95, "reason": f"文件名含招标关键词"}
        if any(k in cp for k in tender_content_kw):
            return {"doc_type": "tender", "material_hint": None,
                    "confidence": 0.90, "reason": f"内容含招标关键词"}

        # ── Layer 2: 完整投标文件 ──
        bid_fn_kw = ["投标文件", "投标书", "投标函", "响应文件", "响应书"]
        bid_content_kw = ["投标函", "法定代表人授权", "拟投入本项目",
                          "项目负责人简历", "4.4.1", "4.4.2",
                          "投标报价", "服务方案", "投标人基本情况"]
        if any(k in fn for k in bid_fn_kw):
            return {"doc_type": "bid_document", "material_hint": None,
                    "confidence": 0.95, "reason": f"文件名含投标关键词"}
        # 内容中出现2个以上投标关键词 → 大概率是完整投标文件
        bid_hits = sum(1 for k in bid_content_kw if k in cp)
        if bid_hits >= 2:
            return {"doc_type": "bid_document", "material_hint": None,
                    "confidence": 0.85, "reason": f"内容含{bid_hits}个投标关键词"}

        # ── Layer 3: 单项素材 ──
        resume_kw = ["简历", "人员", "律师", "团队", "个人", "履历"]
        project_kw = ["业绩", "案例", "项目经验", "代表项目", "服务案例"]
        qual_kw = ["资质", "证书", "执照", "荣誉", "奖项", "资格"]

        for kw in resume_kw:
            if kw in fn:
                return {"doc_type": "material", "material_hint": "resume",
                        "confidence": 0.90, "reason": f"文件名含'{kw}'"}
        for kw in project_kw:
            if kw in fn:
                return {"doc_type": "material", "material_hint": "project",
                        "confidence": 0.90, "reason": f"文件名含'{kw}'"}
        for kw in qual_kw:
            if kw in fn:
                return {"doc_type": "material", "material_hint": "qualification",
                        "confidence": 0.90, "reason": f"文件名含'{kw}'"}

        # Content-based material detection
        if "工作年限" in cp or "执业年限" in cp or "学历" in cp:
            return {"doc_type": "material", "material_hint": "resume",
                    "confidence": 0.75, "reason": "内容含简历字段"}
        if "项目名称" in cp and "委托人" in cp:
            return {"doc_type": "material", "material_hint": "project",
                    "confidence": 0.75, "reason": "内容含项目字段"}

        return {"doc_type": "unknown", "material_hint": None,
                "confidence": 0.0, "reason": "无法确定文件类型"}

    @staticmethod
    def _detect_type_from_filename(filename: str) -> Optional[str]:
        """Backward-compat wrapper for detect_document_type."""
        result = BidDocumentParserSkill.detect_document_type(filename)
        return result.get("material_hint")

    async def _extract_resumes(self, llm, title: str,
                                content: str) -> List[Dict]:
        """Extract structured resume data from a section."""
        # Truncate if too long
        if len(content) > self.MAX_CHUNK_SIZE:
            content = content[:self.MAX_CHUNK_SIZE]

        prompt = EXTRACT_RESUMES_PROMPT.format(content=content)
        try:
            response = await llm.generate(prompt, system=EXTRACT_RESUMES_SYSTEM)
            result = _safe_parse_json(response)
            if isinstance(result, list):
                # Add source info
                for item in result:
                    item["_source_section"] = title
                return result
        except Exception as e:
            logger.error(f"Resume extraction failed for '{title}': {e}")
        return []

    async def _extract_projects(self, llm, title: str,
                                 content: str) -> List[Dict]:
        """Extract structured project history from a section."""
        if len(content) > self.MAX_CHUNK_SIZE:
            content = content[:self.MAX_CHUNK_SIZE]

        prompt = EXTRACT_PROJECTS_PROMPT.format(content=content)
        try:
            response = await llm.generate(prompt, system=EXTRACT_PROJECTS_SYSTEM)
            result = _safe_parse_json(response)
            if isinstance(result, list):
                for item in result:
                    item["_source_section"] = title
                return result
        except Exception as e:
            logger.error(f"Project extraction failed for '{title}': {e}")
        return []

    async def _extract_qualifications(self, llm, title: str,
                                       content: str) -> List[Dict]:
        """Extract structured qualification data from a section."""
        if len(content) > self.MAX_CHUNK_SIZE:
            content = content[:self.MAX_CHUNK_SIZE]

        prompt = EXTRACT_QUALIFICATIONS_PROMPT.format(content=content)
        try:
            response = await llm.generate(prompt, system=EXTRACT_QUALIFICATIONS_SYSTEM)
            result = _safe_parse_json(response)
            if isinstance(result, list):
                for item in result:
                    item["_source_section"] = title
                return result
        except Exception as e:
            logger.error(f"Qualification extraction failed for '{title}': {e}")
        return []

    def _split_narrative(self, title: str, content: str,
                          max_chunk_size: int = 500) -> List[Dict]:
        """Split narrative content into chunks suitable for RAG vectorization."""
        if not content.strip():
            return []

        chunks = []
        paragraphs = [p.strip() for p in content.split("\n") if p.strip()]

        current_chunk = ""
        for para in paragraphs:
            if len(current_chunk) + len(para) + 1 > max_chunk_size and current_chunk:
                chunks.append({
                    "title": title,
                    "content": current_chunk.strip(),
                    "char_count": len(current_chunk),
                })
                current_chunk = para
            else:
                current_chunk += "\n" + para if current_chunk else para

        if current_chunk.strip():
            chunks.append({
                "title": title,
                "content": current_chunk.strip(),
                "char_count": len(current_chunk),
            })

        return chunks
