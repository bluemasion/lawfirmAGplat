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


# ── V2: Batch classify prompt (LLM only classifies, doesn't generate structure) ──

BATCH_CLASSIFY_SYSTEM = """你是招标文件分析专家。你的任务是对招标文件的章节标题进行分类标注。
你必须输出严格的 JSON 格式，不要包含任何其他内容。"""

BATCH_CLASSIFY_PROMPT = """以下是从招标文件中提取的原始章节标题列表。
请为每个标题标注两个信息：
1. type: 投标文件中该章节应该用什么形式呈现
   - narrative: 需要撰写叙述性内容（如方案、说明、承诺等）
   - table: 需要用表格呈现（如报价表、业绩一览表、人员配置表等）
   - form: 需要用固定格式表单（如投标函、声明函、承诺书等）
   - qualification: 需要提供资质证明文件（如营业执照、执业证等）
2. content_hints: 根据招标文件上下文，该章节在投标文件中应该包含什么内容（简要描述）

【招标文件原文参考】
{tender_context}

【章节标题列表】
{section_list}

请输出 JSON 数组，格式如下：
[
  {{
    "order": 1,
    "title": "原始标题（必须与上面的标题完全一致，不要修改）",
    "type": "narrative|table|form|qualification",
    "content_hints": "该章节应包含的内容描述",
    "data_fields": ["需要填写的具体数据字段"]
  }}
]

重要：
- title 必须和输入的标题完全一致，一字不改
- 每个标题都必须有对应的输出项
- 只输出 JSON 数组，不要额外文字"""


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
            mode (str): 'structure' (V2, default) or 'legacy' (V1)

        Returns:
            Dict: Structured tender requirements JSON
        """
        raw_text = params.get("raw_text", "")
        sections = params.get("sections", [])
        llm_provider = params.get("llm_provider", "qwen")
        mode = params.get("mode", "structure")

        if not raw_text and not sections:
            raise ValueError("Either raw_text or sections must be provided")

        llm = get_llm(llm_provider)
        logger.info(f"Extracting requirements using {llm.get_model_name()}, mode={mode}")

        if mode == "structure" and sections:
            # ── V2: Use original section titles from tender_parsing ──
            # LLM only classifies types + extracts content_hints
            result = await self._structure_from_sections(llm, sections, raw_text)
        else:
            # ── V1 Legacy: LLM generates the entire structure ──
            text_length = len(raw_text)
            if text_length <= self.MAX_CHUNK_SIZE:
                result = await self._extract_full(llm, raw_text)
            else:
                result = await self._extract_by_sections(llm, sections, raw_text)

        if result is None:
            result = self._fallback_from_sections(sections)

        # Post-LLM: refine section types using local classifier (90.9% accuracy)
        result = self._refine_section_types(result)

        total_sections = sum(len(v.get('sections', [])) for v in result.get('volumes', []))
        logger.info(f"Extraction complete: {len(result.get('volumes', []))} volumes, "
                     f"{total_sections} sections (mode={mode})")
        return result

    def _filter_bid_sections(self, sections: List[Dict]) -> List[Dict]:
        """Filter tender_parsing sections to keep only bid-relevant headings.

        tender_parsing extracts ALL headings, including instructional text from
        the tender document itself (e.g. "投标人应当按照招标文件的要求编制投标文件").
        We only want actual bid document section titles.

        Filters:
        1. Title length <= 60 chars (longer = paragraph text, not heading)
        2. No duplicate titles
        3. Skip tender instruction patterns
        """
        import re

        # Patterns that indicate tender instructions (not bid sections)
        SKIP_PATTERNS = [
            r'投标人应当',
            r'投标人递交',
            r'投标人没有',
            r'招标人有权',
            r'招标人不予',
            r'投标文件应当使用不褪色',
            r'应当按照招标文件',
            r'应当认真阅读',
            r'并加盖单位公章',
        ]
        skip_regex = re.compile('|'.join(SKIP_PATTERNS))

        MAX_TITLE_LEN = 60
        seen_titles = set()  # type: set
        filtered = []

        for sec in sections:
            title = sec.get("title", "").strip()
            if not title:
                continue

            # Skip titles that are too long (paragraph text, not headings)
            if len(title) > MAX_TITLE_LEN:
                continue

            # Skip tender instruction patterns
            if skip_regex.search(title):
                continue

            # Skip duplicates
            if title in seen_titles:
                continue
            seen_titles.add(title)

            filtered.append(sec)

        logger.info(f"Section filter: {len(sections)} → {len(filtered)} "
                     f"(removed {len(sections) - len(filtered)} non-bid sections)")
        return filtered

    async def _structure_from_sections(self, llm, sections: List[Dict],
                                       raw_text: str) -> Dict:
        """V2: Build structure directly from parsed sections, LLM only classifies.

        Instead of asking LLM to generate the directory structure (which causes
        title drift), we use the exact titles from tender_parsing and only ask
        LLM to classify each section's type and extract content hints.
        """
        logger.info(f"V2 structure mode: {len(sections)} raw sections from tender_parsing")

        # Step 1: Filter to bid-relevant sections only
        sections = self._filter_bid_sections(sections)

        # Step 2: Build section list for the LLM prompt
        section_lines = []
        for i, sec in enumerate(sections, 1):
            title = sec.get("title", f"第{i}节")
            section_lines.append(f"{i}. {title}")

        section_list_text = "\n".join(section_lines)

        # Use first 8000 chars of raw text as context for classification
        tender_context = raw_text[:8000] if raw_text else "暂无原文"

        prompt = BATCH_CLASSIFY_PROMPT.format(
            tender_context=tender_context,
            section_list=section_list_text,
        )

        # Step 3: LLM batch classification
        try:
            response = await llm.generate(prompt, system=BATCH_CLASSIFY_SYSTEM)
            classifications = _safe_parse_json(response)
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            classifications = None

        # Build classification lookup: title -> {type, content_hints, data_fields}
        classify_map = {}  # type: Dict[str, Dict]
        if classifications and isinstance(classifications, list):
            for item in classifications:
                title = item.get("title", "")
                if title:
                    classify_map[title] = {
                        "type": item.get("type", "narrative"),
                        "content_hints": item.get("content_hints", ""),
                        "data_fields": item.get("data_fields", []),
                    }
            logger.info(f"LLM classified {len(classify_map)}/{len(sections)} sections")
        else:
            logger.warning("LLM classification returned no results, using heuristic types")

        # Step 4: Build final structure using original titles + LLM classifications
        bid_sections = []
        for i, sec in enumerate(sections):
            title = sec.get("title", f"第{i+1}节")
            original_type = sec.get("section_type", "narrative")
            content = sec.get("content", "")

            # Try to get LLM classification for this title
            classification = classify_map.get(title, {})

            # Use LLM type if available, otherwise use tender_parsing's heuristic
            sec_type = classification.get("type", original_type)
            hints = classification.get("content_hints", content[:100] if content else "")
            fields = classification.get("data_fields", [])

            bid_sections.append({
                "order": i + 1,
                "title": title,  # Original title, never modified
                "type": sec_type,
                "required": True,
                "content_hints": hints,
                "data_fields": fields,
            })

        return {
            "bid_title": "投标文件",
            "volumes": [{"name": "投标文件", "sections": bid_sections}],
            "qualification_requirements": [],
            "format_requirements": {},
            "evaluation_criteria": [],
            "deadline_info": {},
        }

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

    def _refine_section_types(self, result: Dict) -> Dict:
        """Use local BGE classifier to correct section types assigned by LLM.

        LLM sometimes misclassifies section types (e.g., assigns "narrative" to
        what should be "table" or "form"). The local classifier has 90.9% accuracy
        on real tender data and runs in <1ms per section.

        Only overrides LLM type when classifier confidence > 0.7.
        """
        try:
            from app.core.rag.section_classifier import section_classifier

            corrections = 0
            for volume in result.get("volumes", []):
                titles = [s.get("title", "") for s in volume.get("sections", [])]
                if not titles:
                    continue

                classifications = section_classifier.classify_batch(titles)

                for section, (predicted_type, confidence) in zip(volume.get("sections", []), classifications):
                    llm_type = section.get("type", "narrative")
                    if predicted_type != llm_type and confidence > 0.7:
                        logger.debug(
                            f"Type correction: '{section.get('title')}' "
                            f"{llm_type} → {predicted_type} (conf={confidence:.2f})"
                        )
                        section["type"] = predicted_type
                        section["type_confidence"] = round(confidence, 3)
                        section["type_source"] = "classifier"
                        corrections += 1
                    else:
                        section["type_source"] = "llm"

            if corrections > 0:
                logger.info(f"Section type classifier corrected {corrections} section types")

        except Exception as e:
            logger.warning(f"Section classifier not available, keeping LLM types: {e}")

        return result

