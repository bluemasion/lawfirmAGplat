"""Requirement extraction skill — analyze tender → derive bid document structure.

V3: Multi-pass LLM analysis.
  Pass 1: Understand the tender, extract key requirements & rejection conditions
  Pass 2: Generate bid document structure from the analysis
"""

import json
from typing import Any, Dict, List

from app.core.skills.base import BaseSkill
from app.core.llm import get_llm
from app.utils.logger import logger


# ── Pass 1: Analyze tender document ──

ANALYSIS_SYSTEM = """你是资深招投标专家，精通政府采购和企业招标流程。
你的任务是深度分析招标文件，提取对编制投标文件至关重要的结构化信息。
你必须输出严格的 JSON 格式，不要包含任何其他内容。"""

ANALYSIS_PROMPT = """请深度分析以下招标文件内容，提取编制投标文件所需的关键信息。

【招标文件内容】
{tender_text}

请按以下维度提取信息，输出 JSON：
{{
  "project_info": {{
    "project_name": "项目名称",
    "project_type": "项目类型（如法律服务、IT采购、工程等）",
    "tender_org": "招标方名称",
    "budget": "预算/最高限价（如有）"
  }},

  "bid_composition": {{
    "has_explicit_format": true,
    "description": "招标文件是否有明确的投标文件格式要求章节（如第六章投标文件格式）",
    "required_documents": [
      {{
        "name": "文档名称（如：投标函、授权委托书、营业执照副本等）",
        "category": "form|table|qualification|narrative",
        "is_mandatory": true,
        "source": "引用自招标文件的哪一条/哪一章"
      }}
    ]
  }},

  "rejection_conditions": [
    {{
      "condition": "废标/否决条件的具体描述",
      "related_document": "需要提供什么文件/满足什么条件来避免废标",
      "source": "来源引用"
    }}
  ],

  "evaluation_criteria": [
    {{
      "item": "评分项名称",
      "max_score": 0,
      "description": "评分要点",
      "bid_section_needed": "投标文件中需要哪个章节来回应这个评分项",
      "sub_criteria": [
        {{
          "name": "子评分项名称",
          "score": 0,
          "scoring_rule": "得分规则，如：5人以上得8分，3-5人得5分"
        }}
      ]
    }}
  ],

  "qualification_requirements": [
    "资质要求1（如：具有有效的律师事务所执业许可证）",
    "资质要求2"
  ],

  "format_requirements": {{
    "font": "字体要求",
    "paper_size": "纸张大小",
    "binding": "装订要求",
    "copies": "份数（正本/副本）",
    "other": "其他格式要求"
  }},

  "deadline_info": {{
    "submission_deadline": "投标截止时间",
    "opening_time": "开标时间",
    "validity_period": "投标有效期"
  }},

  "special_requirements": [
    "其他特殊要求(如落实政策要求、节能环保、中小企业扶持等)"
  ]
}}

【分析要点】
1. 重点关注「投标人须知」「投标人须知前附表」中的强制要求和废标条件
2. 如果有「投标文件格式」章节，从中提取投标文件的完整组成清单
3. 如果没有明确的格式章节，从评标办法、资格条件、技术要求中推导出投标文件应包含的部分
4. 废标条件（rejection_conditions）是最重要的——任何漏项都会导致投标无效
5. 评标办法中的评分项目直接决定了投标文件的核心章节
6. evaluation_criteria 必须深度提取：
   - 每个评分大项下的子评分项（sub_criteria）必须逐条列出
   - 包含具体得分规则（如"5人以上得8分，3-5人得5分"）
   - 子项分值之和应等于大项的 max_score
   - 如果评标办法以表格形式呈现，逐行提取
7. 所有字段尽量填写，实在找不到的写 null

请严格输出 JSON，不要有任何额外说明文字。"""


# ── Pass 2: Generate bid document structure ──

STRUCTURE_SYSTEM = """你是资深投标文件编制专家。
你的任务是根据招标文件分析结果，生成一份完整的投标文件目录结构。
这份目录将直接用于指导 AI 逐章节生成投标文件内容。
你必须输出严格的 JSON 格式，不要包含任何其他内容。"""

