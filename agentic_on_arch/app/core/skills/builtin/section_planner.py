"""
SectionPlannerSkill — Build section list from tender attachment list.

Instead of letting the LLM freely decide what sections to generate,
this skill uses the tender's Chapter 6 attachment list as the
definitive section structure.

This ensures:
1. Section list exactly matches tender requirements
2. No spurious sections (like "价格偏离表" when tender doesn't have it)
3. Correct attachment numbering and ordering
4. Works with ANY tender document (reads attachments dynamically)
"""

import logging
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


# ─── Content type detection ──────────────────────────────────────
# These keywords are industry-universal across tender documents.
# Order matters: first match wins.

_TYPE_RULES = [
    # Form types (template filling, no LLM needed)
    (['投标函'], 'form'),
    (['授权书', '授权委托'], 'form'),
    (['投标保证金', '保证金'], 'form'),
    (['承诺书', '代理服务费'], 'form'),

    # Table types (structured tables)
    (['评标索引', '索引表'], 'table'),
    (['投标一览', '一览表', '报价一览'], 'table'),
    (['商务条款', '商务偏离', '商务响应'], 'table'),
    (['技术条款', '技术偏离', '技术响应'], 'table'),
    (['价格偏离', '价格响应'], 'table'),
    (['投标人情况'], 'table'),
    (['拟派实施人员', '实施人员表'], 'table'),
    (['拟派人员资历', '人员资历表'], 'table'),
    (['投标报价', '报价表', '开标一览'], 'table'),

    # Qualification types (material matching)
    (['业绩清单', '业绩证明'], 'qualification'),
    (['营业执照'], 'qualification'),
    (['法定代表人身份', '法人身份'], 'qualification'),
    (['投标人代表身份', '授权代表身份'], 'qualification'),
    (['资质证书', '认证体系', '资质及认证'], 'qualification'),
    (['社保缴费', '社保证明'], 'qualification'),
    (['财务报表', '审计报告'], 'qualification'),

    # Narrative types (LLM generation needed)
    (['服务方案', '服务响应', '详细的服务'], 'narrative'),
    (['技术方案', '实施方案'], 'narrative'),
    (['项目团队', '团队配置', '人员配置'], 'narrative'),
]


def detect_content_type(title: str) -> str:
    """Detect section content type from attachment title.

    Returns: 'form', 'table', 'narrative', or 'qualification'
    """
    for keywords, content_type in _TYPE_RULES:
        for kw in keywords:
            if kw in title:
                return content_type
    # Default: narrative (LLM will generate)
    return 'narrative'


def clean_attachment_title(raw_title: str) -> str:
    """Clean attachment title — remove trailing text after title.

    Example:
        "投标一览表中内容进行报价；" → "投标一览表"
        "招标代理服务费承诺书）。招标代理..." → "招标代理服务费承诺书"
        "法定代表人（单位负责人）授权书" → kept intact
    """
    # Don't clean short titles — they're usually complete
    if len(raw_title) <= 15:
        return raw_title.strip()

    # Separators that indicate trailing text
    # Note: （ is only a separator if no matching ） follows nearby
    simple_seps = ['中内容', '）。', '）；', '。', '；', ',', '，']
    for sep in simple_seps:
        idx = raw_title.find(sep)
        if idx > 2:
            raw_title = raw_title[:idx]
            return raw_title.strip()

    # Handle （ only if no matching ）— means it's trailing text
    paren_idx = raw_title.find('（')
    if paren_idx > 2:
        close_idx = raw_title.find('）', paren_idx)
        if close_idx < 0:
            # No closing paren — it's trailing text
            raw_title = raw_title[:paren_idx]
        else:
            # Has matching ）— check if there's more text after ）
            after_close = raw_title[close_idx + 1:].strip()
            if len(after_close) > 10:
                # Long text after ）— might be trailing
                # Keep up to some reasonable endpoint
                for sep in ['。', '；', ',', '，']:
                    sep_idx = after_close.find(sep)
                    if sep_idx > 0:
                        raw_title = raw_title[:close_idx + 1 + sep_idx]
                        return raw_title.strip()

    return raw_title.strip()


# ─── Material reference generation ─────────────────────────────
# Maps attachment titles to material_refs that MaterialMatcher understands.

