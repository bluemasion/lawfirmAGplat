"""Material matcher — match materials from the store to bid sections.

Given a section's `material_refs` and `type`, finds the most relevant
materials (resumes, projects, qualifications, narratives) from the
MaterialStore.  Used by content_generation to inject real data into
bid document sections.
"""

from typing import Any, Dict, List, Optional
import re
from app.utils.logger import logger


# ── Type detection keywords ──
_RESUME_KWS = ['简历', '人员', '团队', '律师', '顾问', '成员', '项目经理',
                '项目负责人', '拟投入', '拟委派', '配置人员']
_PROJECT_KWS = ['业绩', '项目', '案例', '合同', '经验', '履约', '类似']
_QUAL_KWS = ['资质', '证书', '执照', '许可', '认证', '荣誉', '信用']
_NARRATIVE_KWS = ['方案', '计划', '措施', '保障', '承诺', '介绍', '概述']


def _detect_material_type(ref_text: str) -> str:
    """Detect which material category a material_ref describes."""
    for kw in _RESUME_KWS:
        if kw in ref_text:
            return 'resume'
    for kw in _PROJECT_KWS:
        if kw in ref_text:
            return 'project'
    for kw in _QUAL_KWS:
        if kw in ref_text:
            return 'qualification'
    for kw in _NARRATIVE_KWS:
        if kw in ref_text:
            return 'narrative'
    return 'unknown'


def _extract_count(ref_text: str) -> Optional[int]:
    """Extract requested count from text like '3-5人' or '5项以上'."""
    m = re.search(r'(\d+)\s*[-~至]\s*(\d+)', ref_text)
    if m:
        return int(m.group(2))  # use upper bound
    m = re.search(r'(\d+)\s*[人项个名条份]', ref_text)
    if m:
        return int(m.group(1))
    return None


def _extract_filter_keywords(ref_text: str) -> List[str]:
    """Extract filtering keywords like '高级职称', '信息化'."""
    # Common qualification/filter terms
    FILTER_TERMS = [
        '高级', '中级', '初级', '合伙人', '主任', '资深',
        '信息化', '数据', '软件', '网络', '安全', '云计算',
        '法律', '金融', '建设', '工程', '设计', '咨询',
        '近三年', '近3年', '近五年', '近5年',
    ]
    return [t for t in FILTER_TERMS if t in ref_text]


