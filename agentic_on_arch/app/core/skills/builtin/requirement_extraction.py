"""Requirement extraction skill — use LLM to structure tender requirements."""

import json
from typing import Any, Dict, List

from app.core.skills.base import BaseSkill
from app.core.llm import get_llm
from app.utils.logger import logger


# System prompt for requirement extraction
EXTRACTION_SYSTEM_PROMPT = """你是招标文件分析专家。你的任务是从招标文件中精确提取投标要求的结构化信息。

你必须输出严格的 JSON 格式，不要包含任何其他内容。"""

# User prompt template for extracting structure from tender text
EXTRACTION_PROMPT_TEMPLATE = """请分析以下招标文件内容，提取投标文件需要包含的所有章节和要求。

【招标文件内容】
{tender_text}

请输出以下 JSON 结构：
{{
  "bid_title": "投标文件的标题",
  "volumes": [
    {{
      "name": "分册名称（如：报价分册、商务分册、技术分册）",
      "sections": [
        {{
          "order": 1,
          "title": "章节标题",
          "type": "narrative|table|form|qualification",
          "required": true,
          "content_hints": "该章节应包含的内容摘要",
          "data_fields": ["需要填写的数据字段名"],
          "source_reference": "对应招标文件的哪一条要求"
        }}
      ]
    }}
  ],
  "qualification_requirements": [
    "资质要求1",
    "资质要求2"
  ],
  "format_requirements": {{
    "font_body": "正文字体要求",
    "font_title": "标题字体要求",
    "font_size": "字号要求",
    "paper_size": "纸张大小",
    "binding": "装订要求",
    "copies": "份数要求",
    "other": "其他格式要求"
  }},
  "evaluation_criteria": [
    {{
      "item": "评分项名称",
      "max_score": 0,
      "description": "简要说明"
    }}
  ],
  "deadline_info": {{
    "submission_deadline": "投标截止时间",
    "opening_time": "开标时间",
    "validity_period": "投标有效期"
  }}
}}

注意：
1. sections 中的 order 必须严格按照招标文件要求的顺序
2. 如果招标文件没有明确分册，就放在一个默认分册里
3. type 只能是 narrative/table/form/qualification 四选一
4. required 字段：招标文件明确要求的设为 true
5. 所有字段都要尽量填写，实在找不到的写 null

请严格输出 JSON，不要有任何额外说明文字。"""


# For long documents, we split and extract per-section
SECTION_EXTRACTION_PROMPT = """请分析以下招标文件的某个章节，提取该章节中对投标文件的具体要求。

【章节标题】
{section_title}

【章节内容】
{section_content}

请提取该章节中提到的所有投标要求，输出 JSON 列表：
[
  {{
    "title": "投标文件中对应的章节标题",
    "type": "narrative|table|form|qualification",
    "required": true,
    "content_hints": "应包含的内容",
    "data_fields": ["需要填写的字段"]
  }}
]

只输出 JSON，不要额外文字。"""


