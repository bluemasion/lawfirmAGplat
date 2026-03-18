"""Company data management API — CRUD for firm profile, team, projects, and certificates.

Manages JSON files in data/company/ which are consumed by data_retrieval and template_filling skills.
"""

import json
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.utils.logger import logger


router = APIRouter()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "company")


# ── Helpers ──────────────────────────────────────────────────

def _read_json(filename: str) -> Dict:
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(filename: str, data: Any) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logger.info(f"Company data saved: {filename}")


# ── Pydantic Models ──────────────────────────────────────────

class CompanyProfile(BaseModel):
    company_name: str = ""
    license_no: str = ""
    legal_rep: str = ""
    address: str = ""
    phone: str = ""
    fax: str = ""
    email: str = ""
    website: str = ""
    bank_name: str = ""
    bank_account: str = ""
    registered_capital: str = ""
    established_year: str = ""
    lawyer_count: str = ""
    partner_count: str = ""
    total_staff: str = ""
    office_area: str = ""
    practice_areas: List[str] = []
    honors: List[str] = []


class TeamMember(BaseModel):
    name: str
    title: str = ""
    license_no: str = ""
    years_of_experience: int = 0
    education: str = ""
    specialties: List[str] = []
    major_cases: List[str] = []
    certifications: List[str] = []


class ProjectCase(BaseModel):
    name: str
    client: str = ""
    industry: str = ""
    type: str = ""
    contract_amount: str = ""
    start_date: str = ""
    end_date: str = ""
    status: str = ""
    lead_lawyer: str = ""
    team_size: int = 0
    description: str = ""
    key_achievements: List[str] = []


class Qualification(BaseModel):
    name: str
    number: str = ""
    issuer: str = ""
    valid_from: str = ""
    valid_to: str = ""
    status: str = "有效"


# ── 1. Company Profile ──────────────────────────────────────

@router.get("/profile")
async def get_profile():
    """获取律所基本信息"""
    data = _read_json("company_profile.json")
    return {"success": True, "data": data}


@router.post("/profile")
async def update_profile(profile: CompanyProfile):
    """更新律所基本信息"""
    # Merge with existing data (preserve extra fields)
    existing = _read_json("company_profile.json")
    update_dict = profile.dict(exclude_unset=False)
    # Only update non-empty fields
    for k, v in update_dict.items():
        if v or v == 0:  # Allow 0 but not empty string/list
            existing[k] = v
    _write_json("company_profile.json", existing)
    return {"success": True, "message": "律所信息已更新", "data": existing}


# ── 2. Team Members ─────────────────────────────────────────

@router.get("/team")
async def get_team():
    """获取团队成员列表"""
    data = _read_json("team_members.json")
    return {"success": True, "data": data}


@router.post("/team/member")
async def add_team_member(member: TeamMember, category: str = "senior_lawyers"):
    """添加团队成员 (category: partners / senior_lawyers / associates)"""
    data = _read_json("team_members.json")
    if category not in data:
        data[category] = []
    data[category].append(member.dict())
    _write_json("team_members.json", data)
    return {"success": True, "message": f"已添加成员: {member.name}", "data": data}


@router.delete("/team/member/{name}")
async def remove_team_member(name: str):
    """删除团队成员"""
    data = _read_json("team_members.json")
    found = False
    for category in data:
        if isinstance(data[category], list):
            original_len = len(data[category])
            data[category] = [m for m in data[category] if m.get("name") != name]
            if len(data[category]) < original_len:
                found = True
    if not found:
        raise HTTPException(status_code=404, detail=f"未找到成员: {name}")
    _write_json("team_members.json", data)
    return {"success": True, "message": f"已删除成员: {name}"}


# ── 3. Project History ──────────────────────────────────────

@router.get("/projects")
async def get_projects():
    """获取业绩案例列表"""
    data = _read_json("project_history.json")
    return {"success": True, "data": data.get("projects", [])}


@router.post("/projects")
async def add_project(project: ProjectCase):
    """添加业绩案例"""
    data = _read_json("project_history.json")
    if "projects" not in data:
        data["projects"] = []
    data["projects"].append(project.dict())
    _write_json("project_history.json", data)
    return {"success": True, "message": f"已添加项目: {project.name}",
            "total": len(data["projects"])}


@router.delete("/projects/{name}")
async def remove_project(name: str):
    """删除业绩案例"""
    data = _read_json("project_history.json")
    projects = data.get("projects", [])
    original_len = len(projects)
    data["projects"] = [p for p in projects if p.get("name") != name]
    if len(data["projects"]) == original_len:
        raise HTTPException(status_code=404, detail=f"未找到项目: {name}")
    _write_json("project_history.json", data)
    return {"success": True, "message": f"已删除项目: {name}"}


# ── 4. Qualifications ───────────────────────────────────────

@router.get("/qualifications")
async def get_qualifications():
    """获取资质证书列表"""
    data = _read_json("qualifications.json")
    return {"success": True, "data": data}


@router.post("/qualifications")
async def add_qualification(qual: Qualification):
    """添加资质证书"""
    data = _read_json("qualifications.json")
    if "qualifications" not in data:
        data["qualifications"] = []
    data["qualifications"].append(qual.dict())
    _write_json("qualifications.json", data)
    return {"success": True, "message": f"已添加资质: {qual.name}",
            "total": len(data["qualifications"])}


# ── 5. Summary / Stats ──────────────────────────────────────

@router.get("/summary")
async def get_data_summary():
    """获取数据完整性摘要 — 帮助用户了解还缺什么数据"""
    profile = _read_json("company_profile.json")
    team = _read_json("team_members.json")
    projects = _read_json("project_history.json")
    quals = _read_json("qualifications.json")

    # Count filled fields in profile
    total_profile_fields = 14  # core fields
    filled_profile = sum(1 for k in [
        "company_name", "license_no", "legal_rep", "address", "phone",
        "fax", "email", "bank_name", "bank_account", "registered_capital",
        "established_year", "lawyer_count", "partner_count", "website",
    ] if profile.get(k))

    team_count = sum(len(v) for v in team.values() if isinstance(v, list))
    project_count = len(projects.get("projects", []))
    qual_count = len(quals.get("qualifications", []))

    completeness = (filled_profile / total_profile_fields) * 100

    missing = []
    for field, label in [
        ("company_name", "律所名称"), ("license_no", "执业许可证号"),
        ("legal_rep", "法定代表人"), ("address", "地址"),
        ("phone", "联系电话"), ("bank_name", "开户银行"),
        ("bank_account", "银行账号"),
    ]:
        if not profile.get(field):
            missing.append(label)

    return {
        "success": True,
        "data": {
            "profile_completeness": round(completeness, 1),
            "profile_filled": filled_profile,
            "profile_total": total_profile_fields,
            "team_members": team_count,
            "projects": project_count,
            "qualifications": qual_count,
            "missing_critical_fields": missing,
        }
    }
