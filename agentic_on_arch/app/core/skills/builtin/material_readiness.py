"""Material Readiness Checker — 投标材料完整性检查

解析招标文件的评分标准中的材料要求，逐项检查素材库是否齐全。
结果用于投标前预检，防止因缺少材料导致废标或丢分。
"""
import json
import logging
import re
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# ── 材料关键词 → 检查规则映射 ──
# 每条规则: keyword_pattern, check_type, check_target, description
MATERIAL_CHECKS = [
    # 律所级材料
    {
        "keywords": ["律所简介", "基本情况"],
        "check": "firm_profile",
        "target": "qualifications",
        "description": "律所简介/基本情况表",
        "severity": "required",
    },
    {
        "keywords": ["财务审计报告", "审计报告"],
        "check": "firm_audit",
        "target": "qualifications",
        "entity_type": "firm_audit",
        "description": "财务审计报告",
        "severity": "required",
        "recent_years": 2,  # 通常要求近2-3年
    },
    {
        "keywords": ["执业许可证", "律师事务所执业许可"],
        "check": "firm_license",
        "target": "qualifications",
        "entity_type": "firm_license",
        "description": "律所执业许可证",
        "severity": "required",
    },
    {
        "keywords": ["荣誉奖项", "荣誉"],
        "check": "awards",
        "target": "qualifications",
        "entity_type_in": ["award", "ranking", "ranking_proof"],
        "description": "荣誉奖项/行业排名证明",
        "severity": "scoring",
    },
    {
        "keywords": ["钱伯斯", "Chambers", "榜单排名", "排名"],
        "check": "rankings",
        "target": "qualifications",
        "entity_type_in": ["ranking", "ranking_proof"],
        "description": "行业榜单排名证明",
        "severity": "scoring",
    },
    {
        "keywords": ["处罚", "行政处罚", "行业处分", "承诺书"],
        "check": "compliance",
        "target": "qualifications",
        "description": "处罚/合规承诺书",
        "severity": "required",
    },
    {
        "keywords": ["诚信信息公示平台", "诚信信息"],
        "check": "integrity_check",
        "target": "qualifications",
        "description": "全国律师执业诚信信息公示平台截图",
        "severity": "required",
    },
    # 人员级材料
    {
        "keywords": ["学历证", "学历证书", "学历"],
        "check": "education_cert",
        "target": "resumes",
        "per_person": True,
        "image_keyword": "学历",
        "description": "学历证书扫描件",
        "severity": "required",
    },
    {
        "keywords": ["执业资格证书", "执业资格证", "执业证"],
        "check": "practice_cert",
        "target": "resumes",
        "per_person": True,
        "image_keyword": "执业",
        "description": "律师执业资格证书扫描件",
        "severity": "required",
    },
    {
        "keywords": ["社保缴费证明", "社保证明", "社保缴费", "社保"],
        "check": "social_security",
        "target": "resumes",
        "per_person": True,
        "image_keyword": "社保",
        "description": "社保缴费证明",
        "severity": "required",
    },
    {
        "keywords": ["身份证"],
        "check": "id_card",
        "target": "resumes",
        "per_person": True,
        "image_keyword": "身份证",
        "description": "身份证扫描件",
        "severity": "optional",
    },
    # 业绩级材料
    {
        "keywords": ["服务合同", "业绩情况表", "项目业绩", "证明材料"],
        "check": "project_evidence",
        "target": "projects",
        "description": "项目业绩证明材料(合同扫描件等)",
        "severity": "scoring",
    },
    # 保证金
    {
        "keywords": ["投标保证金"],
        "check": "bid_bond",
        "target": "qualifications",
        "entity_type": "financial_proof",
        "description": "投标保证金缴纳证明",
        "severity": "required",
    },
]