_MATERIAL_REF_MAP = {
    # Qualification type → qualification refs
    '业绩清单':       ['律所业绩', '项目业绩', '业绩证明材料'],
    '业绩证明':       ['律所业绩', '项目业绩', '业绩证明材料'],
    '营业执照':       ['营业执照副本'],
    '法定代表人':     ['法定代表人身份证'],
    '投标人代表':     ['投标人代表身份证'],
    '资质证书':       ['资质及认证体系证书复印件'],
    '认证体系':       ['资质及认证体系证书复印件'],
    '社保':           ['社保缴费证明'],
    '财务报表':       ['财务审计报告'],
    '荣誉':           ['荣誉奖项与排名'],
    '排名':           ['荣誉奖项与排名'],

    # Table type → data refs
    '投标人情况':     ['投标人情况表', '项目团队配置'],
    '拟派实施人员':   ['拟派实施人员表', '项目团队配置'],
    '拟派人员资历':   ['项目负责人资历', '拟派人员资历表'],

    # Narrative type → content refs
    '服务方案':       ['服务方案', '服务响应方案'],
    '服务响应':       ['服务方案', '服务响应方案'],
    '团队':           ['项目团队配置'],
    '人员配置':       ['项目团队配置'],
}


def _build_material_refs(title: str, content_type: str) -> List[str]:
    """Build material_refs for a section based on its title and type.

    These refs are used by MaterialMatcher to find relevant materials
    from the material store.
    """
    refs = []

    # Match from keyword map
    for kw, kw_refs in _MATERIAL_REF_MAP.items():
        if kw in title:
            refs.extend(kw_refs)

    # Always add the title itself as a ref (for fallback matching)
    if title not in refs:
        refs.append(title)

    return refs


def build_sections_from_attachments(
    format_spec: Dict,
    llm_sections: Optional[List[Dict]] = None,
    scoring_criteria: Optional[List[Dict]] = None,
) -> List[Dict]:
    """Build definitive section list from tender attachment list.

    Args:
        format_spec: The format_spec extracted from tender Chapter 6.
        llm_sections: Optional LLM-generated sections to merge content from.
        scoring_criteria: Optional scoring criteria for linking.

    Returns:
        List of section dicts matching the expected format:
        [{"title": ..., "type": ..., "order": ..., "att_id": ..., ...}]
    """
    attachments = format_spec.get("attachments", [])
    if not attachments:
        return llm_sections or []

    # Sort attachments by order
    sorted_atts = sorted(attachments, key=lambda a: a.get("order", 999))

    # Build LLM section lookup by title keywords for content merging
    llm_lookup = {}
    if llm_sections:
        for sec in llm_sections:
            llm_lookup[sec.get("title", "")] = sec

    sections = []
    for att in sorted_atts:
        att_id = att.get("id", "")
        raw_title = att.get("title", "")
        title = clean_attachment_title(raw_title)
        has_tables = bool(att.get("tables"))

        # Detect content type
        content_type = detect_content_type(title)

        # If attachment has cloned table templates, mark as table
        if has_tables and content_type not in ('table', 'qualification'):
            content_type = 'table'

        # Try to find matching LLM section for content
        matched_llm = _find_matching_llm_section(title, att_id, llm_lookup)

        # Build material_refs based on content type
        material_refs = _build_material_refs(title, content_type)

        # Build section
        section = {
            "title": title,
            "type": content_type,
            "order": att.get("order", 0),
            "level": 2,
            "att_id": att_id,
            "linked_scoring": [],
            "material_refs": material_refs,
        }

        # Merge LLM content if available
        if matched_llm:
            section["content"] = matched_llm.get("content", "")
            section["linked_scoring"] = matched_llm.get("linked_scoring", [])
            section["missing_fields"] = matched_llm.get("missing_fields", [])
            if matched_llm.get("status"):
                section["status"] = matched_llm["status"]
        else:
            section["content"] = ""

        # Link scoring criteria if available
        if scoring_criteria and not section.get("linked_scoring"):
            section["linked_scoring"] = _link_scoring(
                title, scoring_criteria
            )

        sections.append(section)
        logger.info(
            f"  Section: {att_id}：{title} → type={content_type}"
            f"{' (LLM content)' if matched_llm else ''}"
        )

    # Handle sub-sections: for 附件10 (投标人情况表), also include
    # related sub-sections from LLM (拟派实施人员表, 拟派人员资历表)
    _merge_sub_sections(sections, llm_sections or [])

    # Handle service-related sub-sections for 附件12
    _merge_service_sub_sections(sections, llm_sections or [])

    logger.info(
        f"SectionPlanner: {len(sections)} sections from "
        f"{len(sorted_atts)} attachments"
    )
    return sections