STRUCTURE_PROMPT = """根据以下招标文件分析结果，生成完整的投标文件目录结构。

【招标分析结果】
{analysis_json}

【招标文件原文参考（用于补充上下文）】
{tender_context}

请生成投标文件的完整目录结构，输出 JSON：
{{
  "bid_title": "XX项目投标文件",
  "volumes": [
    {{
      "name": "分册名称（如只有一个分册，用\"投标文件\"）",
      "sections": [
        {{
          "order": 1,
          "title": "章节标题",
          "type": "narrative|table|form|qualification",
          "required": true,
          "rejection_risk": false,
          "score_weight": 0,
          "content_hints": "该章节应包含的具体内容描述",
          "content_outline": [
            "子要点1：该章节需要覆盖的第一个关键内容",
            "子要点2：该章节需要覆盖的第二个关键内容",
            "子要点3：该章节需要覆盖的第三个关键内容"
          ],
          "material_refs": [
            "需引用的素材类型和数量，如：项目经理简历、类似业绩3项、营业执照副本"
          ],
          "data_fields": ["需要填写的数据字段（如有）"],
          "source_reference": "对应招标文件的要求来源"
        }}
      ]
    }}
  ],
  "rejection_items": [
    {{
      "description": "废标条件描述",
      "related_sections": ["关联的投标文件章节标题"],
      "severity": "critical"
    }}
  ]
}}

【投标文件编制规则】
1. 章节类型说明：
   - form: 固定格式的函件（投标函、授权委托书、声明函等）
   - table: 需要表格呈现的内容（报价表、业绩表、人员表等）
   - qualification: 需要提供的资质证明文件（营业执照、执业许可证等）
   - narrative: 需要撰写的叙述性方案内容（服务方案、技术方案等）

2. 标准投标文件结构通常包含（具体以招标文件要求为准）：
   - 第一部分：商务文件（投标函、声明函、授权委托书等）
   - 第二部分：资格证明文件（营业执照、资质证书等）
   - 第三部分：报价文件（报价表、费用明细等）
   - 第四部分：技术/服务方案（服务方案、实施计划等）
   - 第五部分：业绩与团队（类似业绩、团队介绍等）
   - 第六部分：其他补充文件

3. rejection_risk = true 的章节是：招标文件中明确要求必须提供的，缺失会导致废标
4. score_weight: 如果该章节对应某个评分项，填写该评分项的最高分值
5. 确保招标文件中所有废标条件对应的文件都有对应章节
6. 确保评标办法中所有评分维度都有对应的投标章节

7. content_outline 规则：
   - 每个章节必须有 3-5 个子要点，描述该章节需要写哪些具体内容
   - narrative 类型：列出需要论述的关键主题和要点
   - table 类型：列出表格应包含的数据列和关键内容
   - form 类型：列出需要填写的关键项目
   - qualification 类型：列出需要提供的具体证照文件

8. material_refs 规则：
   - 标注该章节在编制时需要从素材库引用的内容
   - 常见素材类型：人员简历、类似业绩/项目经验、资质证书、获奖荣誉
   - 如果不需要引用素材库，设为空数组 []
   - 示例：["项目经理及核心成员简历 3-5人", "近3年类似业绩 5项"]

请严格输出 JSON，不要有任何额外说明文字。"""


# ── Legacy prompts (kept for fallback) ──

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


