"""Content generation skill — generate bid section content.

Phase 2 refactor: only narrative sections use LLM.
Table/form/qualification sections use code templates + RAG data.
"""

import os
from typing import Any, Dict, List, Optional

from app.core.skills.base import BaseSkill
from app.core.skills.builtin.data_retrieval import DataRetrievalSkill
from app.core.skills.builtin.material_matcher import (
    MaterialMatcher, format_materials_for_prompt,
)
from app.core.llm import get_llm
from app.utils.logger import logger


def _get_material_store():
    """Lazy import material store to avoid circular imports."""
    try:
        from app.core.skills.builtin.material_store import get_material_store
        return get_material_store()
    except Exception:
        return None


# ── Prompts are now managed via PromptSkill system ──
# Legacy prompts kept for backward compatibility (non-streaming path)
from app.core.prompts.content_generation_prompts import (
    SECTION_GENERATION_SYSTEM,
    PROMPT_FIRM_INTRO,
    PROMPT_SERVICE_PLAN,
    PROMPT_COMPLIANCE,
    PROMPT_TEAM,
    PROMPT_PROJECT_PERF,
    NARRATIVE_PROMPT,
    PROMPT_ROUTING,
)
# New PromptSkill system (used in streaming path)
from app.core.prompts.prompt_skill import get_prompt_registry


def _route_prompt(title, return_type=False):
    # type: (str, bool) -> str
    """Match chapter title to specialized prompt template.

    If return_type=True, returns the type string (e.g. 'service_plan')
    instead of the prompt template. Used for reference_sections lookup.
    """
    title_lower = title.lower()
    for route in PROMPT_ROUTING:
        for kw in route["keywords"]:
            if kw in title_lower:
                logger.info(f"  Prompt routing: '{title}' → {route['type']}")
                return route["type"] if return_type else route["prompt"]
    logger.info(f"  Prompt routing: '{title}' → generic")
    return "generic" if return_type else NARRATIVE_PROMPT


# ── Built-in Form Templates (code, no LLM) ──

FORM_TEMPLATES = {
    "投标函": """## 投标函

致：{招标方名称}

{company_name}（以下简称"投标人"）经研究贵方发布的{项目名称}招标文件及其附件，我方愿意按照招标文件规定的条件和要求参加投标，并承诺如下：

1. 我方已仔细阅读并完全理解贵方招标文件的全部内容，接受招标文件的各项要求，不提出任何异议。
2. 我方承诺投标文件中所提供的全部资料和数据均真实、准确、完整、有效。
3. 我方投标有效期为自投标截止日起 [待补充：有效期天数] 个日历天。
4. 如我方中标，我方承诺按照招标文件规定的期限和条件履行合同义务。
5. 我方完全理解贵方不一定接受最低报价的投标或任何一个投标。
6. 与本投标有关的一切正式往来请按下列地址联系：

| 项目 | 内容 |
|------|------|
| 投标人名称 | {company_name} |
| 法定代表人 | {legal_rep} |
| 联系地址 | {address} |
| 联系电话 | {phone} |
| 传真号码 | {fax} |
| 电子邮箱 | {email} |
| 邮政编码 | [待补充：邮政编码] |

投标人（盖章）：{company_name}

法定代表人或其委托代理人（签字）：

日期：[待补充：投标日期]
""",

    "授权委托书": """## 授权委托书

本人{legal_rep}，系{company_name}的法定代表人，现特别授权{company_name}的 [待补充：被委托人姓名] 为我方代理人，以本公司名义参加{项目名称}项目的投标活动。

**代理人信息：**

| 项目 | 内容 |
|------|------|
| 姓名 | [待补充：被委托人姓名] |
| 性别 | [待补充：性别] |
| 职务 | [待补充：职务] |
| 身份证号 | [待补充：身份证号] |
| 联系电话 | [待补充：联系电话] |

代理人在上述项目投标活动中签署投标文件、进行澄清、签订合同及处理与之有关的一切事务，我均予以承认。

委托期限：自本授权书签发日起至该项目中标通知书规定的合同签订日止。

委托人（法定代表人签字）：
代理人签字：
{company_name}（盖章）
日期：[待补充：日期]
""",

    "企业信誉声明函": """## 企业信誉声明函

致：{招标方名称}

{company_name}就参加{项目名称}项目投标，郑重声明如下：

1. 我单位在最近三年内遵守国家有关法律、法令和条例，依法缴纳税收及社会保险，具有良好记录。
2. 我单位近三年内无以下重大违法违规行为：
   - 无重大质量事故
   - 无行政处罚记录
   - 无法人犯罪记录
   - 无拖欠工资和劳动纠纷群体性事件
3. 我单位不存在处于被责令停业、财产被接管、冻结、破产状态的情形。
4. 以上声明内容真实、准确、完整。如有不实，我单位愿意承担一切法律责任。

声明单位（盖章）：{company_name}
法定代表人（签字）：{legal_rep}
日期：[待补充：日期]
""",

    "非联合体投标承诺函": """## 非联合体投标承诺函（不存在任何形式的转包）

致：{招标方名称}

{company_name}郑重承诺：

1. 本次参加{项目名称}项目投标，我方以独立投标人身份参加投标，不以联合体方式投标。
2. 如我方中标，将由我方独立承担项目全部服务内容，不存在任何形式的转包、分包行为。
3. 我方具有独立完成本项目全部服务内容的能力和资源。
4. 如违反以上承诺，愿意承担由此引起的一切法律责任和经济损失。

承诺单位（盖章）：{company_name}
法定代表人或授权代理人（签字）：
日期：[待补充：日期]
""",

    "中小微企业声明函": """## 中小微企业声明函

本公司（供应商名称：{company_name}）参加{项目名称}采购活动，提供的服务全部由符合政策要求的中小微企业承接。相关中小微企业信息如下：

| 项目 | 信息 |
|------|------|
{fields}

本企业对上述声明内容的真实性负责。如有虚假，将依法承担相应责任。

声明单位（盖章）：{company_name}
日期：[待补充：日期]
""",

    "投标一览表": """## 投标一览表

| 序号 | 项目 | 内容 |
|------|------|------|
| 1 | 投标人名称 | {company_name} |
| 2 | 投标总价（人民币） | [待补充：投标总价] |
| 3 | 投标总价（大写） | [待补充：大写金额] |
| 4 | 服务期限 | [待补充：服务期限] |
| 5 | 质量标准 | 符合国家法律法规及行业标准 |
| 6 | 投标有效期 | [待补充：投标有效期] |
| 7 | 是否接受招标文件的全部条款 | 是 |

投标人（盖章）：{company_name}
法定代表人或其授权代理人（签字）：
日期：[待补充：投标日期]
""",

    "履约保证金承诺": """## 履约保证金承诺书

致：[待补充：招标方名称]

{company_name}就参加[待补充：项目名称]投标事宜，郑重承诺如下：

1. 若我方中标，我方将按照招标文件要求，在收到中标通知书后 [待补充：天数] 个工作日内缴纳履约保证金人民币 [待补充：金额] 元。
2. 在合同履行期间，如因我方原因造成合同无法履行或未按合同约定履行义务的，招标人有权扣除全部或部分履约保证金。
3. 合同履行完毕后，招标人应在验收合格后 [待补充：天数] 个工作日内，无息退还履约保证金。

投标人（盖章）：{company_name}
法定代表人或其授权代理人（签字）：
日期：[待补充：日期]
""",

    "投标保证金": """## 投标保证金承诺

致：[待补充：招标方名称]

{company_name}了解并承诺：若我方在投标有效期内撤回投标文件，或中标后未按规定签订合同，贵方有权不予退还投标保证金。

投标人（盖章）：{company_name}
法定代表人或其授权代理人（签字）：
日期：[待补充：日期]
""",
}


# ── Built-in Table Templates ──

TABLE_TEMPLATES = {
    "基本情况表": {
        "match_keywords": ["基本情况", "投标人基本", "供应商基本"],
        "generator": "_gen_company_basic_table",
    },
    "报价一览表": {
        "match_keywords": ["报价", "一览表", "投标一览", "分项报价"],
        "generator": "_gen_price_overview_table",
    },
    "报价明细表": {
        "match_keywords": ["报价明细", "费用明细", "分项明细"],
        "generator": "_gen_price_detail_table",
    },
    "业绩表": {
        "match_keywords": ["业绩", "项目经验", "类似项目", "合同业绩", "业绩统计"],
        "generator": "_gen_project_history_table",
    },
    "人员配置表": {
        "match_keywords": ["人员配置", "团队配置", "人员安排", "律师团队", "项目组",
                         "拟投入", "人员简历", "主要人员", "项目负责人"],
        "generator": "_gen_team_table",
    },
    "偏离表": {
        "match_keywords": ["偏离", "偏差", "响应偏离"],
        "generator": "_gen_deviation_table",
    },
    "技术偏离表": {
        "match_keywords": ["技术偏离", "技术偏差", "技术响应"],
        "generator": "_gen_tech_deviation_table",
    },
    "评审索引表": {
        "match_keywords": ["评审索引", "索引表"],
        "generator": "_gen_review_index_table",
    },
    "控股关系表": {
        "match_keywords": ["控股", "管理关系", "股东"],
        "generator": "_gen_shareholder_table",
    },
}