def _find_matching_llm_section(
    att_title: str,
    att_id: str,
    llm_lookup: Dict[str, Dict],
) -> Optional[Dict]:
    """Find LLM section that matches this attachment."""
    # Direct title match
    if att_title in llm_lookup:
        return llm_lookup.pop(att_title)

    # Keyword matching
    _match_map = {
        '评标索引':     ['评标索引'],
        '投标函':       ['投标函'],
        '投标一览':     ['投标一览', '报价一览', '报价'],
        '商务条款':     ['商务偏离', '商务评分偏离', '商务条款'],
        '技术条款':     ['技术偏离', '技术评分偏离', '技术条款'],
        '业绩清单':     ['业绩清单', '律所业绩', '业绩'],
        '授权书':       ['授权委托', '授权书'],
        '投标保证金':   ['投标保证金', '保证金'],
        '投标人情况':   ['投标人情况', '项目团队'],
        '代理服务费':   ['代理服务费', '承诺书'],
        '服务响应':     ['服务响应', '详细的服务', '服务方案'],
    }

    for kw, sec_kws in _match_map.items():
        if kw in att_title:
            for sec_title, sec in list(llm_lookup.items()):
                for skw in sec_kws:
                    if skw in sec_title:
                        return llm_lookup.pop(sec_title)

    # Fuzzy: check if any LLM section title is contained in att_title
    for sec_title, sec in list(llm_lookup.items()):
        if sec_title in att_title or att_title in sec_title:
            return llm_lookup.pop(sec_title)

    return None


def _merge_sub_sections(
    sections: List[Dict],
    llm_sections: List[Dict],
):
    """Merge sub-sections into parent attachment sections.

    E.g., 拟派实施人员表 and 拟派人员资历表 belong under 附件10.
    """
    # Find 附件10 index
    att10_idx = None
    for i, sec in enumerate(sections):
        if sec.get("att_id") == "附件10":
            att10_idx = i
            break

    if att10_idx is None:
        return

    # Find sub-sections from LLM
    sub_kws = ['拟派实施人员', '拟派人员资历', '其他资格']
    insert_after = att10_idx
    for llm_sec in llm_sections:
        title = llm_sec.get("title", "")
        if any(kw in title for kw in sub_kws):
            insert_after += 1
            sub_section = {
                "title": title,
                "type": llm_sec.get("type", "table"),
                "order": sections[att10_idx]["order"],
                "level": 3,  # sub-level
                "att_id": sections[att10_idx].get("att_id", ""),
                "content": llm_sec.get("content", ""),
                "linked_scoring": llm_sec.get("linked_scoring", []),
                "is_sub_section": True,
            }
            sections.insert(insert_after, sub_section)


def _merge_service_sub_sections(
    sections: List[Dict],
    llm_sections: List[Dict],
):
    """Create narrative sub-sections for service-type attachments.

    Always creates standard sub-sections (重点难点/响应承诺/增值服务)
    even if LLM didn't generate them — these are essential for
    content volume and scoring coverage.
    """
    # Find service attachment
    svc_idx = None
    for i, sec in enumerate(sections):
        title = sec.get("title", "")
        if '服务响应' in title or '详细的服务' in title or '服务方案' in title:
            svc_idx = i
            break

    if svc_idx is None:
        return

    parent = sections[svc_idx]

    # Standard sub-sections that should always exist for service proposals
    # (泛化: these apply to most industries — legal, IT, engineering)
    _STANDARD_SUBS = [
        {"title": "重点难点分析及应对措施", "material_scope": ["projects"]},
        {"title": "响应时间承诺及保障机制", "material_scope": []},
        {"title": "增值服务方案", "material_scope": ["projects", "resumes"]},
    ]

    # Build lookup of LLM-generated sub-sections
    llm_sub_lookup = {}
    for llm_sec in llm_sections:
        llm_title = llm_sec.get("title", "")
        for std in _STANDARD_SUBS:
            # Match by keyword overlap
            std_kws = std["title"].replace("及", " ").replace("方案", "").split()
            if any(kw in llm_title for kw in std_kws if len(kw) >= 2):
                llm_sub_lookup[std["title"]] = llm_sec
                break

    # Insert sub-sections after parent
    insert_after = svc_idx
    created = 0
    for std in _STANDARD_SUBS:
        insert_after += 1
        llm_match = llm_sub_lookup.get(std["title"])
        sub_section = {
            "title": llm_match.get("title", std["title"]) if llm_match else std["title"],
            "type": "narrative",
            "order": parent["order"],
            "level": 3,
            "att_id": parent.get("att_id", ""),
            "content": llm_match.get("content", "") if llm_match else "",
            "linked_scoring": llm_match.get("linked_scoring", []) if llm_match else [],
            "is_sub_section": True,
            "material_refs": _build_material_refs(std["title"], "narrative"),
        }
        sections.insert(insert_after, sub_section)
        created += 1
        src = "LLM" if llm_match else "standard"
        logger.info(f"  Sub-section: {std['title']} ({src})")

    if created:
        logger.info(f"  Service sub-sections: {created} created for '{parent['title']}'")



def _link_scoring(
    title: str,
    criteria: List[Dict],
) -> List[Dict]:
    """Link scoring criteria to section by keyword matching."""
    linked = []
    for c in criteria:
        c_name = c.get("name", "")
        # Simple keyword overlap check
        if any(kw in title for kw in c_name.split()) or \
           any(kw in c_name for kw in title):
            linked.append(c)
    return linked