def _safe_parse_json(text):
    # type: (str) -> Any
    """Try to parse JSON from LLM output, handling common issues."""
    text = text.strip()

    # Remove markdown code fences if present
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
        import re
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
    """Analyze tender document and derive bid document structure.

    V3 approach (default):
      Pass 1: Deep analysis of tender — extract requirements, rejection
              conditions, evaluation criteria, composition rules
      Pass 2: Generate bid document structure from the analysis

    Falls back to V2 (heading classification) if V3 fails.
    """

    name = "requirement_extraction"
    description = "分析招标文件，提取废标项和评分标准，智能生成投标文件目录结构"

    MAX_CHUNK_SIZE = 28000  # Qwen-Max supports ~32K tokens

    async def execute(self, params):
        # type: (Dict[str, Any]) -> Any
        """
        Params:
            raw_text (str): Full text of the tender document
            sections (List[Dict]): Parsed sections from tender_parsing
            llm_provider (str): Which LLM to use (default: "qwen")
            mode (str): 'analyze' (V3, default) or 'structure' (V2) or 'legacy' (V1)
        """
        raw_text = params.get("raw_text", "")
        sections = params.get("sections", [])
        llm_provider = params.get("llm_provider", "qwen")
        mode = params.get("mode", "analyze")

        if not raw_text and not sections:
            raise ValueError("Either raw_text or sections must be provided")

        llm = get_llm(llm_provider)
        logger.info(f"Extracting requirements using {llm.get_model_name()}, mode={mode}")

        if mode == "analyze":
            # ── V3: Multi-pass tender analysis ──
            progress_cb = params.get("progress_callback", None)
            result = await self._analyze_and_build(llm, raw_text, sections, progress_cb=progress_cb)
        elif mode == "structure" and sections:
            # ── V2: Classify parsed section titles ──
            result = await self._structure_from_sections(llm, sections, raw_text)
        else:
            # ── V1 Legacy ──
            result = await self._extract_full(llm, raw_text)

        if result is None:
            result = self._fallback_from_sections(sections)

        # Post-LLM: refine section types using local classifier
        result = self._refine_section_types(result)

        total_sections = sum(len(v.get('sections', [])) for v in result.get('volumes', []))
        logger.info(f"Extraction complete: {len(result.get('volumes', []))} volumes, "
                     f"{total_sections} sections (mode={mode})")
        return result

    # ── V3: Multi-pass analysis ──

    SCORING_KEYWORDS = [
        '评标', '评审', '评分', '打分', '计分',
        '评标办法', '评标标准', '评分标准', '评分细则',
        '评审标准', '评审办法', '评分方法',
    ]

    REJECTION_KEYWORDS = [
        '废标', '否决', '无效投标', '不予受理', '拒绝',
        '投标人须知', '须知前附表', '资格条件', '资格要求',
    ]

    @staticmethod
    def _render_table_as_markdown(table_data):
        # type: (Dict) -> str
        """Render a parsed table (from tender_parsing) as a markdown table."""
        rows = table_data.get('rows', [])
        if not rows:
            return ''
        # Build markdown table
        lines = []
        for i, row in enumerate(rows):
            line = '| ' + ' | '.join(cell.replace('|', '/') for cell in row) + ' |'
            lines.append(line)
            if i == 0:
                # Add separator after header
                lines.append('|' + '|'.join(['---'] * len(row)) + '|')
        return '\n'.join(lines)

    def _extract_scoring_sections(self, sections):
        # type: (List[Dict]) -> str
        """Locate and extract scoring/evaluation sections with table data."""
        scoring_parts = []
        for sec in (sections or []):
            title = sec.get('title', '')
            if any(kw in title for kw in self.SCORING_KEYWORDS):
                part = f"## {title}"
                content = sec.get('content', '')
                if content and len(content) > 20:
                    part += f"\n{content}"
                # Extract tables within this section
                for tbl in sec.get('tables', []):
                    md_table = self._render_table_as_markdown(tbl)
                    if md_table:
                        part += f"\n\n{md_table}"
                scoring_parts.append(part)
        return '\n\n'.join(scoring_parts) if scoring_parts else ''

    def _extract_rejection_sections(self, sections):
        # type: (List[Dict]) -> str
        """Locate and extract rejection/disqualification sections with table data."""
        rejection_parts = []
        for sec in (sections or []):
            title = sec.get('title', '')
            if any(kw in title for kw in self.REJECTION_KEYWORDS):
                part = f"## {title}"
                content = sec.get('content', '')
                if content and len(content) > 20:
                    part += f"\n{content}"
                for tbl in sec.get('tables', []):
                    md_table = self._render_table_as_markdown(tbl)
                    if md_table:
                        part += f"\n\n{md_table}"
                rejection_parts.append(part)
        return '\n\n'.join(rejection_parts) if rejection_parts else ''

    async def _analyze_and_build(self, llm, raw_text, sections, progress_cb=None):
        # type: (Any, str, List[Dict], Any) -> Dict
        """V3: Analyze tender → derive bid structure in two passes."""

        def _progress(msg):
            """Send progress update if callback is provided."""
            if progress_cb:
                try:
                    progress_cb(msg)
                except Exception:
                    pass

        async def _stream_with_progress(prompt, system, pass_name=""):
            """Use LLM streaming to show real-time generation progress."""
            buffer = []
            total_chars = 0
            last_report = 0
            REPORT_INTERVAL = 300  # Report every 300 chars

            try:
                async for chunk in llm.stream(prompt, system=system):
                    buffer.append(chunk)
                    total_chars += len(chunk)
                    # Send periodic progress with content snippet
                    if total_chars - last_report >= REPORT_INTERVAL:
                        last_report = total_chars
                        # Show last ~60 chars as a preview
                        recent = ''.join(buffer)[-80:].replace('\n', ' ').strip()
                        if len(recent) > 60:
                            recent = '...' + recent[-60:]
                        _progress(f"   └─ [{pass_name}] 已接收 {total_chars} 字符 | {recent}")
            except Exception as e:
                _progress(f"⚠️ [{pass_name}] 流式调用异常: {str(e)[:80]}")
                raise

            full_text = ''.join(buffer)
            _progress(f"   └─ [{pass_name}] 完成接收: 共 {len(full_text)} 字符")
            return full_text

        # ── Step 0: Extract scoring & rejection sections (with tables) ──
        scoring_text = self._extract_scoring_sections(sections)
        rejection_text = self._extract_rejection_sections(sections)
        if scoring_text:
            logger.info(f"Located scoring sections: {len(scoring_text)} chars "
                        f"(includes structured tables)")
            _progress(f"🏆 提取评分章节: {len(scoring_text)} 字符 (含表格结构)")
        if rejection_text:
            logger.info(f"Located rejection sections: {len(rejection_text)} chars")
            _progress(f"🔴 提取废标章节: {len(rejection_text)} 字符")

        # Prepare text: use full raw_text, truncate if too long
        text_for_analysis = raw_text
        if len(text_for_analysis) > self.MAX_CHUNK_SIZE:
            # Prioritize: keep beginning (project info, 投标人须知)
            # and end (投标文件格式, 评标办法 are often at the end)
            half = self.MAX_CHUNK_SIZE // 2
            text_for_analysis = (
                raw_text[:half] +
                "\n\n... (中间部分省略) ...\n\n" +
                raw_text[-half:]
            )
            logger.info(f"Tender text truncated: {len(raw_text)} → {len(text_for_analysis)} chars")

        # Append scoring sections (with structured tables) if truncated
        if scoring_text and len(raw_text) > self.MAX_CHUNK_SIZE:
            if scoring_text[:100] not in text_for_analysis:
                supplement = f"\n\n【评标办法原文（定向提取，含表格结构）】\n{scoring_text[:6000]}"
                text_for_analysis += supplement
                logger.info(f"Appended scoring section: +{len(supplement)} chars")

        # Append rejection sections if truncated
        if rejection_text and len(raw_text) > self.MAX_CHUNK_SIZE:
            if rejection_text[:100] not in text_for_analysis:
                supplement = f"\n\n【废标/否决条件原文（定向提取）】\n{rejection_text[:4000]}"
                text_for_analysis += supplement
                logger.info(f"Appended rejection section: +{len(supplement)} chars")

        # ── Pass 1: Deep analysis (with retry) ──
        logger.info("Pass 1: Analyzing tender document...")
        _progress("🧠 Pass 1/3: AI 正在分析招标文件要求（可能需要 2-5 分钟）...")
        analysis = None
        try:
            prompt1 = ANALYSIS_PROMPT.format(tender_text=text_for_analysis)
            _progress(f"   └─ Prompt 大小: {len(prompt1)} 字符, 模型: {llm.get_model_name()}")
            # Try up to 2 times to handle transient Qwen API timeouts
            for attempt in range(2):
                try:
                    response1 = await _stream_with_progress(prompt1, system=ANALYSIS_SYSTEM, pass_name="Pass1")
                    analysis = _safe_parse_json(response1)
                    if analysis:
                        break
                except Exception as retry_err:
                    if attempt == 0:
                        logger.warning(f"Pass 1 attempt 1 failed ({retry_err}), retrying in 3s...")
                        _progress(f"⚠️ Pass 1 第1次尝试失败: {str(retry_err)[:80]}，3秒后重试...")
                        import asyncio
                        await asyncio.sleep(3)
                    else:
                        raise
            if analysis:
                # Log key findings
                rej_count = len(analysis.get("rejection_conditions", []))
                eval_count = len(analysis.get("evaluation_criteria", []))
                doc_count = len(analysis.get("bid_composition", {}).get("required_documents", []))
                has_format = analysis.get("bid_composition", {}).get("has_explicit_format", False)
                logger.info(
                    f"Pass 1 results: {doc_count} required docs, "
                    f"{rej_count} rejection conditions, "
                    f"{eval_count} evaluation criteria, "
                    f"explicit_format={'yes' if has_format else 'no'}"
                )
                _progress(
                    f"✅ Pass 1 完成: {doc_count} 个必须文件, "
                    f"{rej_count} 个废标条件, "
                    f"{eval_count} 个评分大类"
                )
        except Exception as e:
            logger.error(f"Pass 1 analysis failed: {e}")
            _progress(f"❌ Pass 1 失败: {str(e)[:100]}")

        if not analysis:
            logger.warning("Pass 1 failed, falling back to V2 section classification")
            _progress("⚠️ AI 分析失败，降级到规则分类模式...")
            if sections:
                return await self._structure_from_sections(llm, sections, raw_text)
            return None

        # ── Pass 2: Generate bid structure ──
        logger.info("Pass 2: Generating bid document structure...")
        _progress("📝 Pass 2/3: AI 正在生成投标文件大纲（可能需要 3-5 分钟）...")
        try:
            analysis_json = json.dumps(analysis, ensure_ascii=False, indent=2)
            # Provide extra tender context for Pass 2
            tender_context = raw_text[:6000] if raw_text else "暂无原文"

            prompt2 = STRUCTURE_PROMPT.format(
                analysis_json=analysis_json,
                tender_context=tender_context,
            )
            response2 = await _stream_with_progress(prompt2, system=STRUCTURE_SYSTEM, pass_name="Pass2")
            structure = _safe_parse_json(response2)

            if structure and structure.get("volumes"):
                # Attach analysis results to the structure for frontend use
                structure["tender_analysis"] = {
                    "project_info": analysis.get("project_info", {}),
                    "rejection_conditions": analysis.get("rejection_conditions", []),
                    "evaluation_criteria": analysis.get("evaluation_criteria", []),
                    "qualification_requirements": analysis.get("qualification_requirements", []),
                    "format_requirements": analysis.get("format_requirements", {}),
                    "deadline_info": analysis.get("deadline_info", {}),
                }
                # Ensure all required fields exist
                if "rejection_items" not in structure:
                    structure["rejection_items"] = []
                if "qualification_requirements" not in structure:
                    structure["qualification_requirements"] = analysis.get("qualification_requirements", [])
                if "format_requirements" not in structure:
                    structure["format_requirements"] = analysis.get("format_requirements", {})
                if "evaluation_criteria" not in structure:
                    structure["evaluation_criteria"] = analysis.get("evaluation_criteria", [])
                if "deadline_info" not in structure:
                    structure["deadline_info"] = analysis.get("deadline_info", {})

                # Count rejection risk sections
                total_secs = 0
                rej_secs = 0
                for vol in structure.get("volumes", []):
                    for sec in vol.get("sections", []):
                        total_secs += 1
                        if sec.get("rejection_risk"):
                            rej_secs += 1
                logger.info(f"Pass 2 results: {total_secs} sections, "
                             f"{rej_secs} with rejection risk")
                _progress(f"✅ Pass 2 完成: {total_secs} 个章节, {rej_secs} 个有废标风险")

                # ── Pass 3: Deterministic verification ──
                _progress("🔍 Pass 3/3: 快速校验和联动匹配...")
                verification = self._verify_structure(analysis, structure)
                structure["verification"] = verification
                logger.info(
                    f"Pass 3 verification: "
                    f"rejection {verification['rejection_check']['covered']}/{verification['rejection_check']['total']}, "
                    f"evaluation {verification['evaluation_check']['covered']}/{verification['evaluation_check']['total']}, "
                    f"documents {verification['document_check']['covered']}/{verification['document_check']['total']}"
                )

                # ── Inject linkage into each section for frontend ──
                linkage = verification.get("section_linkage", {})
                linked_count = 0
                for vol in structure.get("volumes", []):
                    for sec in vol.get("sections", []):
                        title = sec.get("title", "")
                        if title in linkage:
                            sec["linked_scoring"] = linkage[title].get("scoring_items", [])
                            sec["linked_rejection"] = linkage[title].get("rejection_items", [])
                            sec["linked_total_score"] = linkage[title].get("total_score", 0)
                            linked_count += 1
                        else:
                            sec["linked_scoring"] = []
                            sec["linked_rejection"] = []
                            sec["linked_total_score"] = 0
                if linked_count:
                    logger.info(f"Section linkage: {linked_count} sections linked to scoring/rejection items")
                    _progress(f"✅ Pass 3 完成: {linked_count} 个章节关联到评分/废标项")

                return structure

        except Exception as e:
            logger.error(f"Pass 2 structure generation failed: {e}")

        # Fallback: build structure from Pass 1 analysis manually
        logger.warning("Pass 2 failed, building structure from Pass 1 analysis")
        return self._build_from_analysis(analysis)

    def _verify_structure(self, analysis, structure):
        # type: (Dict, Dict) -> Dict
        """Pass 3: Deterministic cross-reference verification.

        Compare Pass 1 analysis results against Pass 2 structure to check
        if all rejection conditions, evaluation criteria, and required
        documents are covered by the bid document structure.
        """
        # Collect all section titles for matching
        all_titles = []
        for vol in structure.get("volumes", []):
            for sec in vol.get("sections", []):
                all_titles.append(sec.get("title", ""))
        titles_text = " ".join(all_titles)

        def _find_matching_section(keywords):
            """Find a section title that matches any of the keywords."""
            if isinstance(keywords, str):
                keywords = [keywords]
            for kw in keywords:
                if not kw:
                    continue
                kw_lower = kw.lower().strip()
                for title in all_titles:
                    if kw_lower in title.lower():
                        return title
                # Fuzzy: check if key terms from kw appear in any title
                key_terms = [t for t in kw_lower.replace("（", " ").replace("）", " ").split() if len(t) >= 2]
                for title in all_titles:
                    title_lower = title.lower()
                    if any(term in title_lower for term in key_terms if len(term) >= 2):
                        return title
            return None

        # Collect rejection_risk sections
        rej_risk_titles = []
        for vol in structure.get("volumes", []):
            for sec in vol.get("sections", []):
                if sec.get("rejection_risk"):
                    rej_risk_titles.append(sec.get("title", ""))

        # Common keyword mapping: abstract condition → keywords to search in titles
        _CONDITION_KEYWORD_MAP = {
            "资格": ["资格", "资质", "证明", "营业执照", "执业"],
            "装订": ["装订", "格式", "投标文件"],
            "密封": ["密封", "投标文件"],
            "保证金": ["保证金", "担保"],
            "签署": ["签署", "签字", "公章", "投标函", "授权"],
            "完整": ["投标函", "开标", "报价"],
            "失信": ["信用", "失信", "声明"],
            "有效期": ["有效期", "投标函"],
            "报价": ["报价", "开标一览表", "价格"],
        }

        def _match_condition(condition_text, related_doc):
            """Try to match a rejection condition to a section via multiple strategies."""
            # Strategy 1: Direct match on related_document
            if related_doc:
                m = _find_matching_section([related_doc])
                if m:
                    return m

            # Strategy 2: Keyword map
            for trigger, search_terms in _CONDITION_KEYWORD_MAP.items():
                if trigger in condition_text:
                    for term in search_terms:
                        for title in all_titles:
                            if term in title:
                                return title

            # Strategy 3: Check if any rejection_risk section relates
            cond_lower = condition_text.lower()
            for title in rej_risk_titles:
                title_lower = title.lower()
                # If condition and title share meaningful Chinese chars
                shared = sum(1 for c in title_lower if c in cond_lower and len(c.encode('utf-8')) > 1)
                if shared >= 2:
                    return title

            # Strategy 4: Fall back to regular fuzzy
            return _find_matching_section([condition_text])

        # ── Rejection conditions check ──
        rejection_items = []
        for rc in analysis.get("rejection_conditions", []):
            condition = rc.get("condition", "")
            related = rc.get("related_document", "")
            matched = _match_condition(condition, related)
            rejection_items.append({
                "condition": condition,
                "related_document": related,
                "source": rc.get("source", ""),
                "status": "covered" if matched else "missing",
                "matched_section": matched,
            })

        rej_covered = sum(1 for r in rejection_items if r["status"] == "covered")

        # ── Evaluation criteria check ──
        # Synonym mapping for common evaluation terms → section titles
        _EVAL_SYNONYM_MAP = {
            '技术方案': ['技术', '方案', '实施', '解决方案', '技术路线'],
            '服务方案': ['服务', '运维', '售后', '服务保障', '服务承诺'],
            '团队': ['人员', '律师', '团队', '简历', '拟投入', '拟委派', '项目经理'],
            '业绩': ['业绩', '案例', '项目经验', '类似项目', '合同'],
            '报价': ['报价', '价格', '费用', '开标', '一览表', '投标报价'],
            '资质': ['资质', '证书', '营业执照', '许可证', '认证'],
            '管理': ['管理', '质量', '进度', '风控', '安全', '保密'],
            '培训': ['培训', '知识转移', '交接'],
            '应急': ['应急', '预案', '备份', '容灾'],
        }

        def _eval_match(item_name, needed):
            """Try to match an evaluation criterion to a section using synonyms."""
            # Direct match first
            matched = _find_matching_section([needed, item_name])
            if matched:
                return matched
            # Synonym-based matching
            for trigger, synonyms in _EVAL_SYNONYM_MAP.items():
                if trigger in item_name or trigger in (needed or ''):
                    for syn in synonyms:
                        for title in all_titles:
                            if syn in title:
                                return title
            return None

        eval_items = []
        for ec in analysis.get("evaluation_criteria", []):
            item_name = ec.get("item", "")
            needed = ec.get("bid_section_needed", "")
            matched = _eval_match(item_name, needed)
            eval_items.append({
                "item": item_name,
                "max_score": ec.get("max_score", 0),
                "description": ec.get("description", ""),
                "bid_section_needed": needed,
                "sub_criteria": ec.get("sub_criteria", []),
                "status": "covered" if matched else "missing",
                "matched_section": matched,
            })

        eval_covered = sum(1 for e in eval_items if e["status"] == "covered")

        # ── Required documents check ──
        doc_items = []
        for doc in analysis.get("bid_composition", {}).get("required_documents", []):
            doc_name = doc.get("name", "")
            matched = _find_matching_section([doc_name])
            doc_items.append({
                "name": doc_name,
                "category": doc.get("category", ""),
                "is_mandatory": doc.get("is_mandatory", True),
                "source": doc.get("source", ""),
                "status": "covered" if matched else "missing",
                "matched_section": matched,
            })

        doc_covered = sum(1 for d in doc_items if d["status"] == "covered")

        # ── Format & deadline info ──
        fmt = analysis.get("format_requirements", {})
        deadline = analysis.get("deadline_info", {})

        # ── Build forward index: section → linked scoring + rejection ──
        section_linkage = {}  # type: Dict[str, Dict]
        for ei in eval_items:
            matched = ei.get("matched_section", "")
            if matched:
                if matched not in section_linkage:
                    section_linkage[matched] = {
                        "scoring_items": [], "rejection_items": [],
                        "total_score": 0,
                    }
                section_linkage[matched]["scoring_items"].append({
                    "item": ei["item"],
                    "max_score": ei.get("max_score", 0),
                    "description": ei.get("description", ""),
                    "sub_criteria": ei.get("sub_criteria", []),
                })
                section_linkage[matched]["total_score"] += ei.get("max_score", 0)

        for ri in rejection_items:
            matched = ri.get("matched_section", "")
            if matched:
                if matched not in section_linkage:
                    section_linkage[matched] = {
                        "scoring_items": [], "rejection_items": [],
                        "total_score": 0,
                    }
                section_linkage[matched]["rejection_items"].append({
                    "condition": ri["condition"],
                    "source": ri.get("source", ""),
                })

        # ── Validate sub_criteria score sums ──
        score_warnings = []
        for ei in eval_items:
            subs = ei.get("sub_criteria", [])
            if subs:
                sub_total = sum(s.get("score", 0) for s in subs)
                max_score = ei.get("max_score", 0)
                if max_score > 0 and sub_total != max_score:
                    score_warnings.append({
                        "item": ei["item"],
                        "max_score": max_score,
                        "sub_total": sub_total,
                        "diff": max_score - sub_total,
                    })
        if score_warnings:
            logger.warning(f"Score sum mismatch in {len(score_warnings)} items: "
                          f"{score_warnings}")

        return {
            "rejection_check": {
                "total": len(rejection_items),
                "covered": rej_covered,
                "items": rejection_items,
            },
            "evaluation_check": {
                "total": len(eval_items),
                "covered": eval_covered,
                "items": eval_items,
            },
            "document_check": {
                "total": len(doc_items),
                "covered": doc_covered,
                "items": doc_items,
            },
            "format_info": fmt,
            "deadline_info": deadline,
            "section_linkage": section_linkage,
            "score_warnings": score_warnings,
        }

    def _build_from_analysis(self, analysis):
        # type: (Dict) -> Dict
        """Fallback: build bid structure directly from Pass 1 results."""
        sections = []
        order = 1

        # Add required documents from bid_composition
        for doc in analysis.get("bid_composition", {}).get("required_documents", []):
            sections.append({
                "order": order,
                "title": doc.get("name", f"文件{order}"),
                "type": doc.get("category", "narrative"),
                "required": doc.get("is_mandatory", True),
                "rejection_risk": doc.get("is_mandatory", False),
                "score_weight": 0,
                "content_hints": doc.get("source", ""),
                "content_outline": [],
                "material_refs": [],
                "data_fields": [],
            })
            order += 1

        # Add sections for evaluation criteria that don't have matching documents
        existing_titles = {s["title"] for s in sections}
        for crit in analysis.get("evaluation_criteria", []):
            needed = crit.get("bid_section_needed", "")
            if needed and needed not in existing_titles:
                sections.append({
                    "order": order,
                    "title": needed,
                    "type": "narrative",
                    "required": True,
                    "rejection_risk": False,
                    "score_weight": crit.get("max_score", 0),
                    "content_hints": crit.get("description", ""),
                    "content_outline": [crit.get("description", "")] if crit.get("description") else [],
                    "material_refs": [],
                    "data_fields": [],
                })
                existing_titles.add(needed)
                order += 1

        return {
            "bid_title": analysis.get("project_info", {}).get("project_name", "投标文件") or "投标文件",
            "volumes": [{"name": "投标文件", "sections": sections}],
            "rejection_items": [
                {
                    "description": r.get("condition", ""),
                    "related_sections": [r.get("related_document", "")],
                    "severity": "critical",
                }
                for r in analysis.get("rejection_conditions", [])
            ],
            "tender_analysis": {
                "project_info": analysis.get("project_info", {}),
                "rejection_conditions": analysis.get("rejection_conditions", []),
                "evaluation_criteria": analysis.get("evaluation_criteria", []),
                "qualification_requirements": analysis.get("qualification_requirements", []),
                "format_requirements": analysis.get("format_requirements", {}),
                "deadline_info": analysis.get("deadline_info", {}),
            },
            "qualification_requirements": analysis.get("qualification_requirements", []),
            "format_requirements": analysis.get("format_requirements", {}),
            "evaluation_criteria": analysis.get("evaluation_criteria", []),
            "deadline_info": analysis.get("deadline_info", {}),
        }

    # ── V2: Section title classification (kept as fallback) ──

    async def _structure_from_sections(self, llm, sections, raw_text):
        # type: (Any, List[Dict], str) -> Dict
        """V2: Build structure from parsed section titles, LLM classifies."""
        logger.info(f"V2 structure mode: {len(sections)} raw sections")

        sections = self._filter_bid_sections(sections)

        section_lines = []
        for i, sec in enumerate(sections, 1):
            title = sec.get("title", f"第{i}节")
            section_lines.append(f"{i}. {title}")

        section_list_text = "\n".join(section_lines)
        tender_context = raw_text[:8000] if raw_text else "暂无原文"

        prompt = BATCH_CLASSIFY_PROMPT.format(
            tender_context=tender_context,
            section_list=section_list_text,
        )

        try:
            response = await llm.generate(prompt, system=BATCH_CLASSIFY_SYSTEM)
            classifications = _safe_parse_json(response)
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            classifications = None

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

        bid_sections = []
        for i, sec in enumerate(sections):
            title = sec.get("title", f"第{i+1}节")
            original_type = sec.get("section_type", "narrative")
            content = sec.get("content", "")
            classification = classify_map.get(title, {})
            sec_type = classification.get("type", original_type)
            hints = classification.get("content_hints", content[:100] if content else "")
            fields = classification.get("data_fields", [])

            bid_sections.append({
                "order": i + 1,
                "title": title,
                "type": sec_type,
                "required": True,
                "rejection_risk": False,
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

    def _filter_bid_sections(self, sections):
        # type: (List[Dict]) -> List[Dict]
        """Filter tender_parsing sections to keep only bid-relevant headings."""
        import re

        SKIP_PATTERNS = [
            r'投标人应当', r'投标人递交', r'投标人没有',
            r'招标人有权', r'招标人不予',
            r'投标文件应当使用不褪色', r'应当按照招标文件',
            r'应当认真阅读', r'并加盖单位公章',
        ]
        skip_regex = re.compile('|'.join(SKIP_PATTERNS))

        MAX_TITLE_LEN = 60
        seen_titles = set()  # type: set
        filtered = []

        for sec in sections:
            title = sec.get("title", "").strip()
            if not title or len(title) > MAX_TITLE_LEN:
                continue
            if skip_regex.search(title):
                continue
            if title in seen_titles:
                continue
            seen_titles.add(title)
            filtered.append(sec)

        logger.info(f"Section filter: {len(sections)} → {len(filtered)}")
        return filtered

    # ── V1: Legacy single-pass extraction ──

    async def _extract_full(self, llm, raw_text):
        # type: (Any, str) -> Any
        """Legacy: Single pass extraction."""
        EXTRACTION_PROMPT = """请分析以下招标文件内容，提取投标文件需要包含的所有章节和要求。

【招标文件内容】
{tender_text}

请输出 JSON 结构（含 bid_title, volumes, qualification_requirements 等），只输出 JSON。"""

        prompt = EXTRACTION_PROMPT.format(tender_text=raw_text[:self.MAX_CHUNK_SIZE])
        response = await llm.generate(prompt, system=ANALYSIS_SYSTEM)
        return _safe_parse_json(response)

    def _fallback_from_sections(self, sections):
        # type: (List[Dict]) -> Dict
        """Create basic structure from parsed sections when all else fails."""
        logger.warning("Using fallback structure from parsed sections")
        bid_sections = []
        for i, sec in enumerate(sections):
            bid_sections.append({
                "order": i + 1,
                "title": sec.get("title", f"第{i+1}节"),
                "type": sec.get("section_type", "narrative"),
                "required": True,
                "rejection_risk": False,
                "content_hints": sec.get("content", "")[:100],
                "content_outline": [],
                "material_refs": [],
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

    def _refine_section_types(self, result):
        # type: (Dict) -> Dict
        """Use local BGE classifier to correct section types if available."""
        try:
            from app.core.rag.section_classifier import section_classifier

            corrections = 0
            for volume in result.get("volumes", []):
                titles = [s.get("title", "") for s in volume.get("sections", [])]
                if not titles:
                    continue

                classifications = section_classifier.classify_batch(titles)

                for section, (predicted_type, confidence) in zip(
                    volume.get("sections", []), classifications
                ):
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
                logger.info(f"Section type classifier corrected {corrections} types")

        except Exception as e:
            logger.warning(f"Section classifier not available: {e}")

        return result