def _safe_parse_json(text: str) -> Any:
    """Try to parse JSON from LLM output, handling common issues."""
    text = text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (``` markers)
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object or array in the text
        import re
        # Look for outermost { } or [ ]
        for pattern in [r'\{[\s\S]*\}', r'\[[\s\S]*\]']:
            match = re.search(pattern, text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    continue
        logger.error(f"Failed to parse JSON from LLM output: {text[:200]}...")
        return None


class RequirementExtractionSkill(BaseSkill):
    """Extract structured requirements from tender document using LLM."""

    name = "requirement_extraction"
    description = "使用LLM从招标文件中提取结构化的投标要求（章节、资质、格式等）"

    # Max characters to send in a single LLM call
    MAX_CHUNK_SIZE = 12000

    async def execute(self, params: Dict[str, Any]) -> Any:
        """
        Params:
            raw_text (str): Full text of the tender document
            sections (List[Dict]): Parsed sections from tender_parsing
            llm_provider (str, optional): Which LLM to use (default: "qwen")

        Returns:
            Dict: Structured tender requirements JSON
        """
        raw_text = params.get("raw_text", "")
        sections = params.get("sections", [])
        llm_provider = params.get("llm_provider", "qwen")

        if not raw_text and not sections:
            raise ValueError("Either raw_text or sections must be provided")

        llm = get_llm(llm_provider)
        logger.info(f"Extracting requirements using {llm.get_model_name()}")

        # Strategy: if text is short enough, send all at once.
        # Otherwise, split by sections and merge.
        text_length = len(raw_text)

        if text_length <= self.MAX_CHUNK_SIZE:
            # Single-pass extraction
            result = await self._extract_full(llm, raw_text)
        else:
            # Multi-pass: extract per-section, then merge
            result = await self._extract_by_sections(llm, sections, raw_text)

        if result is None:
            # Fallback: create structure from parsed sections
            result = self._fallback_from_sections(sections)

        logger.info(f"Extraction complete: {len(result.get('volumes', []))} volumes, "
                     f"{sum(len(v.get('sections', [])) for v in result.get('volumes', []))} sections")
        return result

    async def _extract_full(self, llm, raw_text: str) -> Any:
        """Single-pass extraction for shorter documents."""
        prompt = EXTRACTION_PROMPT_TEMPLATE.format(tender_text=raw_text)
        response = await llm.generate(prompt, system=EXTRACTION_SYSTEM_PROMPT)
        return _safe_parse_json(response)

    async def _extract_by_sections(self, llm, sections: List[Dict],
                                    raw_text: str) -> Dict:
        """Multi-pass extraction for long documents."""
        all_requirements = []  # type: List[Dict]

        for section in sections:
            title = section.get("title", "")
            content = section.get("content", "")

            if not content or len(content) < 20:
                continue

            # Truncate very long sections
            if len(content) > self.MAX_CHUNK_SIZE:
                content = content[:self.MAX_CHUNK_SIZE] + "\n...(内容过长已截断)"

            prompt = SECTION_EXTRACTION_PROMPT.format(
                section_title=title,
                section_content=content,
            )
            response = await llm.generate(prompt, system=EXTRACTION_SYSTEM_PROMPT)
            parsed = _safe_parse_json(response)

            if parsed and isinstance(parsed, list):
                all_requirements.extend(parsed)
            elif parsed and isinstance(parsed, dict):
                all_requirements.append(parsed)

        # Now do a final consolidation pass with extracted requirements
        # Build a summary and ask LLM to organize into the full structure
        if all_requirements:
            return await self._consolidate(llm, all_requirements, raw_text)
        return self._fallback_from_sections(sections)

    async def _consolidate(self, llm, requirements: List[Dict],
                           raw_text: str) -> Dict:
        """Consolidate per-section extractions into final structure."""
        req_summary = json.dumps(requirements, ensure_ascii=False, indent=2)
        if len(req_summary) > self.MAX_CHUNK_SIZE:
            req_summary = req_summary[:self.MAX_CHUNK_SIZE]

        prompt = f"""以下是从招标文件各章节中分别提取的投标要求：

{req_summary}

请将这些要求整合为一份完整的投标文件结构，输出 JSON 格式：
{{
  "bid_title": "投标文件",
  "volumes": [
    {{
      "name": "分册名称",
      "sections": [
        {{"order": 1, "title": "章节标题", "type": "narrative|table|form|qualification",
          "required": true, "content_hints": "内容摘要", "data_fields": []}}
      ]
    }}
  ],
  "qualification_requirements": [],
  "format_requirements": {{}},
  "evaluation_criteria": [],
  "deadline_info": {{}}
}}

注意确保：
1. 章节不重复
2. 顺序合理（资质→报价→商务→技术 是典型顺序）
3. 只输出 JSON"""

        response = await llm.generate(prompt, system=EXTRACTION_SYSTEM_PROMPT)
        result = _safe_parse_json(response)
        return result if result else self._fallback_from_sections([])

    def _fallback_from_sections(self, sections: List[Dict]) -> Dict:
        """Create a basic structure from parsed sections when LLM fails."""
        logger.warning("Using fallback structure from parsed sections")
        bid_sections = []
        for i, sec in enumerate(sections):
            bid_sections.append({
                "order": i + 1,
                "title": sec.get("title", f"第{i+1}节"),
                "type": sec.get("section_type", "narrative"),
                "required": True,
                "content_hints": sec.get("content", "")[:100],
                "data_fields": [],
            })

        return {
            "bid_title": "投标文件",
            "volumes": [{"name": "投标文件", "sections": bid_sections}],
            "qualification_requirements": [],
            "format_requirements": {},
            "evaluation_criteria": [],
            "deadline_info": {},
        }