class MaterialMatcher:
    """Match materials from the store to bid sections based on material_refs."""

    def __init__(self, store):
        """
        Args:
            store: MaterialStore instance
        """
        self.store = store

    def match_for_section(self, section: dict, company: str = "",
                          project_id: int = None) -> dict:
        """Match materials for a single bid section.

        Args:
            section: Dict with title, type, material_refs, content_outline
            company: Company name to filter materials by

        Returns:
            Dict with matched materials:
            {
                "resumes": [...],
                "projects": [...],
                "qualifications": [...],
                "narratives": [...],
                "match_summary": "简历3人 | 业绩5项"
            }
        """
        material_refs = section.get("material_refs", [])
        title = section.get("title", "")
        sec_type = section.get("type", "narrative")

        result = {
            "resumes": [],
            "projects": [],
            "qualifications": [],
            "narratives": [],
            "match_summary": "",
        }

        if not material_refs and sec_type == "narrative":
            # For narrative sections without explicit refs, try title-based matching
            material_refs = [title]

        for ref in material_refs:
            mat_type = _detect_material_type(ref)
            count = _extract_count(ref)
            filters = _extract_filter_keywords(ref)

            if mat_type == 'resume':
                matched = self._match_resumes(ref, filters, count, company, project_id)
                result["resumes"].extend(matched)
            elif mat_type == 'project':
                matched = self._match_projects(ref, filters, count, company, project_id)
                result["projects"].extend(matched)
            elif mat_type == 'qualification':
                matched = self._match_qualifications(ref, filters, count, company, project_id)
                result["qualifications"].extend(matched)
            elif mat_type == 'narrative':
                # narrative refs are informational, no direct material match
                pass

        # Deduplicate by name
        result["resumes"] = _dedup_by_key(result["resumes"], "name")
        result["projects"] = _dedup_by_key(result["projects"], "project_name")
        result["qualifications"] = _dedup_by_key(result["qualifications"], "name")

        # Build summary
        parts = []
        if result["resumes"]:
            parts.append(f"简历{len(result['resumes'])}人")
        if result["projects"]:
            parts.append(f"业绩{len(result['projects'])}项")
        if result["qualifications"]:
            parts.append(f"资质{len(result['qualifications'])}项")
        result["match_summary"] = " | ".join(parts) if parts else ""

        if result["match_summary"]:
            logger.info(f"  MaterialMatcher [{title}]: {result['match_summary']}")

        return result

    # Keywords indicating a record is a document/file, not a real person
    _NON_PERSON_KEYWORDS = [
        '身份证', '学历', '毕业证', '学位证', '实习证', '执业证', '资格证',
        '社保', '证书', '许可证', '平台', '律师事务所', '副本', '扫描件',
        '法律职业', '信息公示',
    ]

    @classmethod
    def _is_person_name(cls, name):
        """Check if a material name looks like a real person name."""
        if not name or len(name) < 2:
            return False
        # Names starting with digits are file names like "1. 身份证-钟雨"
        if name[0].isdigit():
            return False
        # Names containing document keywords
        if any(kw in name for kw in cls._NON_PERSON_KEYWORDS):
            return False
        # Real Chinese names are typically 2-4 chars
        if len(name) > 6:
            return False
        return True

    def _match_resumes(self, ref: str, filters: List[str],
                       count: Optional[int], company: str,
                       project_id: int = None) -> List[dict]:
        """Match resumes from store, prioritizing people with images and seniority."""
        all_resumes = self.store.get_resumes(company=company, project_id=project_id)
        if not all_resumes:
            return []

        # Filter out non-person records (file names like "身份证扫描件-钟雨")
        all_resumes = [r for r in all_resumes if self._is_person_name(r.get('name', ''))]

        # Apply keyword filters
        if filters:
            filtered = []
            for r in all_resumes:
                text = ' '.join([
                    r.get('name', '') or '', r.get('title', '') or '',
                    r.get('specialty', '') or '', r.get('brief_bio', '') or '',
                    str(r.get('years_of_practice', '') or ''),
                ])
                if any(f in text for f in filters):
                    filtered.append(r)
            if filtered:
                all_resumes = filtered

        # ── Smart sort: images first → seniority → years ──
        _TITLE_RANK = {
            '高级合伙人': 0, '管理合伙人': 0, '首席合伙人': 0,
            '合伙人': 1, '高级顾问': 2,
            '资深律师': 3, '律师': 4,
        }

        def _sort_key(r):
            # 1. Has images (more is better)
            img_count = len(r.get('_images', []))
            # 2. Title seniority (lower rank number = more senior)
            title = r.get('title', '') or ''
            title_rank = 9  # default for unknown titles
            for t, rank in _TITLE_RANK.items():
                if t in title:
                    title_rank = rank
                    break
            # 3. Years of practice
            years = 0
            try:
                years = int(r.get('years_of_practice') or 0)
            except (ValueError, TypeError):
                pass
            return (-img_count, title_rank, -years)

        all_resumes.sort(key=_sort_key)

        limit = count or 8
        matched = all_resumes[:limit]

        # ── Enrich: merge images from separate named records ──
        # Some images live in separate records like "身份证扫描件-钟雨"
        # rather than on the resume "钟雨" itself. Find and merge them.
        self._enrich_resume_images(matched, company, project_id)

        return matched

    def _enrich_resume_images(self, resumes, company, project_id=None):
        """Find images from other material records that contain the person's
        name and merge them into the resume's _images list."""
        # Get ALL materials (resumes + qualifications) to search for name matches
        all_resumes = self.store.get_resumes(company=company, project_id=project_id)
        all_quals = self.store.get_qualifications(company=company, project_id=project_id)
        all_records = list(all_resumes or []) + list(all_quals or [])

        for resume in resumes:
            person_name = (resume.get('name') or '').strip()
            if not person_name or len(person_name) < 2:
                continue

            # Build set of existing image files for dedup
            existing_files = set()
            for img in resume.get('_images', []):
                f = img.get('file', img) if isinstance(img, dict) else img
                existing_files.add(f)

            added = []

            # Search all records for ones containing this person's name
            for record in all_records:
                record_name = (record.get('name') or '').strip()
                if not record_name or record_name == person_name:
                    continue

                # Check if person's name appears in the record name
                if person_name in record_name:
                    for img in record.get('_images', []):
                        img_file = img.get('file', img) if isinstance(img, dict) else img
                        if img_file not in existing_files:
                            existing_files.add(img_file)
                            added.append(img)

            if added:
                current = list(resume.get('_images', []))
                current.extend(added)
                resume['_images'] = current
                logger.info(
                    f"  Enriched '{person_name}': +{len(added)} images "
                    f"from related records → {len(current)} total"
                )

    def _match_projects(self, ref: str, filters: List[str],
                        count: Optional[int], company: str,
                        project_id: int = None) -> List[dict]:
        """Match projects from store."""
        all_projects = self.store.get_projects(company=company, project_id=project_id)
        if not all_projects:
            return []

        if filters:
            filtered = []
            for p in all_projects:
                text = ' '.join([
                    p.get('project_name', '') or '', p.get('project_type', '') or '',
                    p.get('description', '') or '', p.get('client', '') or '',
                ])
                if any(f in text for f in filters):
                    filtered.append(p)
            if filtered:
                all_projects = filtered

        limit = count or 6
        return all_projects[:limit]

    def _match_qualifications(self, ref: str, filters: List[str],
                              count: Optional[int], company: str,
                              project_id: int = None) -> List[dict]:
        """Match qualifications from store, with entity_type smart routing.

        Routes based on ref/filter context:
        - 荣誉/奖项/排名 → award + ranking + ranking_proof
        - 资格审查/执照/许可 → firm_license + firm_audit + financial_proof
        - Other → all qualifications
        """
        # Determine entity_type filter from ref and filter keywords
        context = f"{ref} {' '.join(filters)}"
        entity_type_filter = ""

        # Honor/award context → only awards and rankings with evidence
        _AWARD_KW = ['荣誉', '奖项', '排名', '榜单', 'ALB', '钱伯斯',
                     'Legal 500', 'LEGALBAND', 'IFLR', '表彰']
        # Qualification/license context → firm-level docs
        _LICENSE_KW = ['资格审查', '营业执照', '执业许可', '执照', '许可证',
                       '审计', '财务']

        if any(kw in context for kw in _AWARD_KW):
            entity_type_filter = "award,ranking,ranking_proof"
        elif any(kw in context for kw in _LICENSE_KW):
            entity_type_filter = "firm_license,firm_audit,financial_proof"

        all_quals = self.store.get_qualifications(
            company=company, project_id=project_id,
            entity_type=entity_type_filter
        )
        if not all_quals:
            return []

        # Additional keyword filter if specified
        if filters:
            filtered = []
            for q in all_quals:
                text = ' '.join([
                    q.get('name', '') or '', q.get('issuer', '') or '',
                    q.get('type', '') or '',
                ])
                if any(f in text for f in filters):
                    filtered.append(q)
            if filtered:
                all_quals = filtered

        # Prioritize items with images
        all_quals.sort(key=lambda q: -len(q.get('_images', [])))

        limit = count or 10
        if entity_type_filter:
            logger.info(
                f"  Qualification filter: entity_type={entity_type_filter} "
                f"→ {len(all_quals)} matches"
            )
        return all_quals[:limit]


