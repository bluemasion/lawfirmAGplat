"""采购方 API — 采购文件编制、响应审核、评审打分。

Phase 0: 基础CRUD骨架
Phase 1: 采购文件编制+智能审核
Phase 2: 响应文件审核+围标检测
Phase 3: 在线评审+专家库
"""

import logging
import os
from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


# ======================== Schemas ========================

class ProjectCreate(BaseModel):
    name: str
    method: str = "open_bidding"  # open_bidding/negotiation/inquiry/sole_source/framework
    budget: float = 0
    industry: str = ""
    description: str = ""


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    method: Optional[str] = None
    budget: Optional[float] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


# ======================== 采购项目 CRUD ========================

@router.get("/projects")
async def list_projects(status: Optional[str] = None):
    """列出采购项目"""
    from app.data.stores.procurement_store import get_procurement_store
    store = get_procurement_store()
    projects = store.list_projects(status=status)
    return {"projects": projects, "total": len(projects)}


@router.post("/projects")
async def create_project(req: ProjectCreate):
    """创建采购项目"""
    from app.data.stores.procurement_store import get_procurement_store
    store = get_procurement_store()
    project = store.create_project(
        name=req.name, method=req.method, budget=req.budget,
        industry=req.industry, description=req.description,
    )
    return {"project": project}


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """获取采购项目详情"""
    from app.data.stores.procurement_store import get_procurement_store
    store = get_procurement_store()
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"project": project}


@router.put("/projects/{project_id}")
async def update_project(project_id: str, req: ProjectUpdate):
    """更新采购项目"""
    from app.data.stores.procurement_store import get_procurement_store
    store = get_procurement_store()
    updates = {k: v for k, v in req.dict().items() if v is not None}
    project = store.update_project(project_id, **updates)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"project": project}


# ======================== 供应商响应 ========================

@router.get("/projects/{project_id}/responses")
async def list_responses(project_id: str):
    """列出项目的供应商响应"""
    from app.data.stores.procurement_store import get_procurement_store
    store = get_procurement_store()
    responses = store.list_responses(project_id)
    return {"responses": responses, "total": len(responses)}


@router.post("/projects/{project_id}/responses")
async def add_response(project_id: str, supplier_name: str = Form(...)):
    """添加供应商响应"""
    from app.data.stores.procurement_store import get_procurement_store
    store = get_procurement_store()
    response = store.add_response(project_id, supplier_name)
    return {"response": response}


# ======================== 专家库 ========================

@router.get("/experts")
async def list_experts(category: Optional[str] = None):
    """列出专家"""
    from app.data.stores.expert_store import get_expert_store
    store = get_expert_store()
    experts = store.list_experts(category=category)
    return {"experts": experts, "total": len(experts)}


@router.post("/experts")
async def add_expert(
    name: str = Form(...),
    organization: str = Form(""),
    title: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
):
    """添加专家"""
    from app.data.stores.expert_store import get_expert_store
    store = get_expert_store()
    expert = store.add_expert(
        name=name, organization=organization,
        title=title, phone=phone, email=email,
    )
    return {"expert": expert}


# ======================== 模板引擎 API (Phase 1) ========================

@router.get("/templates/skeleton")
async def get_skeleton():
    """获取采购文件7章标准骨架"""
    from app.core.skills.procurement.template_engine import TemplateEngine
    engine = TemplateEngine()
    return {"skeleton": engine.get_skeleton()}


@router.get("/templates/parameters")
async def get_parameter_fields():
    """获取须知前附表参数字段定义"""
    from app.core.skills.procurement.template_engine import TemplateEngine
    engine = TemplateEngine()
    fields = engine.get_parameter_fields()
    groups = engine.get_parameter_groups()
    return {"fields": fields, "groups": groups}


@router.get("/templates/eval-methods")
async def get_eval_methods():
    """获取评标方法模板"""
    from app.core.skills.procurement.template_engine import TemplateEngine
    engine = TemplateEngine()
    return {"methods": engine.get_eval_methods()}


class FillTemplateRequest(BaseModel):
    parameters: Dict = {}
    scoring_criteria: Dict = {}


@router.post("/templates/fill")
async def fill_template(req: FillTemplateRequest):
    """用参数填充模板，生成结构化文档内容"""
    from app.core.skills.procurement.template_engine import TemplateEngine
    engine = TemplateEngine()
    params = {**req.parameters}
    if req.scoring_criteria:
        params["scoring_criteria"] = req.scoring_criteria
    document = engine.fill_template(params)
    return {"document": document}


