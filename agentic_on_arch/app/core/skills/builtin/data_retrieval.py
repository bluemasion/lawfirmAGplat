"""Data retrieval skill — retrieve company data from JSON data files for RAG."""

import json
import os
from typing import Any, Dict, List, Optional

from app.core.skills.base import BaseSkill
from app.utils.logger import logger


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "company")


def _load_json(filename: str) -> Dict:
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        logger.warning(f"Data file not found: {path}")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class DataRetrievalSkill(BaseSkill):
    """Retrieve structured company data from JSON files — acts as RAG data layer."""

    name = "data_retrieval"
    description = "从本地数据文件检索律所真实数据（公司信息、团队、业绩、资质）"

    async def execute(self, params: Dict[str, Any]) -> Any:
        action = params.get("action", "company_profile")

        if action == "company_profile":
            return self.get_company_profile()
        elif action == "team_for_project":
            return self.get_team_for_project(
                params.get("project_type", ""),
                params.get("count", 3),
            )
        elif action == "similar_projects":
            return self.get_similar_projects(
                params.get("industry", ""),
                params.get("count", 3),
            )
        elif action == "qualifications":
            return self.get_qualifications()
        elif action == "fill_section":
            return self.fill_section_data(
                params.get("section_title", ""),
                params.get("section_type", ""),
                params.get("data_fields", []),
            )
        else:
            return {"error": f"Unknown action: {action}"}

    # ── Core retrieval methods ──

    def get_company_profile(self) -> Dict:
        """Get full company profile data."""
        return _load_json("company_profile.json")

    def get_team_for_project(self, project_type: str, count: int = 3) -> Dict:
        """Recommend team members based on project type."""
        data = _load_json("team_members.json")
        partners = data.get("partners", [])
        seniors = data.get("senior_lawyers", [])
        all_members = partners + seniors

        # Score each member by relevance to project type
        scored = []
        for m in all_members:
            areas = " ".join(m.get("practice_areas", []))
            bio = m.get("bio", "")
            score = 0
            for keyword in project_type:
                if keyword in areas or keyword in bio:
                    score += 1
            scored.append((score, m))

        scored.sort(key=lambda x: (-x[0], -x[1].get("practice_years", 0)))
        recommended = [m for _, m in scored[:count]]

        return {
            "recommended_team": recommended,
            "total_available": len(all_members),
        }

    def get_similar_projects(self, industry: str, count: int = 3) -> Dict:
        """Get similar past projects by industry."""
        data = _load_json("project_history.json")
        projects = data.get("projects", [])

        # Filter by industry keyword
        matched = []
        for p in projects:
            p_industry = p.get("industry", "")
            p_name = p.get("name", "")
            p_client = p.get("client", "")
            relevance = 0
            for keyword in industry:
                if keyword in p_industry or keyword in p_name or keyword in p_client:
                    relevance += 1
            if relevance > 0:
                matched.append((relevance, p))

        matched.sort(key=lambda x: -x[0])
        results = [p for _, p in matched[:count]]

        # If not enough matches, pad with most recent projects
        if len(results) < count:
            remaining = [p for p in projects if p not in results]
            results.extend(remaining[:count - len(results)])

        return {"projects": results, "total_matched": len(matched)}

    def get_qualifications(self) -> Dict:
        """Get all qualifications and compliance records."""
        return _load_json("qualifications.json")

    # ── Section-level data filling ──

    def fill_section_data(self, title: str, sec_type: str, data_fields: List[str]) -> Dict:
        """Fill data for a specific section based on its type and title.

        Returns a dict of field→value pairs that can be used to populate templates.
        """
        filled = {}  # type: Dict[str, str]
        profile = self.get_company_profile()
        quals = self.get_qualifications()

        title_lower = title.lower()

        # Company basic info fields
        company_fields = {
            "律所名称": profile.get("company_name", ""),
            "投标人名称": profile.get("company_name", ""),
            "公司名称": profile.get("company_name", ""),
            "单位名称": profile.get("company_name", ""),
            "法定代表人": profile.get("legal_rep", ""),
            "法人代表": profile.get("legal_rep", ""),
            "地址": profile.get("address", ""),
            "联系地址": profile.get("address", ""),
            "电话": profile.get("phone", ""),
            "联系电话": profile.get("phone", ""),
            "传真": profile.get("fax", ""),
            "邮箱": profile.get("email", ""),
            "电子邮箱": profile.get("email", ""),
            "网址": profile.get("website", ""),
            "开户银行": profile.get("bank_name", ""),
            "银行账号": profile.get("bank_account", ""),
            "注册资本": profile.get("registered_capital", ""),
            "成立时间": profile.get("established_year", "") + "年",
            "成立年份": profile.get("established_year", ""),
            "律师人数": profile.get("lawyer_count", ""),
            "合伙人人数": profile.get("partner_count", ""),
            "执业证号": profile.get("license_no", ""),
            "许可证号": profile.get("license_no", ""),
        }

        for field in data_fields:
            value = company_fields.get(field, "")
            if value:
                filled[field] = value

        # If section is about projects/performance, add project data
        if any(kw in title_lower for kw in ["业绩", "项目", "案例", "经验"]):
            proj_data = _load_json("project_history.json")
            filled["_projects"] = proj_data.get("projects", [])

        # If section is about team/personnel, add team data
        if any(kw in title_lower for kw in ["人员", "团队", "简历", "配置"]):
            team_data = _load_json("team_members.json")
            filled["_team"] = {
                "partners": team_data.get("partners", []),
                "senior_lawyers": team_data.get("senior_lawyers", []),
            }

        # If section is about qualifications, add qualification data
        if any(kw in title_lower for kw in ["资质", "证照", "执照", "纳税", "营业"]):
            filled["_qualifications"] = quals.get("qualifications", [])
            filled["_compliance"] = quals.get("compliance_records", {})

        return {
            "filled_data": filled,
            "data_source": "local_json",
            "fill_rate": len([v for v in filled.values() if v]) / max(len(data_fields), 1),
        }

    # ── Formatting helpers for code templates ──

    @staticmethod
    def format_project_table(projects: List[Dict], max_rows: int = 5) -> str:
        """Format project history as a Markdown table."""
        rows = ["| 序号 | 项目名称 | 委托单位 | 合同金额 | 服务期间 | 项目负责人 |",
                "|------|---------|---------|---------|---------|----------|"]
        for i, p in enumerate(projects[:max_rows], 1):
            rows.append(
                f"| {i} | {p.get('name', '')} | {p.get('client', '')} | "
                f"{p.get('contract_amount', '')} | "
                f"{p.get('start_date', '')} 至 {p.get('end_date', '')} | "
                f"{p.get('lead_lawyer', '')} |"
            )
        return "\n".join(rows)

    @staticmethod
    def format_team_table(team: Dict, max_rows: int = 5) -> str:
        """Format team members as a Markdown table."""
        all_members = team.get("partners", []) + team.get("senior_lawyers", [])
        rows = ["| 序号 | 姓名 | 职务 | 执业年限 | 学历 | 擅长领域 |",
                "|------|------|------|---------|------|---------|"]
        for i, m in enumerate(all_members[:max_rows], 1):
            areas = "、".join(m.get("practice_areas", [])[:3])
            rows.append(
                f"| {i} | {m.get('name', '')} | {m.get('title', '')} | "
                f"{m.get('practice_years', '')}年 | {m.get('education', '')} | {areas} |"
            )
        return "\n".join(rows)

    @staticmethod
    def format_qualification_checklist(quals: List[Dict]) -> str:
        """Format qualifications as a checklist."""
        lines = []
        for q in quals:
            status = "✅" if q.get("file_available") else "❌"
            valid = q.get("valid_until", "")
            lines.append(f"- {status} {q.get('name', '')} (编号: {q.get('number', '')}, 有效期: {valid})")
        return "\n".join(lines)