def _dedup_by_key(items: List[dict], key: str) -> List[dict]:
    """Deduplicate list of dicts by a key field."""
    seen = set()
    result = []
    for item in items:
        k = item.get(key, '')
        if k and k in seen:
            continue
        seen.add(k)
        result.append(item)
    return result


def format_materials_for_prompt(matched: dict) -> str:
    """Format matched materials into a text block for LLM prompt injection.

    Returns a string ready to be appended to the LLM prompt.
    """
    parts = []

    resumes = matched.get("resumes", [])
    if resumes:
        parts.append("【素材库：人员简历数据（请使用真实信息，不要编造）】")
        for r in resumes:
            line = f"- {r.get('name', '?')}"
            if r.get('title'):
                line += f", {r['title']}"
            if r.get('years_of_practice'):
                line += f", 执业{r['years_of_practice']}年"
            if r.get('specialty'):
                line += f", 擅长{r['specialty']}"
            cases = r.get('representative_cases', [])
            if cases:
                case_strs = [str(c.get('name', c)) if isinstance(c, dict) else str(c)
                             for c in cases[:3]]
                line += f", 代表案例: {'; '.join(case_strs)}"
            parts.append(line)

    projects = matched.get("projects", [])
    if projects:
        parts.append("\n【素材库：项目业绩数据（请使用真实信息，不要编造）】")
        for p in projects:
            line = f"- {p.get('project_name', '?')}"
            if p.get('client'):
                line += f", 委托方: {p['client']}"
            if p.get('contract_amount') or p.get('amount'):
                line += f", 金额: {p.get('contract_amount', p.get('amount', '?'))}"
            if p.get('description'):
                line += f", {p['description'][:60]}"
            parts.append(line)

    quals = matched.get("qualifications", [])
    if quals:
        parts.append("\n【素材库：资质证书数据（请使用真实信息，不要编造）】")
        for q in quals:
            line = f"- {q.get('name', '?')}"
            if q.get('number'):
                line += f", 编号: {q['number']}"
            if q.get('issuer'):
                line += f", 颁发: {q['issuer']}"
            if q.get('valid_until'):
                line += f", 有效期至: {q['valid_until']}"
            parts.append(line)

    return "\n".join(parts) if parts else ""