# ======================== 评分标准 API (Phase 1) ========================

@router.get("/scoring/items")
async def get_scoring_items():
    """获取所有评分项模板"""
    from app.core.skills.procurement.scoring_template import ScoringTemplateLibrary
    lib = ScoringTemplateLibrary()
    return {"items": lib.get_all_items()}


@router.get("/scoring/formulas")
async def get_price_formulas():
    """获取价格评分公式模板"""
    from app.core.skills.procurement.scoring_template import ScoringTemplateLibrary
    lib = ScoringTemplateLibrary()
    return {"formulas": lib.get_price_formulas()}


@router.get("/scoring/presets")
async def get_scoring_presets():
    """获取预设评分方案"""
    from app.core.skills.procurement.scoring_template import ScoringTemplateLibrary
    lib = ScoringTemplateLibrary()
    return {"presets": lib.get_presets()}


@router.get("/scoring/presets/{industry}")
async def get_scoring_preset(industry: str):
    """获取指定行业的预设评分方案(含详细评分项)"""
    from app.core.skills.procurement.scoring_template import ScoringTemplateLibrary
    lib = ScoringTemplateLibrary()
    preset = lib.get_preset(industry)
    if not preset:
        raise HTTPException(status_code=404, detail=f"行业 '{industry}' 预设方案不存在")
    return {"preset": preset}


class BuildScoringRequest(BaseModel):
    commercial_item_ids: List[str] = []
    technical_item_ids: List[str] = []
    score_distribution: Dict = {"commercial": 30, "technical": 40, "price": 30}
    price_formula: str = "arithmetic_mean"


@router.post("/scoring/build")
async def build_scoring_criteria(req: BuildScoringRequest):
    """根据选择的评分项构建完整评分标准"""
    from app.core.skills.procurement.scoring_template import ScoringTemplateLibrary
    lib = ScoringTemplateLibrary()
    criteria = lib.build_scoring_criteria(
        commercial_item_ids=req.commercial_item_ids,
        technical_item_ids=req.technical_item_ids,
        score_distribution=req.score_distribution,
        price_formula=req.price_formula,
    )
    return {"criteria": criteria}


# ======================== 文档生成 + 审核 API (Phase 1) ========================

class GenerateDocRequest(BaseModel):
    parameters: Dict = {}
    scoring_criteria: Dict = {}


@router.post("/documents/generate")
async def generate_document(req: GenerateDocRequest):
    """生成采购文件 Word 文档"""
    from app.core.skills.procurement.template_engine import TemplateEngine
    from app.core.skills.procurement.doc_builder import DocBuilder

    engine = TemplateEngine()
    params = {**req.parameters}
    if req.scoring_criteria:
        params["scoring_criteria"] = req.scoring_criteria

    document = engine.fill_template(params)
    builder = DocBuilder()
    file_path = builder.build(document)

    return {
        "status": "success",
        "file_path": file_path,
        "file_name": os.path.basename(file_path),
        "document_metadata": document.get("metadata", {}),
    }


class ReviewRequest(BaseModel):
    parameters: Dict = {}
    scoring_criteria: Dict = {}


@router.post("/documents/review")
async def review_document(req: ReviewRequest):
    """智能审核采购文件"""
    from app.core.skills.procurement.template_engine import TemplateEngine
    from app.core.skills.procurement.doc_reviewer import DocReviewer, ReviewReportGenerator

    engine = TemplateEngine()
    params = {**req.parameters}
    if req.scoring_criteria:
        params["scoring_criteria"] = req.scoring_criteria

    document = engine.fill_template(params)
    reviewer = DocReviewer()
    result = reviewer.review(document)

    # 生成文本报告
    report_gen = ReviewReportGenerator()
    text_report = report_gen.generate_text_report(result)
    result["text_report"] = text_report

    return result


from starlette.responses import FileResponse


@router.get("/documents/download/{filename}")
async def download_document(filename: str):
    """下载生成的采购文件"""
    from app.core.skills.procurement.doc_builder import OUTPUT_DIR

    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


# ======================== Phase 2-3 Placeholder ========================

@router.post("/projects/{project_id}/collusion-check")
async def check_collusion(project_id: str):
    """围标检测 (Phase 2)"""
    return {"status": "not_implemented", "message": "Phase 2: 围标检测待实现"}


@router.post("/reviews/{session_id}/score")
async def submit_score(session_id: str):
    """评审打分 (Phase 3)"""
    return {"status": "not_implemented", "message": "Phase 3: 评审打分待实现"}