class ContentGenerationSkill(BaseSkill):
    """Generate content for individual bid sections.

    Phase 2 routing:
    - table → code template + RAG data
    - form → code template + RAG data
    - qualification → code placeholder (unchanged)
    - narrative → LLM generation (with optional skeleton reference)
    """

    name = "content_generation"
    description = "按章节类型分流生成投标内容：表格/表单用代码模板，叙述型用LLM"

    def __init__(self):
        self._data_retrieval = DataRetrievalSkill()

    async def execute(self, params: Dict[str, Any]) -> Any:
        section = params.get("section", {})
        company_info = params.get("company_info", "暂无律所信息")
        reference_data = params.get("reference_data", "暂无参考资料")
        llm_provider = params.get("llm_provider", "qwen")
        skeleton = params.get("skeleton", None)  # from template matching

        title = section.get("title", "未知章节")
        sec_type = section.get("type", "narrative")
        content_hints = section.get("content_hints", "")
        data_fields = section.get("data_fields", [])

        logger.info(f"Generating content for: [{sec_type}] {title}")

        # ── Route by type ──

        if sec_type == "qualification":
            content = self._generate_qualification_placeholder(title, content_hints, data_fields)
            return self._result(title, content, data_fields or [title], "placeholder")

        if sec_type == "table":
            content = await self._generate_table_by_template(title, content_hints, data_fields)
            missing = self._scan_missing(content)
            return self._result(title, content, missing, "template")

        if sec_type == "form":
            content = self._generate_form_by_template(title, content_hints)
            missing = self._scan_missing(content)
            return self._result(title, content, missing, "template")

        # ── narrative → LLM ──
        content = await self._generate_narrative_section(
            title, content_hints, reference_data, company_info, llm_provider, skeleton,
            company=params.get("company", "")
        )
        missing = self._scan_missing(content)
        return self._result(title, content, missing, "generated")

    async def execute_streaming(self, params, chunk_callback=None):
        # type: (Dict[str, Any], Any) -> Any
        """Like execute(), but streams narrative content via chunk_callback.

        chunk_callback(chunk: str) is called for each token/chunk of content.
        For table/form/qualification, the full content is generated instantly
        and chunk_callback is called once with the entire content.
        Returns the same result dict as execute().
        """
        section = params.get("section", {})
        company_info = params.get("company_info", "暂无律所信息")
        reference_data = params.get("reference_data", "暂无参考资料")
        llm_provider = params.get("llm_provider", "qwen")
        skeleton = params.get("skeleton", None)
        company = params.get("company", "")  # company name for material filtering
        project_id = params.get("project_id", None)  # project id for material filtering
        sibling_titles = params.get("sibling_titles", [])  # other section titles for boundary awareness

        title = section.get("title", "未知章节")
        sec_type = section.get("type", "narrative")
        content_hints = section.get("content_hints", "")
        data_fields = section.get("data_fields", [])
        content_outline = section.get("content_outline", [])
        material_refs = section.get("material_refs", [])
        linked_scoring = section.get("linked_scoring", [])
        linked_total_score = section.get("linked_total_score", 0)
        is_sub_section = section.get("is_sub_section", False)

        logger.info(f"Generating (stream) content for: [{sec_type}] {title}")
        if linked_scoring:
            logger.info(f"  Linked scoring: {len(linked_scoring)} items, total {linked_total_score}分")

        # ── Match materials for this section ──
        # Prefer pre-matched data from bidding pipeline's batch pre-matching
        matched_materials = section.get("pre_matched_materials", {})
        if not matched_materials and material_refs:
            store = _get_material_store()
            if store:
                matcher = MaterialMatcher(store)
                matched_materials = matcher.match_for_section(section, company=company, project_id=project_id)
        if matched_materials.get("match_summary"):
            logger.info(f"  Materials for '{title}': {matched_materials['match_summary']}")

        # ── Type override: force data-driven narrative for misclassified sections ──
        _NARRATIVE_FORCE_KEYWORDS = ["业绩", "项目经验", "项目案例", "成功案例",
                                     "团队介绍", "人员简介", "公司简介", "企业概况"]
        if sec_type in ("qualification", "table"):
            matched_projects = matched_materials.get("projects", [])
            matched_resumes = matched_materials.get("resumes", [])
            if any(kw in title for kw in _NARRATIVE_FORCE_KEYWORDS):
                if matched_projects or matched_resumes:
                    logger.info(
                        f"  Type override: '{title}' {sec_type} → narrative "
                        f"(matched {len(matched_projects)} projects, "
                        f"{len(matched_resumes)} resumes)"
                    )
                    sec_type = "narrative"

        # Non-narrative types: generate instantly, callback once
        if sec_type == "qualification":
            content = self._generate_qualification_placeholder(
                title, content_hints, data_fields,
                matched_quals=matched_materials.get("qualifications", [])
            )
            if chunk_callback:
                await chunk_callback(content)
            return self._result(title, content, data_fields or [title], "placeholder")

        if sec_type == "table":
            # If pre-filled content exists (e.g. auto-generated deviation table), use directly
            prefilled = section.get("_deviation_table_content", "")
            if prefilled:
                logger.info(f"  Using pre-filled deviation table for '{title}' ({len(prefilled)}字)")
                if chunk_callback:
                    await chunk_callback(prefilled)
                return self._result(title, prefilled, [], "deviation_table")
            content = await self._generate_table_by_template(
                title, content_hints, data_fields,
                company=company, project_id=project_id
            )
            if chunk_callback:
                await chunk_callback(content)
            missing = self._scan_missing(content)
            return self._result(title, content, missing, "template")

        if sec_type == "form":
            content = self._generate_form_by_template(title, content_hints, company=company, project_id=project_id)
            if chunk_callback:
                await chunk_callback(content)
            missing = self._scan_missing(content)
            return self._result(title, content, missing, "template")

        # ── Data-driven strategies: prefer real data over LLM ──
        team_kws = ["团队", "人员", "律师", "成员", "拟投入", "配置", "项目组"]
        project_kws = ["业绩", "案例", "经验", "履约", "类似项目"]
        title_lower = title.lower()

        # Strategy 1: Team narrative — use resumes directly
        if (any(kw in title_lower for kw in team_kws)
                and matched_materials.get("resumes")):
            content = self._generate_team_narrative(
                title, content_hints, matched_materials["resumes"],
                company_info, content_outline,
            )
            # Append ONLY resume images (not projects/qualifications)
            scoped = self._filter_materials_for_section(title, matched_materials)
            content += self._append_material_images(title, scoped)
            if chunk_callback:
                await chunk_callback(content)
            logger.info(f"  → Data-driven team narrative: {len(matched_materials['resumes'])} resumes")
            missing = self._scan_missing(content)
            return self._result(title, content, missing, "data_driven")

        # Strategy 2: Project narrative — use projects directly
        if (any(kw in title_lower for kw in project_kws)
                and matched_materials.get("projects")):
            content = self._generate_project_narrative(
                title, content_hints, matched_materials["projects"],
                company_info, content_outline,
            )
            # Append ONLY project evidence images
            scoped = self._filter_materials_for_section(title, matched_materials)
            content += self._append_material_images(title, scoped)
            if chunk_callback:
                await chunk_callback(content)
            logger.info(f"  → Data-driven project narrative: {len(matched_materials['projects'])} projects")
            missing = self._scan_missing(content)
            return self._result(title, content, missing, "data_driven")

        # ── Degradation guard: warn if expected data-driven section has no materials ──
        is_team_section = any(kw in title_lower for kw in team_kws)
        is_project_section = any(kw in title_lower for kw in project_kws)
        if is_team_section and not matched_materials.get("resumes"):
            logger.warning(
                f"  ⚠️ DEGRADATION: '{title}' is a team section but has 0 resumes! "
                f"Falling back to LLM generation. Check material dedup or uploads."
            )
        if is_project_section and not matched_materials.get("projects"):
            logger.warning(
                f"  ⚠️ DEGRADATION: '{title}' is a project section but has 0 projects! "
                f"Falling back to LLM generation. Check material dedup or uploads."
            )

        # ── narrative → LLM streaming (with enhanced prompt) ──
        task_id = params.get("task_id", "")
        content = await self._generate_narrative_section_streaming(
            title, content_hints, reference_data, company_info,
            llm_provider, skeleton, chunk_callback,
            content_outline=content_outline,
            matched_materials=matched_materials,
            company=company,
            project_id=project_id,
            sibling_titles=sibling_titles,
            linked_scoring=linked_scoring,
            linked_total_score=linked_total_score,
            task_id=task_id,
            is_sub_section=is_sub_section,
        )
        missing = self._scan_missing(content)
        return self._result(title, content, missing, "generated")

    async def _generate_narrative_section_streaming(
        self, title, hints, reference, company_info,
        llm_provider, skeleton=None, chunk_callback=None,
        content_outline=None, matched_materials=None, company="",
        project_id=None, sibling_titles=None,
        linked_scoring=None, linked_total_score=0,
        task_id="", is_sub_section=False,
    ):
        # type: (str, str, str, str, str, Optional[str], Any, Optional[List], Optional[Dict], str) -> str
        """Stream narrative section using llm.stream(), calling chunk_callback per token."""
        llm = get_llm(llm_provider)

        # Build prompt
        skeleton_hint = ""
        if skeleton:
            skeleton_hint = f"\n【参考骨架（来自历史模板）】\n{skeleton}\n请参考以上骨架结构，结合本次招标要求改写。\n"

        # ── Cross-section boundary hint (prevent content duplication) ──
        if sibling_titles:
            other_sections = [t for t in sibling_titles if t != title]
            if other_sections:
                boundary_hint = (
                    "\n【⚠️ 内容边界 — 防止章节间内容重复】\n"
                    "本投标文件中还有以下其他章节，它们各自有独立的内容。"
                    "请严格只写本章节的内容，不要涉及其他章节的主题：\n"
                )
                for ot in other_sections:
                    boundary_hint += f"- 《{ot}》\n"
                boundary_hint += (
                    "\n例如：如果有独立的'律所业绩'章节，本章节就不要再写业绩内容。"
                    "如果有独立的'项目团队配置'章节，本章节就不要再写团队介绍。\n"
                )
                skeleton_hint = boundary_hint + skeleton_hint

        # ── content_outline injection (with tender requirement linkage) ──
        outline_hint = ""
        if content_outline:
            outline_hint = "\n【本章内容大纲（必须逐条回应招标要求）】\n"
            for i, point in enumerate(content_outline, 1):
                # Parse "topic ← 招标原文：requirement" format
                if "← 招标原文：" in str(point):
                    topic, req = str(point).split("← 招标原文：", 1)
                    outline_hint += f"{i}. {topic.strip()}\n"
                    outline_hint += f"   📌 招标方要求：{req.strip()}\n"
                    outline_hint += f"   → 请针对以上要求给出具体、可操作的回应\n"
                else:
                    outline_hint += f"{i}. {point}\n"
            outline_hint += (
                "\n⚠️ 重要：请逐条回应以上每一个要点，"
                "确保招标方的每条具体要求都能在对应段落中找到明确回应。"
                "不要泛泛而谈，要有具体数据、时间节点和可执行的措施。\n"
            )
            logger.info(f"  Content outline injected: {len(content_outline)} points for '{title}'")

        # ── Material injection via MaterialMatcher ──
        structured_context = ""
        if matched_materials:
            structured_context = format_materials_for_prompt(matched_materials)
            if structured_context:
                logger.info(f"  MaterialMatcher injected: {matched_materials.get('match_summary', '')}")
        if not structured_context:
            # Fallback 1: use MaterialMatcher with title-based matching
            store = _get_material_store()
            if store:
                try:
                    matcher = MaterialMatcher(store)
                    fallback_section = {"title": title, "type": "narrative", "material_refs": [title]}
                    auto_matched = matcher.match_for_section(fallback_section, company=company, project_id=project_id)
                    structured_context = format_materials_for_prompt(auto_matched)
                    if structured_context:
                        logger.info(f"  MaterialMatcher (auto): {auto_matched.get('match_summary', '')}")
                except Exception as e:
                    logger.debug(f"MaterialMatcher auto-match failed for '{title}': {e}")

        if not structured_context:
            # Fallback 2: inject company material summary as background context.
            # Scope-filtered: only inject categories relevant to this section.
            store = _get_material_store()
            if store and company:
                try:
                    # Determine which categories are allowed for this section
                    allowed_cats = None
                    for kw, cats in self._SECTION_MATERIAL_SCOPE.items():
                        if kw in title:
                            allowed_cats = set(cats)
                            break
                    # If allowed_cats is empty list [], skip injection entirely
                    if allowed_cats is not None and len(allowed_cats) == 0:
                        logger.info(
                            f"  Company material summary SKIPPED for '{title}': "
                            f"scope rule = [] (pure LLM writing)"
                        )
                    elif allowed_cats is not None and "company_profile" in allowed_cats:
                        # Special: inject company profile summary (not full materials)
                        # Use company-aware profile to avoid leaking default firm data
                        profile = self._build_company_profile(company, project_id=project_id)
                        cp_parts = ["\n【我方公司核心信息（真实数据，必须在方案中引用）】"]
                        cp_parts.append(
                            f"- 公司名称：{profile.get('company_name', '?')}，"
                            f"成立于{profile.get('established_year', '?')}年"
                        )
                        highlight = profile.get('history_highlight', '')
                        if highlight:
                            cp_parts.append(f"- 历史地位：{highlight}")
                        cp_parts.append(
                            f"- 规模：执业律师{profile.get('lawyer_count', '?')}余名，"
                            f"合伙人{profile.get('partner_count', '?')}余名"
                        )
                        branch_count = profile.get('branch_count', 0)
                        if branch_count:
                            branches = profile.get('branch_offices', [])
                            branch_str = '、'.join(branches[:8])
                            if len(branches) > 8:
                                branch_str += f"等{branch_count}个分所"
                            cp_parts.append(f"- 分所网络：{branch_str}")
                        key_clients = profile.get('key_clients', [])
                        if key_clients:
                            cp_parts.append(
                                f"- 代表客户：{'、'.join(key_clients[:6])}"
                            )
                        strengths = profile.get('core_strengths', [])
                        if strengths:
                            cp_parts.append("\n【我方核心优势（请在方案中自然引用）】")
                            for s in strengths:
                                cp_parts.append(f"- {s}")
                        mgmt = profile.get('management_systems', {})
                        if mgmt:
                            cp_parts.append("\n【我方管理制度（质量控制类章节必须引用）】")
                            for k, v in mgmt.items():
                                cp_parts.append(f"- {v}")
                        structured_context = "\n".join(cp_parts)
                        structured_context += (
                            "\n\n⚠️ 重要：以上是我方公司的真实数据和制度。"
                            "请在方案中自然引用这些信息（特别是团队规模、"
                            "管理制度），不要使用泛泛的承诺性语言。\n"
                        )
                        logger.info(
                            f"  Company profile injected for '{title}': "
                            f"{len(structured_context)}字"
                        )
                    else:
                        company_context_parts = []

                        # Projects summary (only if allowed)
                        if allowed_cats is None or "projects" in allowed_cats:
                            projects = store.get_projects(company=company, project_id=project_id)
                            if projects:
                                company_context_parts.append(
                                    f"\n【我方公司业绩数据（{len(projects)}项，请在撰写中引用真实案例）】"
                                )
                                for p in projects[:6]:
                                    line = f"- {p.get('project_name', '?')}"
                                    if p.get('client'):
                                        line += f"，委托方: {p['client']}"
                                    if p.get('contract_amount') or p.get('amount'):
                                        line += f"，金额: {p.get('contract_amount', p.get('amount', ''))}"
                                    if p.get('description'):
                                        line += f"，{p['description'][:50]}"
                                    company_context_parts.append(line)

                        # Resumes summary (only if allowed)
                        if allowed_cats is None or "resumes" in allowed_cats:
                            resumes = store.get_resumes(company=company, project_id=project_id)
                            if resumes:
                                company_context_parts.append(
                                    f"\n【我方公司团队成员（{len(resumes)}人，可引用真实信息）】"
                                )
                                for r in resumes[:5]:
                                    line = f"- {r.get('name', '?')}"
                                    if r.get('title'):
                                        line += f"，{r['title']}"
                                    if r.get('specialty'):
                                        line += f"，擅长{r['specialty']}"
                                    company_context_parts.append(line)

                        # Qualifications summary (only if allowed)
                        if allowed_cats is None or "qualifications" in allowed_cats:
                            quals = store.get_qualifications(company=company, project_id=project_id)
                            if quals:
                                company_context_parts.append(
                                    f"\n【我方公司资质证书（{len(quals)}项，按需引用）】"
                                )
                                for q in quals[:5]:
                                    line = f"- {q.get('name', '?')}"
                                    if q.get('issuer'):
                                        line += f"，颁发: {q['issuer']}"
                                    company_context_parts.append(line)

                        if company_context_parts:
                            structured_context = "\n".join(company_context_parts)
                            structured_context += (
                                "\n\n⚠️ 重要写作指示：以上是我方公司的真实数据。"
                                "在撰写本章节时，请引用相关的真实案例或信息来支撑论述，"
                                "而不是使用泛泛的承诺性语言。\n"
                            )
                            injected_types = []
                            if allowed_cats is None or "projects" in (allowed_cats or set()):
                                injected_types.append(f"{len(store.get_projects(company=company, project_id=project_id))} projects")
                            if allowed_cats is None or "resumes" in (allowed_cats or set()):
                                injected_types.append(f"{len(store.get_resumes(company=company, project_id=project_id))} resumes")
                            if allowed_cats is None or "qualifications" in (allowed_cats or set()):
                                injected_types.append(f"{len(store.get_qualifications(company=company, project_id=project_id))} quals")
                            _types = ", ".join(injected_types)
                            logger.info(
                                f"  Company material summary injected for '{title}': "
                                f"{_types} (scope: {allowed_cats or 'all'})"
                            )
                except Exception as e:
                    logger.debug(f"Company material summary failed for '{title}': {e}")

        # ── Narrative RAG: search for relevant narrative chunks ──
        material_context = ""
        store = _get_material_store()
        if store:
            # Priority 1: Search reference_sections (historical winning bid sections)
            try:
                prompt_type = _route_prompt(title, return_type=True)
                ref_sections = store.search_reference_sections(
                    section_type=prompt_type,
                    query=title,
                    top_k=2,
                    company=company
                )
                if ref_sections:
                    material_context = (
                        "\n【历史中标方案参考（学习结构和论证方式，不要照抄）】\n"
                    )
                    for rs in ref_sections:
                        # Truncate to avoid context overflow
                        content_preview = rs['content'][:2000]
                        material_context += (
                            f"--- {rs['title']} ---\n{content_preview}\n\n"
                        )
                    material_context += (
                        "请参考以上方案的论证结构和写作方式，"
                        "结合本次招标的具体要求改写。\n"
                    )
                    logger.info(
                        f"  Reference RAG: {len(ref_sections)} sections "
                        f"for '{title}' (type={prompt_type})"
                    )
            except Exception as e:
                logger.debug(f"Reference section RAG failed for '{title}': {e}")

            # Priority 2: Fallback to narrative_chunks (if no reference sections)
            if not material_context:
                try:
                    relevant = await store.search_narratives(
                        title, top_k=3, company=company
                    )
                    if relevant:
                        material_context = "\n【来自历史投标文件的参考范文】\n"
                        for chunk in relevant:
                            material_context += (
                                f"[{chunk.get('title', '')}]\n"
                                f"{chunk.get('content', '')}\n\n"
                            )
                        material_context += (
                            "请参考以上范文的写法和结构，"
                            "结合本次招标要求改写。\n"
                        )
                        logger.info(
                            f"  Material RAG: {len(relevant)} chunks "
                            f"for '{title}'"
                        )
                except Exception as e:
                    logger.debug(f"Material RAG failed for '{title}': {e}")

        # ── Deterministic content block: pre-compose real data ──
        # Scope-filtered: only inject categories relevant to this section.
        deterministic_block = ""
        if company and not is_sub_section:
            # Check if this section should get any materials at all
            det_allowed = None
            for kw, cats in self._SECTION_MATERIAL_SCOPE.items():
                if kw in title:
                    det_allowed = set(cats)
                    break

            # If scope is empty list [], skip deterministic block entirely
            if det_allowed is not None and len(det_allowed) == 0:
                logger.info(
                    f"  Deterministic block SKIPPED for '{title}': "
                    f"scope rule = [] (pure LLM writing)"
                )
            else:
                store = _get_material_store()
                if store:
                    det_parts = []

                    # Inject project references (only if allowed)
                    if det_allowed is None or "projects" in det_allowed:
                        projects = store.get_projects(company=company)
                        if projects:
                            det_parts.append("\n### 我方相关业绩\n")
                            det_parts.append("我方在相关领域具有丰富的实践经验，代表性项目包括：\n")
                            for i, p in enumerate(projects[:5], 1):
                                line = f"{i}. **{p.get('project_name', '项目')}**"
                                if p.get('client'):
                                    line += f"（委托方：{p['client']}"
                                if p.get('contract_amount') or p.get('amount'):
                                    amt = p.get('contract_amount', p.get('amount', ''))
                                    line += f"，合同金额：{amt}"
                                if p.get('client'):
                                    line += "）"
                                if p.get('service_period') or p.get('period'):
                                    line += f"，服务期：{p.get('service_period', p.get('period', ''))}"
                                if p.get('description'):
                                    desc = p['description'][:80]
                                    line += f"。{desc}"
                                det_parts.append(line + "\n")
                            det_parts.append("")

                    # Inject team summary (only if allowed)
                    if det_allowed is None or "resumes" in det_allowed:
                        resumes = store.get_resumes(company=company)
                        if resumes:
                            det_parts.append("\n### 项目团队保障\n")
                            det_parts.append(
                                f"我方将组建由{len(resumes)}名专业人员组成的服务团队，核心成员包括：\n"
                            )
                            det_parts.append("| 姓名 | 职务/职称 | 专业方向 | 从业年限 |")
                            det_parts.append("|------|----------|---------|---------|")
                            for r in resumes[:6]:
                                name = r.get('name', '—')
                                title_r = r.get('title', '—')
                                spec = r.get('specialty', '—')
                                yrs = r.get('years_of_practice', '—')
                                det_parts.append(f"| {name} | {title_r} | {spec} | {yrs}年 |")
                            det_parts.append("")

                    # Inject qualification summary (only if allowed)
                    if det_allowed is None or "qualifications" in det_allowed:
                        quals = store.get_qualifications(company=company)
                        if quals:
                            det_parts.append("\n### 资质保障\n")
                            det_parts.append("我方持有以下相关资质证书：\n")
                            for q in quals[:5]:
                                qname = q.get('name', '—')
                                issuer = q.get('issuer', '')
                                line = f"- **{qname}**"
                                if issuer:
                                    line += f"（颁发机构：{issuer}）"
                                det_parts.append(line)
                            det_parts.append("")

                    if det_parts:
                        deterministic_block = "\n".join(det_parts)
                        logger.info(
                            f"  Deterministic block for '{title}': "
                            f"(scope: {det_allowed or 'all'}, "
                            f"block={len(deterministic_block)}字)"
                        )

        # ── Build scoring criteria context for LLM ──
        scoring_context = ""
        if linked_scoring:
            scoring_parts = [
                "\n\n━━━ 本章节对应的评分标准 ━━━",
                f"⚠️ 本章节共对应 {linked_total_score} 分，请严格按照以下评分标准组织内容："
            ]
            has_sub_criteria = False
            for si in linked_scoring:
                item = si.get('item', '')
                score = si.get('max_score', 0)
                desc = si.get('description', '')
                scoring_parts.append(f"\n【评分项: {item}】分值: {score}分")
                if desc:
                    scoring_parts.append(f"评分标准: {desc}")
                # Include sub-criteria if available
                subs = si.get('sub_criteria', [])
                for sub in subs:
                    sub_name = sub.get('name', sub) if isinstance(sub, dict) else sub
                    sub_score = sub.get('score', '') if isinstance(sub, dict) else ''
                    scoring_parts.append(f"  - {sub_name}")
                # Auto-generate mandatory section headings from sub_criteria
                if subs and len(subs) >= 2:
                    has_sub_criteria = True
                    scoring_parts.append(
                        f"\n📋 你必须按以下子评分项分段撰写，每段用二级标题（##）："
                    )
                    for sub in subs:
                        sub_name = sub.get('name', sub) if isinstance(sub, dict) else sub
                        sub_score = sub.get('score', '') if isinstance(sub, dict) else ''
                        score_label = f"（{sub_score}分）" if sub_score else ""
                        scoring_parts.append(f"  → ## {sub_name}{score_label}")
                    scoring_parts.append(
                        "每个子项段落至少 300 字，包含：方法论 + 具体措施 + 量化承诺。"
                    )
            scoring_parts.append(
                "\n❗ 写作要求：内容必须逐项回应以上评分标准，"
                "确保评委能直接找到得分点。"
                "每个评分项应有对应的内容段落，不要遗漏任何评分点。"
            )
            if has_sub_criteria:
                scoring_parts.append(
                    "⚠️ 每个子评分项必须有独立的二级标题(##)段落，"
                    "评委会按子项逐一打分！"
                )
            scoring_context = "\n".join(scoring_parts)
            logger.info(f"  Scoring context injected: {len(scoring_context)}字")

        # ── Build prompt via PromptSkill (dynamic, company-aware) ──
        prompt_registry = get_prompt_registry()
        prompt_skill = prompt_registry.match(title)

        # Build context for PromptSkill
        prompt_context = {
            "company_info": company_info,
            "reference_data": reference,
            "skeleton_hint": skeleton_hint,
            "scoring_context": scoring_context,
        }

        # Inject team/projects/qualifications from store into context
        store = _get_material_store()
        if store and company:
            try:
                prompt_context["team"] = store.get_resumes(
                    company=company, project_id=project_id
                )
                prompt_context["projects"] = store.get_projects(
                    company=company, project_id=project_id
                )
                prompt_context["qualifications"] = store.get_qualifications(
                    company=company, project_id=project_id
                )
            except Exception as e:
                logger.warning(f"  PromptSkill context build error: {e}")

        section_dict = {
            "title": title,
            "content_hints": hints or "按照招标要求撰写",
        }

        # ── Word count requirement (dynamic by scoring weight) ──
        if is_sub_section:
            min_words = 1500
        elif linked_total_score >= 20:
            min_words = 3000
        elif linked_total_score >= 10:
            min_words = 2500
        else:
            min_words = 2000

        word_count_hint = (
            f"\n\n⚠️ 字数要求：本章节内容不少于 {min_words} 字。"
            f"请详细展开论述，包含具体措施、时间节点、人员安排等细节。"
            f"避免空洞的承诺性语言，每个要点至少展开2-3段。\n"
        )
        prompt_context["word_count_hint"] = word_count_hint

        prompt = prompt_skill.build_prompt(section_dict, prompt_context)
        # Append word count hint directly to prompt if not already included
        if f"{min_words}" not in prompt:
            prompt += word_count_hint
        system_prompt = prompt_skill.get_system_prompt()

        logger.info(
            f"  PromptSkill '{prompt_skill.name}' built prompt: "
            f"{len(prompt)}字, system: {len(system_prompt)}字"
        )

        # Stream from LLM, accumulate full content
        full_content = []

        # First: emit the deterministic block (real data, guaranteed in output)
        if deterministic_block:
            if chunk_callback:
                await chunk_callback(deterministic_block + "\n\n")
            full_content.append(deterministic_block + "\n\n")

        # Then: stream LLM-generated analytical content
        try:
            async for token in llm.stream(prompt, system=system_prompt):
                full_content.append(token)
                if chunk_callback:
                    await chunk_callback(token)
        except Exception as e:
            error_msg = f"[LLM流式生成错误: {str(e)}]"
            full_content.append(error_msg)
            if chunk_callback:
                await chunk_callback(error_msg)
            logger.error(f"Stream generation failed for '{title}': {e}")

        # ── Append matched material images (qualifications, certifications) ──
        if matched_materials:
            img_block = self._append_material_images(title, matched_materials)
            if img_block:
                full_content.append(img_block)
                if chunk_callback:
                    await chunk_callback(img_block)

        final_content = "".join(full_content)

        # ── Collect training data for future SFT fine-tuning ──
        try:
            from app.core.skills.builtin.training_collector import save_training_sample
            _task_id = task_id
            save_training_sample(
                task_id=_task_id,
                section_title=title,
                prompt_skill=prompt_skill.name,
                prompt=prompt,
                system=system_prompt,
                output=final_content,
                llm_provider=llm_provider,
                section_type="narrative",
                scoring_weight=linked_total_score,
            )
        except Exception as _train_err:
            logger.debug(f"Training data collection failed: {_train_err}")

        return final_content

    # ── Material image embedding helper ──

    # Section topic → allowed material categories for image attachment.
    # This prevents team chapters from showing financial audit images, etc.
    _SECTION_MATERIAL_SCOPE = {
        # topic_keywords → allowed categories
        # 团队类: 只附简历+证件照
        "团队": ["resumes"],
        "人员": ["resumes"],
        "律师": ["resumes"],
        "成员": ["resumes"],
        "拟投入": ["resumes"],
        # 业绩类: 只附业绩合同扫描件
        "业绩": ["projects"],
        "案例": ["projects"],
        "项目经验": ["projects"],
        # 资质类: 只附资质证书
        "资格审查": ["qualifications"],
        "资质": ["qualifications"],
        "荣誉": ["qualifications"],
        "奖项": ["qualifications"],
        # 方案类: 注入公司概要（非全量素材，给LLM律所特色数据）
        "方案": ["company_profile"],
        "质量": ["company_profile"],
        "控制": ["company_profile"],
        # 声明类: 不注入素材（纯模板）
        "措施": [],
        "承诺": [],
    }

    @classmethod
    def _filter_materials_for_section(cls, title, matched_materials):
        # type: (str, dict) -> dict
        """Filter matched_materials to only include categories relevant
        to the section's topic. Returns a new dict with irrelevant
        categories emptied out."""
        # Determine allowed categories based on title keywords
        allowed = None
        for kw, categories in cls._SECTION_MATERIAL_SCOPE.items():
            if kw in title:
                allowed = set(categories)
                break

        if allowed is None:
            # No scope rule matched → return all (for generic chapters)
            return matched_materials

        # Build filtered copy
        filtered = dict(matched_materials)
        for key in ["resumes", "projects", "qualifications"]:
            if key not in allowed:
                filtered[key] = []

        old_count = sum(
            len(matched_materials.get(k, []))
            for k in ["resumes", "projects", "qualifications"]
        )
        new_count = sum(
            len(filtered.get(k, []))
            for k in ["resumes", "projects", "qualifications"]
        )
        if old_count != new_count:
            logger.info(
                f"  Material scope filter for '{title}': "
                f"{old_count} → {new_count} items "
                f"(allowed: {allowed})"
            )
        return filtered

    @staticmethod
    def _append_material_images(title: str, matched_materials: dict) -> str:
        """Generate markdown image references for matched material images.
        Supports both flat format ['hash.png'] and typed format
        [{'file': 'hash.png', 'type': 'id_card', 'label': '身份证'}].
        Returns a string block to append to section content.
        """
        images_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "..",
            "data", "materials", "images"
        )
        images_dir = os.path.normpath(images_dir)
        image_lines = []
        image_count = 0

        for category, label_key, label_suffix in [
            ("qualifications", "name", ""),
            ("resumes", "name", " — 执业证书"),
            ("projects", "project_name", " — 业绩证明"),
        ]:
            for item in matched_materials.get(category, []):
                item_images = item.get('_images', [])
                if not item_images:
                    continue

                item_name = item.get(label_key, category)
                image_lines.append(f"\n#### {item_name}{label_suffix}\n")

                for img_entry in item_images:
                    # Support both formats
                    if isinstance(img_entry, dict):
                        img_file = img_entry.get('file', '')
                        img_label = img_entry.get('label', item_name)
                        caption = f"{item_name} - {img_label}"
                    else:
                        img_file = img_entry
                        caption = item_name

                    if not img_file:
                        continue
                    img_path = os.path.join(images_dir, img_file)
                    if os.path.exists(img_path):
                        image_lines.append(f"![{caption}]({img_path})")
                        image_count += 1

        if image_lines:
            logger.info(
                f"  → Material images appended for '{title}': {image_count} images"
            )
            return "\n\n---\n\n### 附件：相关证明材料\n" + "\n".join(image_lines) + "\n"
        return ""

    # ── Form: code templates ──

    def _build_company_profile(self, company: str = "",
                               project_id: int = None) -> dict:
        """Build company profile: for the selected company, prefer material store
        data over default company_profile.json to ensure data isolation.
        """
        default_profile = self._data_retrieval.get_company_profile()
        default_name = default_profile.get("company_name", "")

        # If no company specified or same as default, use default profile
        if not company or company == default_name:
            return default_profile

        # Different company selected — build profile from material store
        store = _get_material_store()
        if not store:
            # No store available — return minimal profile with just the name
            logger.info(f"  [profile] No material store, using company_name='{company}' only")
            return {"company_name": company}

        profile = {"company_name": company}

        # Try to get richer info from material store
        try:
            resumes = store.get_resumes(company=company, project_id=project_id)
            projects = store.get_projects(company=company, project_id=project_id)
            quals = store.get_qualifications(company=company, project_id=project_id)

            if resumes:
                profile["lawyer_count"] = str(len(resumes))
                # Find the most senior person as potential legal_rep
                for r in resumes:
                    if any(kw in (r.get('title', '') or '') for kw in ['主任', '总经理', '法人', '董事长']):
                        profile["legal_rep"] = r.get('name', '')
                        break
            if projects:
                profile["project_count"] = str(len(projects))
            if quals:
                profile["qualification_count"] = str(len(quals))

            logger.info(
                f"  [profile] Built profile for '{company}' from material store: "
                f"{len(resumes)} resumes, {len(projects)} projects, {len(quals)} quals"
            )
        except Exception as e:
            logger.warning(f"  [profile] Failed to build profile for '{company}': {e}")

        return profile

    def _generate_form_by_template(self, title: str, hints: str,
                                   company: str = "",
                                   project_id: int = None) -> str:
        """Generate form content using built-in templates."""
        profile = self._build_company_profile(company, project_id=project_id)

        # Find matching form template (precise matching)
        title_stripped = title.strip()

        # 1. Exact match
        if title_stripped in FORM_TEMPLATES:
            tpl_name = title_stripped
            logger.info(f"  → Form template exact match: {tpl_name}")
            return self._fill_form_template(FORM_TEMPLATES[tpl_name], profile)

        # 2. Keyword-based match (more precise than substring)
        FORM_MATCH_KEYWORDS = {
            "投标函": ["投标函"],
            "授权委托书": ["授权委托", "委托书"],
            "企业信誉声明函": ["信誉声明", "企业信誉"],
            "非联合体投标承诺函": ["非联合体", "不存在任何形式"],
            "中小微企业声明函": ["中小微", "中小企业"],
            "投标一览表": ["投标一览", "开标一览"],
            "履约保证金承诺": ["履约保证金"],
            "投标保证金": ["投标保证金"],
        }

        for tpl_name, keywords in FORM_MATCH_KEYWORDS.items():
            if tpl_name in FORM_TEMPLATES:
                # Must match specific keywords, not just any substring
                if any(kw in title_stripped for kw in keywords):
                    # Avoid false positives: "投标函" should not match "投标保证金说明函"
                    # Only match if the keyword is closely tied to the title
                    if tpl_name == "投标函" and any(
                        excl in title_stripped
                        for excl in ["保证金", "担保", "声明", "承诺", "一览"]
                    ):
                        continue
                    if tpl_name == "投标保证金" and "凭证" in title_stripped:
                        continue
                    logger.info(f"  → Form template matched: {tpl_name}")
                    return self._fill_form_template(FORM_TEMPLATES[tpl_name], profile)

        # No match → generic form template with title
        logger.info(f"  → No form template match for '{title}', using generic")
        return self._generic_form(title, hints, profile)

    def _fill_form_template(self, tpl_content, profile):
        """Fill a form template with company profile data."""
        try:
            return tpl_content.format(
                company_name=profile.get("company_name", "[待补充：投标人名称]"),
                legal_rep=profile.get("legal_rep", "[待补充：法定代表人]"),
                address=profile.get("address", "[待补充：地址]"),
                phone=profile.get("phone", "[待补充：电话]"),
                fax=profile.get("fax", "[待补充：传真]"),
                email=profile.get("email", "[待补充：邮箱]"),
                total_staff=profile.get("total_staff", profile.get("lawyer_count", "[待补充：员工人数]")),
                招标方名称="[待补充：招标方名称]",
                项目名称="[待补充：项目名称]",
                fields="| [待补充] | [待补充] |",
            )
        except KeyError:
            # If template has unrecognized placeholders, return with partial fill
            return tpl_content

    # ── Table: code templates + data ──

    async def _generate_table_by_template(self, title: str, hints: str,
                                          data_fields: List[str],
                                          company: str = "",
                                          project_id: int = None) -> str:
        """Generate table section using code templates and RAG data."""
        profile = self._build_company_profile(company, project_id=project_id)

        for tpl_name, tpl_info in TABLE_TEMPLATES.items():
            if any(kw in title for kw in tpl_info["match_keywords"]):
                generator_name = tpl_info["generator"]
                generator = getattr(self, generator_name, None)
                if generator:
                    logger.info(f"  → Table template matched: {tpl_name}")
                    return generator(title, profile, company=company)

        # No match → generic table
        logger.info(f"  → No table template match for '{title}', using generic")
        return self._generic_table(title, hints, data_fields)

    # ── Narrative: LLM only ──

    async def _generate_narrative_section(self, title: str, hints: str,
                                           reference: str, company_info: str,
                                           llm_provider: str,
                                           skeleton: Optional[str] = None,
                                           company: str = "") -> str:
        """Generate narrative section using LLM (the only LLM-calling path)."""
        llm = get_llm(llm_provider)

        skeleton_hint = ""
        if skeleton:
            skeleton_hint = f"\n【参考骨架（来自历史模板）】\n{skeleton}\n请参考以上骨架结构，结合本次招标要求改写。\n"

        # S4: Add material RAG context from historical bid narratives
        material_context = ""
        store = _get_material_store()
        if store:
            try:
                relevant = await store.search_narratives(title, top_k=3, company=company)
                if relevant:
                    material_context = "\n【来自历史投标文件的参考范文】\n"
                    for chunk in relevant:
                        material_context += f"[{chunk.get('title', '')}]\n{chunk.get('content', '')}\n\n"
                    material_context += "请参考以上范文的写法和结构，结合本次招标要求改写。\n"
                    logger.info(f"  Material RAG: {len(relevant)} chunks for '{title}'")
            except Exception as e:
                logger.debug(f"Material RAG failed for '{title}': {e}")

        # S7-P1B: Inject structured materials for specific chapter types
        structured_context = ""
        # NOTE: This is the old non-streaming path. The company parameter
        # is not available here, so we cannot filter by company.
        # The streaming path (execute_streaming) should be preferred.
        if store:
            title_lower = title.lower()
            try:
                # Team/resume chapters → inject real lawyer bios
                team_kws = ["团队介绍", "人员介绍", "律师团队", "拟投入人员",
                            "项目团队", "核心团队", "服务团队", "人员配置"]
                if any(kw in title_lower for kw in team_kws):
                    resumes = store.get_resumes(company=company)
                    if resumes:
                        structured_context = "\n【素材库：律师简历数据】\n"
                        for r in resumes[:8]:
                            structured_context += (
                                f"- {r.get('name', '?')}, "
                                f"{r.get('title', '律师')}, "
                                f"执业{r.get('years_of_practice', '?')}年, "
                                f"擅长{r.get('specialty', '?')}"
                            )
                            cases = r.get('representative_cases', [])
                            if cases:
                                structured_context += f", 代表案例: {'; '.join(str(c) for c in cases[:3])}"
                            structured_context += "\n"
                        structured_context += "请使用以上真实律师信息撰写，不要编造姓名或经历。\n"
                        logger.info(f"  Structured inject: {len(resumes)} resumes for '{title}'")

                # Project/performance chapters → inject real project data
                proj_kws = ["业绩介绍", "类似业绩", "项目经验", "服务案例",
                            "成功案例", "代表业绩", "项目业绩"]
                if any(kw in title_lower for kw in proj_kws):
                    projects = store.get_projects(company=company)
                    if projects:
                        structured_context = "\n【素材库：项目业绩数据】\n"
                        for p in projects[:6]:
                            structured_context += (
                                f"- {p.get('project_name', '?')}, "
                                f"委托方: {p.get('client', '?')}, "
                                f"金额: {p.get('contract_amount', p.get('amount', '?'))}, "
                                f"类型: {p.get('project_type', '?')}"
                            )
                            desc = p.get('description', '')
                            if desc:
                                structured_context += f", {desc[:60]}"
                            structured_context += "\n"
                        structured_context += "请使用以上真实项目信息撰写，不要编造项目名称或金额。\n"
                        logger.info(f"  Structured inject: {len(projects)} projects for '{title}'")

                # Qualification chapters → inject real cert data
                qual_kws = ["资质", "资格", "荣誉", "证书"]
                if any(kw in title_lower for kw in qual_kws):
                    quals = store.get_qualifications(company=company)
                    if quals:
                        structured_context = "\n【素材库：资质证书数据】\n"
                        for q in quals[:10]:
                            structured_context += (
                                f"- {q.get('name', '?')}, "
                                f"编号: {q.get('number', '?')}, "
                                f"颁发: {q.get('issuer', '?')}, "
                                f"有效期至: {q.get('valid_until', '?')}\n"
                            )
                        structured_context += "请使用以上真实资质信息。\n"
                        logger.info(f"  Structured inject: {len(quals)} qualifications for '{title}'")
            except Exception as e:
                logger.debug(f"Structured material inject failed for '{title}': {e}")

        # Route to specialized prompt by chapter title keywords
        selected_prompt = _route_prompt(title)
        prompt = selected_prompt.format(
            section_title=title,
            content_hints=hints or "按照招标要求撰写",
            reference_data=reference,
            company_info=company_info,
            skeleton_hint=skeleton_hint + material_context + structured_context,
        )
        return await llm.generate(prompt, system=SECTION_GENERATION_SYSTEM)

    # ── Table generators ──

    def _gen_company_basic_table(self, title: str, profile: Dict, **kwargs) -> str:
        return f"""## {title}

| 项目 | 信息 |
|------|------|
| 投标人名称 | {profile.get('company_name', '[待补充]')} |
| 执业许可证号 | {profile.get('license_no', '[待补充]')} |
| 法定代表人 | {profile.get('legal_rep', '[待补充]')} |
| 成立时间 | {profile.get('established_year', '[待补充]')}年 |
| 注册资本 | {profile.get('registered_capital', '[待补充]')} |
| 律师人数 | {profile.get('lawyer_count', '[待补充]')}人 |
| 合伙人人数 | {profile.get('partner_count', '[待补充]')}人 |
| 联系地址 | {profile.get('address', '[待补充]')} |
| 联系电话 | {profile.get('phone', '[待补充]')} |
| 传真 | {profile.get('fax', '[待补充]')} |
| 电子邮箱 | {profile.get('email', '[待补充]')} |
| 开户银行 | {profile.get('bank_name', '[待补充]')} |
| 银行账号 | {profile.get('bank_account', '[待补充]')} |
"""

    def _gen_price_overview_table(self, title: str, profile: Dict, **kwargs) -> str:
        return f"""## {title}

| 序号 | 服务项目 | 单位 | 数量 | 单价（元） | 合计（元） | 备注 |
|------|---------|------|------|-----------|-----------|------|
| 1 | 常年法律顾问服务 | 年 | 1 | [待补充：单价] | [待补充：合计] | |
| 2 | 专项法律服务 | 项 | [待补充] | [待补充：单价] | [待补充：合计] | |
| 3 | 诉讼/仲裁代理 | 件 | [待补充] | [待补充：单价] | [待补充：合计] | |
| | **合计** | | | | **[待补充：总价]** | |

> 注：以上报价为含税价格，税率为 [待补充：税率]%。
"""

    def _gen_price_detail_table(self, title: str, profile: Dict, **kwargs) -> str:
        return f"""## {title}

| 序号 | 费用项目 | 计算方式 | 金额（元） | 说明 |
|------|---------|---------|-----------|------|
| 1 | 律师服务费 | [待补充] | [待补充] | 主要服务费用 |
| 2 | 调查取证费 | 实报实销 | [待补充] | 按实际发生 |
| 3 | 交通差旅费 | 实报实销 | [待补充] | 按实际发生 |
| 4 | 文印资料费 | 包含在服务费中 | — | |
| | **合计** | | **[待补充：合计]** | |
"""

    def _gen_project_history_table(self, title: str, profile: Dict, company: str = "") -> str:
        # S4: Check material store for projects first
        projects = []
        store = _get_material_store()
        if store:
            mat_projects = store.get_projects(company=company)
            if mat_projects:
                projects = mat_projects
                logger.info(f"  → Using {len(projects)} projects from material store")

        if not projects:
            projects = self._data_retrieval.get_similar_projects("", 10).get("projects", [])

        if not projects:
            return f"## {title}\n\n暂无业绩数据，请补充。\n"

        lines = [f"## {title}\n"]
        lines.append("| 序号 | 项目名称 | 委托方 | 服务内容 | 合同金额 | 服务期间 | 项目负责人 |")
        lines.append("|------|---------|-------|---------|---------|---------|----------|")
        for i, p in enumerate(projects, 1):
            name = p.get('project_name') or '[待补充]'
            client = p.get('client') or '[待补充]'
            desc = (p.get('description') or p.get('project_type') or '')[:30]
            amount = p.get('contract_amount') or p.get('amount') or '[待补充]'
            period = p.get('period') or f"{p.get('start_date', '?')} 至 {p.get('end_date', '?')}"
            lead = p.get('lead_lawyer') or '[待补充]'
            lines.append(f"| {i} | {name} | {client} | {desc} | {amount} | {period} | {lead} |")

        lines.append("")
        lines.append("> 注：以上业绩均为本律所近五年内完成的代表性项目，相关合同文件可供查验。")
        return "\n".join(lines) + "\n"

    def _gen_team_table(self, title: str, profile: Dict, company: str = "") -> str:
        # S4: Check material store for resumes first
        all_members = []
        store = _get_material_store()
        if store:
            mat_resumes = store.get_resumes(company=company)
            if mat_resumes:
                # Convert material store format to team member format
                all_members = []
                for r in mat_resumes:
                    all_members.append({
                        'name': r.get('name', '[待补充]'),
                        'title': r.get('title', '[待补充]'),
                        'license_no': r.get('license_number', '[待补充]'),
                        'specialties': [r.get('specialty', '')] if r.get('specialty') else [],
                        'years_experience': r.get('years_of_practice', '[待补充]'),
                        'education': r.get('education', '[待补充：学历]'),
                        'representative_cases': r.get('representative_cases', []),
                    })
                logger.info(f"  → Using {len(all_members)} resumes from material store")

        if not all_members:
            team_result = self._data_retrieval.get_team_for_project("", 10)
            all_members = team_result.get("recommended_team", [])

        if not all_members:
            return f"## {title}\n\n暂无团队数据，请补充。\n"

        lines = [f"## {title}\n"]

        # Summary table
        lines.append("### 项目团队一览表\n")
        lines.append("| 序号 | 姓名 | 职务/职称 | 执业证号 | 专业领域 | 本项目拟担任角色 |")
        lines.append("|------|------|---------|---------|---------|---------------|")
        for i, m in enumerate(all_members, 1):
            name = m.get('name', '[待补充]')
            title_str = m.get('title', '[待补充]')
            license_no = m.get('license_no', m.get('bar_number', '[待补充]'))
            specs = '、'.join(m.get('specialties', [])[:3]) if m.get('specialties') else '[待补充]'
            role = m.get('role_in_project', '项目负责人' if i == 1 else ('主办律师' if i <= 3 else '协办律师'))
            lines.append(f"| {i} | {name} | {title_str} | {license_no} | {specs} | {role} |")

        # Individual resumes
        lines.append("\n### 主要人员简历\n")
        for i, m in enumerate(all_members[:5], 1):
            name = m.get('name', '[待补充]')
            title_str = m.get('title', '')
            years = m.get('years_experience', m.get('experience_years', '[待补充]'))
            specs = '、'.join(m.get('specialties', [])) if m.get('specialties') else '[待补充]'
            edu = m.get('education', '[待补充：学历]')
            cases = m.get('representative_cases', m.get('notable_cases', []))

            lines.append(f"#### {i}. {name} — {title_str}\n")
            lines.append(f"- **执业年限**：{years}年")
            lines.append(f"- **专业领域**：{specs}")
            lines.append(f"- **学历**：{edu}")
            if cases:
                lines.append(f"- **代表案例**：")
                for c in cases[:3]:
                    if isinstance(c, str):
                        lines.append(f"  - {c}")
                    elif isinstance(c, dict):
                        lines.append(f"  - {c.get('name', c.get('case_name', str(c)))}")
            lines.append("")

        return "\n".join(lines) + "\n"

    def _gen_deviation_table(self, title: str, profile: Dict, **kwargs) -> str:
        return f"""## {title}

| 序号 | 招标文件条款号 | 招标文件条款内容 | 偏离情况 | 说明 |
|------|-------------|----------------|---------|------|
| 1 | | | 无偏离 | 完全响应 |
| 2 | | | 无偏离 | 完全响应 |

> 本公司对招标文件商务条款无偏离，完全接受招标文件的全部商务条款要求。
"""

    def _gen_tech_deviation_table(self, title: str, profile: Dict, **kwargs) -> str:
        return f"""## {title}

| 序号 | 招标文件条款号 | 技术要求 | 投标人响应 | 偏离程度 | 说明 |
|------|-------------|---------|-----------|---------|------|
| 1 | | | 响应 | 无偏离 | |
| 2 | | | 响应 | 无偏离 | |

> 本公司对招标文件技术要求无偏离，完全响应招标文件的全部技术规格要求。
"""

    def _gen_review_index_table(self, title: str, profile: Dict, **kwargs) -> str:
        return f"""## {title}

| 序号 | 评审内容 | 投标文件对应页码 | 备注 |
|------|---------|----------------|------|
| 1 | 投标函 | [待补充：页码] | |
| 2 | 投标人基本情况表 | [待补充：页码] | |
| 3 | 营业执照 | [待补充：页码] | |
| 4 | 执业许可证 | [待补充：页码] | |
| 5 | 法定代表人身份证明 | [待补充：页码] | |
| 6 | 近三年业绩证明 | [待补充：页码] | |
| 7 | 项目实施方案 | [待补充：页码] | |
| 8 | 服务团队配置 | [待补充：页码] | |
| 9 | 报价文件 | [待补充：页码] | |
"""

    def _gen_shareholder_table(self, title: str, profile: Dict, **kwargs) -> str:
        cn = profile.get("company_name", "[待补充：律所名称]")
        lr = profile.get("legal_rep", "[待补充：法定代表人]")
        return f"""## {title}

| 项目 | 内容 |
|------|------|
| 投标人名称 | {cn} |
| 法定代表人 | {lr} |
| 控股股东 | [待补充：控股股东名称] |
| 实际控制人 | [待补充：实际控制人] |
| 是否存在控股或管理关系 | [待补充：是/否] |
| 关联企业名称 | [待补充：关联企业名称（如有）] |

> 本公司郑重声明：以上信息真实、准确，如有隐瞒，愿承担相关法律责任。

投标人（盖章）：{cn}
日期：[待补充：日期]
"""

    # ── Generic fallbacks ──

    def _generic_form(self, title: str, hints: str, profile: Dict) -> str:
        cn = profile.get("company_name", "[待补充：投标人名称]")
        lr = profile.get("legal_rep", "[待补充：法定代表人]")
        return f"""## {title}

{hints if hints else '（请根据招标文件要求填写本部分内容）'}

声明单位（盖章）：{cn}
法定代表人（签字）：{lr}
日期：[待补充：日期]
"""

    def _generic_table(self, title: str, hints: str, fields: List[str]) -> str:
        if fields:
            header = "| " + " | ".join(fields) + " |"
            sep = "| " + " | ".join(["---"] * len(fields)) + " |"
            row = "| " + " | ".join([f"[待补充：{f}]" for f in fields]) + " |"
            return f"## {title}\n\n{header}\n{sep}\n{row}\n"
        return f"## {title}\n\n| 项目 | 内容 |\n|------|------|\n| [待补充] | [待补充] |\n"

    # ── Qualification (unchanged from Phase 1) ──

    def _generate_qualification_placeholder(self, title: str, hints: str,
                                            data_fields: List[str],
                                            matched_quals: List[dict] = None) -> str:
        """Generate qualification section content.
        
        If matched qualifications are provided from the material store,
        generates a real qualification list instead of placeholders.
        """
        if matched_quals:
            lines = [f"## {title}\n"]
            lines.append("以下为我方相关资质证书清单：\n")
            lines.append("| 序号 | 资质/证书名称 | 证书编号 | 颁发机构 | 有效期 |")
            lines.append("|------|--------------|---------|---------|--------|")
            for i, q in enumerate(matched_quals, 1):
                name = q.get('name', '[待补充]')
                number = q.get('number', '-')
                issuer = q.get('issuer', '-')
                valid_until = q.get('valid_until', '-')
                lines.append(f"| {i} | {name} | {number} | {issuer} | {valid_until} |")
            lines.append("")

            # ── Embed qualification images if available ──
            images_dir = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "..",
                "data", "materials", "images"
            )
            images_dir = os.path.normpath(images_dir)
            image_count = 0
            for q in matched_quals:
                q_images = q.get('_images', [])
                if q_images:
                    q_name = q.get('name', '资质证书')
                    lines.append(f"\n#### {q_name} — 证书扫描件\n")
                    for img_entry in q_images:
                        img_file = img_entry.get('file', img_entry) if isinstance(img_entry, dict) else img_entry
                        img_path = os.path.join(images_dir, img_file)
                        if os.path.exists(img_path):
                            lines.append(f"![{q_name}]({img_path})")
                            image_count += 1
                        else:
                            lines.append(f"[图片缺失: {img_file}]")
                    lines.append("")

            if image_count:
                logger.info(
                    f"  → Qualification images: {image_count} images "
                    f"for {len(matched_quals)} qualifications"
                )
            else:
                lines.append("> 注：以上资质证书复印件可供查验。")

            logger.info(f"  → Qualification from material store: {len(matched_quals)} items")
            return "\n".join(lines) + "\n"
        # Check if we have the qualification data
        quals_data = self._data_retrieval.get_qualifications()
        all_quals = quals_data.get("qualifications", [])

        content_parts = [f"## {title}\n"]

        # Try to match real qualification data
        matched_qual = None
        for q in all_quals:
            if any(kw in title for kw in [q.get("name", "")[:4]]):
                matched_qual = q
                break

        if matched_qual and matched_qual.get("file_available"):
            content_parts.append(
                f"> ✅ 已具备：{matched_qual['name']}（编号：{matched_qual['number']}，"
                f"有效期：{matched_qual['valid_until']}）\n\n"
                f"*请将 {matched_qual['name']} 扫描件附在本页之后。*\n"
            )
            return "\n".join(content_parts)

        if hints:
            content_parts.append(f"> ⚠️ 本章节需要提供资质文件：\n\n**招标要求**：{hints}\n")
        if data_fields:
            content_parts.append("**需要提供的材料**：\n")
            for field in data_fields:
                content_parts.append(f"- [ ] {field} [待补充：{field}]")
        else:
            content_parts.append(f"- [ ] {title} [待补充：{title}]")

        content_parts.append("\n*请将相关证书扫描件附在投标文件相应位置。*")
        return "\n".join(content_parts)

    # ── Data-driven generation: Team & Project ──

    def _generate_team_narrative(self, title: str, hints: str,
                                  resumes: List[Dict], company_info: str,
                                  content_outline: List = None) -> str:
        """Generate team/personnel section from real resume data."""
        parts = []

        # Opening paragraph
        parts.append(
            f"为确保本项目高效、专业地推进，我方特组建了一支由 {len(resumes)} 名"
            f"专业人员组成的项目团队，涵盖项目管理、专业技术等多个维度。"
            f"团队成员均具备丰富的相关领域从业经验，能够为本项目提供全方位的专业服务。\n"
        )

        # Overview table
        parts.append("### 项目团队概况\n")
        parts.append("| 序号 | 姓名 | 职务/职称 | 学历 | 从业年限 | 项目角色 |")
        parts.append("|------|------|----------|------|---------|---------|")
        for i, r in enumerate(resumes, 1):
            name = r.get("name", "")
            title_r = r.get("title", "") or ""
            edu = r.get("education", "") or ""
            years = r.get("years_of_practice", "") or ""
            role = r.get("role_in_project", "") or ""
            parts.append(f"| {i} | {name} | {title_r} | {edu} | {years}年 | {role} |")
        parts.append("")

        # Detailed bios
        parts.append("### 核心成员介绍\n")
        for i, r in enumerate(resumes, 1):
            name = r.get("name", "")
            title_r = r.get("title", "") or ""
            bio = r.get("brief_bio", "") or ""
            specialty = r.get("specialty", "") or ""
            cases = r.get("representative_cases", [])
            license_num = r.get("license_number", "") or ""

            parts.append(f"**{i}. {name}　{title_r}**\n")
            if bio:
                parts.append(f"{bio}\n")
            if specialty:
                parts.append(f"- **专业领域**：{specialty}")
            if license_num:
                parts.append(f"- **执业证号**：{license_num}")
            if r.get("years_of_practice"):
                parts.append(f"- **从业年限**：{r['years_of_practice']}年")
            if r.get("education"):
                parts.append(f"- **学历**：{r['education']}")

            if cases:
                parts.append(f"\n**代表性项目/案例**：")
                for j, c in enumerate(cases[:5], 1):
                    case_name = c.get("name", c) if isinstance(c, dict) else str(c)
                    parts.append(f"  {j}. {case_name}")

            # Image placeholder
            images = r.get("_images", [])
            if images:
                # Count image files (support both flat and typed format)
                img_count = len(images)
                parts.append(f"\n> 📎 附件：{name} 资质证书（{img_count}份）")
            parts.append("")

        return "\n".join(parts)

    def _generate_project_narrative(self, title: str, hints: str,
                                     projects: List[Dict], company_info: str,
                                     content_outline: List = None) -> str:
        """Generate project history/performance section from real project data."""
        parts = []

        # Opening paragraph
        parts.append(
            f"我方在相关领域具有丰富的项目实施经验。"
            f"以下为我方近年来承接的 {len(projects)} 个代表性项目，"
            f"充分证明了我方在同类项目中的服务能力和履约实力。\n"
        )

        # Summary table
        parts.append("### 项目业绩一览\n")
        parts.append("| 序号 | 项目名称 | 委托方/客户 | 合同金额(元) | 服务期限 |")
        parts.append("|------|---------|-----------|------------|---------|")
        for i, p in enumerate(projects, 1):
            pname = p.get("project_name", "") or ""
            client = p.get("client", "") or ""
            amount = p.get("amount", p.get("contract_amount", "")) or ""
            # Format amount
            try:
                amount_num = float(str(amount).replace(",", ""))
                if amount_num >= 10000:
                    amount = f"{amount_num/10000:.1f}万"
                else:
                    amount = f"{amount_num:.0f}"
            except (ValueError, TypeError):
                pass
            period = p.get("period", "") or ""
            # Truncate long names
            if len(pname) > 30:
                pname = pname[:28] + "..."
            parts.append(f"| {i} | {pname} | {client} | {amount} | {period} |")
        parts.append("")

        # Detailed case studies
        parts.append("### 代表性项目详情\n")
        for i, p in enumerate(projects, 1):
            pname = p.get("project_name", "") or ""
            parts.append(f"**案例{i}：{pname}**\n")

            client = p.get("client", "")
            ptype = p.get("project_type", "")
            amount = p.get("amount", p.get("contract_amount", ""))
            period = p.get("period", "")
            desc = p.get("description", "")
            outcome = p.get("outcome", "")

            if client:
                parts.append(f"- **委托方/客户**：{client}")
            if ptype:
                parts.append(f"- **项目类型**：{ptype}")
            if amount:
                parts.append(f"- **合同金额**：{amount}元")
            if period:
                parts.append(f"- **服务期限**：{period}")
            if desc:
                parts.append(f"- **项目概况**：{desc}")
            if outcome:
                parts.append(f"- **项目成果**：{outcome}")

            # Image references
            images = p.get("_images", [])
            if images:
                parts.append(f"\n> 📎 附件：项目证明材料（{len(images)}份）")
            parts.append("")

        return "\n".join(parts)



    @staticmethod
    def _scan_missing(content: str) -> List[str]:
        import re
        return re.findall(r'\[待补充[：:]?([^\]]*)\]', content)

    @staticmethod
    def _result(title: str, content: str, missing: List[str], status: str) -> Dict:
        return {
            "title": title,
            "content": content,
            "missing_fields": missing,
            "status": status,
        }