class MaterialReadinessChecker:
    """Check material completeness against tender requirements."""

    def __init__(self, material_store):
        self.store = material_store

    def check_readiness(
        self,
        evaluation_criteria: List[Dict],
        company: str = "",
        team_members: List[str] = None,
    ) -> Dict:
        """Run completeness check against evaluation criteria.
        
        Returns:
            {
                "overall_status": "incomplete" | "complete" | "warning",
                "score": 85,  # percentage of required items present
                "total_checks": 12,
                "passed": 10,
                "failed": 1,
                "warnings": 1,
                "items": [
                    {
                        "description": "财务审计报告",
                        "status": "pass" | "fail" | "warning",
                        "severity": "required" | "scoring" | "optional",
                        "detail": "找到2份: 2023年, 2024年",
                        "scoring_item": "综合实力",
                        "max_score": 40,
                    },
                    ...
                ]
            }
        """
        # Collect all material_evidence text
        all_evidence_text = []
        evidence_to_criteria = {}  # evidence_text -> {item, max_score}
        
        for criterion in evaluation_criteria:
            evidence = criterion.get("material_evidence", "")
            if evidence:
                all_evidence_text.append(evidence)
                evidence_to_criteria[evidence] = {
                    "item": criterion.get("item", ""),
                    "max_score": criterion.get("max_score", 0),
                }

        # Determine which checks are needed
        needed_checks = []
        for check_rule in MATERIAL_CHECKS:
            for evidence in all_evidence_text:
                if any(kw in evidence for kw in check_rule["keywords"]):
                    # Find which criterion triggered this
                    criteria_info = evidence_to_criteria.get(evidence, {})
                    needed_checks.append({
                        **check_rule,
                        "scoring_item": criteria_info.get("item", ""),
                        "max_score": criteria_info.get("max_score", 0),
                        "evidence_text": evidence,
                    })
                    break  # Don't double-add

        # Run each check
        results = []
        for check in needed_checks:
            result = self._run_check(check, company, team_members or [])
            results.append(result)

        # Calculate summary
        passed = sum(1 for r in results if r["status"] == "pass")
        failed = sum(1 for r in results if r["status"] == "fail")
        warnings = sum(1 for r in results if r["status"] == "warning")
        total = len(results)

        required_checks = [r for r in results if r["severity"] == "required"]
        required_passed = sum(1 for r in required_checks if r["status"] == "pass")
        required_total = len(required_checks)

        score = round(passed / total * 100) if total > 0 else 100

        if failed > 0 and any(r["status"] == "fail" and r["severity"] == "required" for r in results):
            overall = "incomplete"
        elif warnings > 0 or failed > 0:
            overall = "warning"
        else:
            overall = "complete"

        return {
            "overall_status": overall,
            "score": score,
            "total_checks": total,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "required_status": f"{required_passed}/{required_total}",
            "items": results,
        }

    def _run_check(self, check: Dict, company: str, team_members: List[str]) -> Dict:
        """Run a single material check."""
        check_type = check.get("check", "")
        result = {
            "description": check.get("description", ""),
            "severity": check.get("severity", "optional"),
            "scoring_item": check.get("scoring_item", ""),
            "max_score": check.get("max_score", 0),
            "status": "fail",
            "detail": "",
        }

        conn = self.store._get_conn()
        try:
            company_id = self._get_company_id(conn, company)
            if not company_id:
                result["detail"] = f"未找到公司: {company}"
                return result

            if check_type == "firm_audit":
                result = self._check_firm_audit(conn, company_id, check, result)
            elif check_type in ("awards", "rankings"):
                result = self._check_by_entity_type(conn, company_id, check, result)
            elif check_type in ("firm_license", "bid_bond"):
                result = self._check_by_entity_type(conn, company_id, check, result)
            elif check_type == "firm_profile":
                result = self._check_firm_profile(conn, company_id, result)
            elif check_type in ("compliance", "integrity_check"):
                result = self._check_compliance(conn, company_id, check_type, result)
            elif check_type in ("education_cert", "practice_cert", "social_security", "id_card"):
                result = self._check_per_person(conn, company_id, check, team_members, result)
            elif check_type == "project_evidence":
                result = self._check_project_evidence(conn, company_id, result)
            else:
                result["detail"] = "未知检查类型"
                result["status"] = "warning"
        finally:
            conn.close()

        return result

    def _get_company_id(self, conn, company: str) -> Optional[int]:
        row = conn.execute(
            "SELECT id FROM companies WHERE name = ?", (company,)
        ).fetchone()
        return row["id"] if row else None

    def _check_firm_audit(self, conn, company_id: int, check: Dict, result: Dict) -> Dict:
        """Check for financial audit reports."""
        rows = conn.execute(
            "SELECT name FROM materials WHERE company_id = ? AND category = 'qualifications' AND entity_type = 'firm_audit'",
            (company_id,),
        ).fetchall()

        if rows:
            names = [r["name"] for r in rows]
            # Check which years are covered
            years = []
            for name in names:
                year_match = re.search(r'20\d{2}', name)
                if year_match:
                    years.append(year_match.group())

            result["status"] = "pass"
            result["detail"] = f"找到{len(rows)}份: {', '.join(names[:3])}"
            if years:
                result["detail"] += f" (年份: {', '.join(sorted(years))})"

            # Warn if missing recent years
            import datetime
            current_year = datetime.datetime.now().year
            expected_years = [str(current_year - i) for i in range(1, 3)]
            missing_years = [y for y in expected_years if y not in years]
            if missing_years:
                result["status"] = "warning"
                result["detail"] += f" ⚠️ 可能缺少: {', '.join(missing_years)}年"
        else:
            result["status"] = "fail"
            result["detail"] = "未找到财务审计报告"

        return result

    def _check_by_entity_type(self, conn, company_id: int, check: Dict, result: Dict) -> Dict:
        """Check for materials by entity_type."""
        entity_type = check.get("entity_type", "")
        entity_types = check.get("entity_type_in", [entity_type] if entity_type else [])

        if not entity_types:
            result["status"] = "warning"
            result["detail"] = "无法检查"
            return result

        placeholders = ",".join(["?"] * len(entity_types))
        rows = conn.execute(
            f"SELECT name, entity_type FROM materials WHERE company_id = ? AND category = 'qualifications' AND entity_type IN ({placeholders})",
            [company_id] + entity_types,
        ).fetchall()

        if rows:
            result["status"] = "pass"
            names = [r["name"] for r in rows[:3]]
            extra = f" ...等{len(rows)}项" if len(rows) > 3 else ""
            result["detail"] = f"找到{len(rows)}项: {', '.join(names)}{extra}"
        else:
            result["status"] = "fail"
            result["detail"] = f"未找到 (需要: {check.get('description', '')})"

        return result

    def _check_firm_profile(self, conn, company_id: int, result: Dict) -> Dict:
        """Check for firm profile/introduction."""
        # Firm profile might be in qualifications or can be generated
        rows = conn.execute(
            "SELECT name FROM materials WHERE company_id = ? AND category = 'qualifications' AND (name LIKE '%简介%' OR name LIKE '%基本情况%' OR entity_type = 'firm_profile')",
            (company_id,),
        ).fetchall()

        if rows:
            result["status"] = "pass"
            result["detail"] = f"找到: {rows[0]['name']}"
        else:
            # Can be auto-generated from company info
            result["status"] = "warning"
            result["detail"] = "未找到独立的律所简介文件，系统将自动生成"

        return result

    def _check_compliance(self, conn, company_id: int, check_type: str, result: Dict) -> Dict:
        """Check for compliance/integrity documents."""
        if check_type == "compliance":
            keywords = ["%承诺书%", "%处罚%", "%合规%"]
        else:
            keywords = ["%诚信%", "%公示平台%"]

        conditions = " OR ".join(["name LIKE ?" for _ in keywords])
        rows = conn.execute(
            f"SELECT name FROM materials WHERE company_id = ? AND category = 'qualifications' AND ({conditions})",
            [company_id] + keywords,
        ).fetchall()

        if rows:
            result["status"] = "pass"
            result["detail"] = f"找到: {rows[0]['name']}"
        else:
            # Check if there's a form template that will generate this
            result["status"] = "warning"
            result["detail"] = "未找到独立文件，系统将从模板自动生成承诺书/声明"

        return result

    def _check_per_person(self, conn, company_id: int, check: Dict, team_members: List[str], result: Dict) -> Dict:
        """Check per-person documents (education cert, practice cert, social security)."""
        image_keyword = check.get("image_keyword", "")

        # Get all resumes if no specific team members
        if not team_members:
            rows = conn.execute(
                "SELECT name, data FROM materials WHERE company_id = ? AND category = 'resumes'",
                (company_id,),
            ).fetchall()
            team_members = [r["name"] for r in rows
                          if not any(skip in r["name"] for skip in ["公示平台", "执业许可", "资格证"])]

        if not team_members:
            result["status"] = "warning"
            result["detail"] = "无团队成员数据"
            return result

        # Check which team members have the required document
        has_doc = []
        missing_doc = []

        for member in team_members:
            # Check in image_meta or qualifications
            found = False

            # Check qualifications
            qual_rows = conn.execute(
                "SELECT name FROM materials WHERE company_id = ? AND category = 'qualifications' AND name LIKE ?",
                (company_id, f"%{member}%{image_keyword}%" if image_keyword else f"%{member}%"),
            ).fetchall()
            if qual_rows:
                found = True

            # Check in resume images (stored in materials data → _images)
            if not found and image_keyword:
                resume_row = conn.execute(
                    "SELECT data FROM materials WHERE company_id = ? AND category = 'resumes' AND name = ?",
                    (company_id, member),
                ).fetchone()
                if resume_row:
                    data = json.loads(resume_row["data"]) if resume_row["data"] else {}
                    images = data.get("_images", [])
                    for img in images:
                        if image_keyword in str(img):
                            found = True
                            break

            if found:
                has_doc.append(member)
            else:
                missing_doc.append(member)

        # Limit check to core team (first 8 members)
        core_team = team_members[:8]
        core_missing = [m for m in missing_doc if m in core_team]

        if not core_missing:
            result["status"] = "pass"
            result["detail"] = f"核心团队{len(core_team)}人全部具备"
        elif len(core_missing) <= 2:
            result["status"] = "warning"
            result["detail"] = f"核心团队{len(core_team)}人中{len(core_missing)}人缺失: {', '.join(core_missing[:3])}"
        else:
            result["status"] = "fail"
            result["detail"] = f"核心团队{len(core_team)}人中{len(core_missing)}人缺失: {', '.join(core_missing[:5])}"

        return result

    def _check_project_evidence(self, conn, company_id: int, result: Dict) -> Dict:
        """Check project evidence (contracts, etc.)."""
        rows = conn.execute(
            "SELECT name, data FROM materials WHERE company_id = ? AND category = 'projects'",
            (company_id,),
        ).fetchall()

        if not rows:
            result["status"] = "fail"
            result["detail"] = "未找到项目业绩数据"
            return result

        # Check how many projects have contract images
        has_images = 0
        for r in rows:
            data = json.loads(r["data"]) if r["data"] else {}
            if data.get("_images"):
                has_images += 1

        total = len(rows)
        if has_images >= min(total, 10):
            result["status"] = "pass"
            result["detail"] = f"{total}个项目, {has_images}个有合同扫描件"
        elif has_images > 0:
            result["status"] = "warning"
            result["detail"] = f"{total}个项目, 仅{has_images}个有合同扫描件 (建议≥10个)"
        else:
            result["status"] = "warning"
            result["detail"] = f"有{total}个项目记录，但均无合同扫描件"

        return result
