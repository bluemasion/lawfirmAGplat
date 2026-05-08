# -*- coding: utf-8 -*-
"""PromptSkill — 可配置的 prompt 策略模块。

每个 PromptSkill 封装一类章节的 prompt 构建逻辑：
- 声明需要什么上下文数据 (required_context)
- 根据实际数据动态构建 prompt (build_prompt)
- 通过关键词匹配自动路由 (match_keywords)

用法:
    registry = PromptSkillRegistry()
    skill = registry.match("服务方案")
    prompt = skill.build_prompt(section, context)
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from app.utils.logger import logger


class PromptSkill(ABC):
    """Base class for all prompt skills."""

    # 子类必须定义
    name = ""           # type: str   # 唯一标识: "service_plan"
    description = ""    # type: str   # 人类描述
    match_keywords = [] # type: List[str]  # 关键词列表

    # 声明本 prompt 需要哪些上下文数据
    # 可选值: "company_info", "team", "projects", "qualifications",
    #         "scoring_criteria", "reference_sections"
    required_context = []  # type: List[str]

    def get_system_prompt(self):
        # type: () -> str
        """Return the system prompt for this skill.
        
        Default: shared system prompt. Override for specialized behavior.
        """
        return SHARED_SYSTEM_PROMPT

    @abstractmethod
    def build_prompt(self, section, context):
        # type: (Dict[str, Any], Dict[str, Any]) -> str
        """Build the user prompt from section info and context data.
        
        Args:
            section: {"title": str, "content_hints": str, "type": str, ...}
            context: {"company_info": str, "team": List, "projects": List,
                      "reference_data": str, "skeleton_hint": str, ...}
        Returns:
            Complete prompt string ready for LLM.
        """
        ...

    def matches(self, title):
        # type: (str) -> bool
        """Check if this skill matches a section title."""
        title_lower = title.lower()
        return any(kw in title_lower for kw in self.match_keywords)


# ── Shared System Prompt (company-neutral) ──

SHARED_SYSTEM_PROMPT = """你是一位资深的投标文件撰写专家，拥有10年以上政府采购和企业招标经验。
你的任务是根据招标要求和参考资料，为投标文件的指定章节撰写专业、精准的内容。

# 核心规则（必须严格遵守）

1. **禁止编造**：不得编造人员姓名、资质编号、案例名称、金额等具体事实数据。
   如无真实数据，必须用 [待补充：xxx] 格式标注。
2. **逐项回应**：招标要求的每一条必须在投标内容中有对应回应段落，不得遗漏。
3. **引用参考**：如果提供了参考资料（来自招标原文），必须基于参考资料的具体要求
   来组织内容，不要泛泛而谈。
4. **仅使用提供的公司信息**：只能引用【我方公司信息】中提供的数据，
   不得混入其他公司的数据或自行编造公司信息。
5. **数据优先**：用具体数据（年限、人数、项目数等）代替空泛描述。
   如果没有提供具体数据，使用 [待补充：xxx] 标注，不要编造数字。

# 格式规范
- 正式商务文书语言，避免口语化
- 段落清晰，逻辑分明
- 引用法律法规时精确到条款
- 方案类内容需有：目标→方法→保障措施→时间安排的完整逻辑"""


# ── Helper: build company data block ──

def _build_company_block(context):
    # type: (Dict[str, Any]) -> str
    """Build the company info block for prompts from context data."""
    company_info = context.get("company_info", "")
    if not company_info:
        return "暂无公司信息"
    return company_info


def _build_team_block(context):
    # type: (Dict[str, Any]) -> str
    """Build team data block from context."""
    team = context.get("team", [])
    if not team:
        return ""
    lines = ["\n【我方团队成员（真实数据，必须引用）】"]
    for r in team[:8]:
        name = r.get("name", "?")
        title = r.get("title", "")
        spec = r.get("specialty", "")
        line = "- %s" % name
        if title:
            line += "，%s" % title
        if spec:
            line += "，擅长%s" % spec
        lines.append(line)
    return "\n".join(lines)


def _build_projects_block(context):
    # type: (Dict[str, Any]) -> str
    """Build projects data block from context."""
    projects = context.get("projects", [])
    if not projects:
        return ""
    lines = ["\n【我方项目业绩（真实数据，必须引用）】"]
    for p in projects[:6]:
        pname = p.get("project_name", p.get("name", "?"))
        client = p.get("client", "")
        line = "- %s" % pname
        if client:
            line += "，委托方: %s" % client
        amount = p.get("contract_amount", p.get("amount", ""))
        if amount:
            line += "，金额: %s" % amount
        lines.append(line)
    return "\n".join(lines)


def _build_qualifications_block(context):
    # type: (Dict[str, Any]) -> str
    """Build qualifications data block from context."""
    quals = context.get("qualifications", [])
    if not quals:
        return ""
    lines = ["\n【我方资质证书（真实数据，按需引用）】"]
    for q in quals[:5]:
        qname = q.get("name", "?")
        issuer = q.get("issuer", "")
        line = "- %s" % qname
        if issuer:
            line += "，颁发: %s" % issuer
        lines.append(line)
    return "\n".join(lines)


# ── Concrete PromptSkill Implementations ──


class FirmIntroPromptSkill(PromptSkill):
    """公司/律所介绍类章节"""
    name = "firm_intro"
    description = "投标人综合实力展示"
    match_keywords = [
        "律所介绍", "律所概况", "供应商介绍", "投标人介绍", "公司简介",
        "企业概况", "单位概况", "基本情况介绍", "投标人概况",
        "机构介绍", "事务所介绍",
    ]
    required_context = ["company_info", "qualifications"]

    def build_prompt(self, section, context):
        company_block = _build_company_block(context)
        quals_block = _build_qualifications_block(context)
        skeleton = context.get("skeleton_hint", "")

        return """请为投标文件撰写以下章节：

【章节标题】{title}

【招标要求】{hints}

【来自招标文件的原文参考】{reference}

【我方公司信息（真实数据，直接引用）】
{company}
{quals}

{skeleton}

# 写作策略：投标人综合实力展示

## 结构要求
1. **公司概况** — 成立时间、规模、办公地点等基本情况
2. **核心业务领域** — 与本次招标相关的业务领域，引用具体数据
3. **荣誉资质** — 行业资质、荣誉证书，按权威性排序
4. **服务优势** — 结合招标要求，说明我方的匹配度和差异化优势

## 写作要求
- 只引用上方提供的真实数据，不要编造
- 如果信息不足，用 [待补充：xxx] 标注
- 800-1500字""".format(
            title=section.get("title", ""),
            hints=section.get("content_hints", ""),
            reference=context.get("reference_data", ""),
            company=company_block,
            quals=quals_block,
            skeleton=skeleton,
        )


class ServicePlanPromptSkill(PromptSkill):
    """服务方案/技术方案类章节"""
    name = "service_plan"
    description = "评分导向型服务方案"
    match_keywords = [
        "服务方案", "实施方案", "技术方案", "工作方案", "项目方案",
        "服务计划", "实施计划", "工作计划", "服务内容",
        "服务承诺", "服务保障", "服务模式", "服务流程",
        "工作思路", "整体方案", "总体方案", "项目实施",
        "工作安排", "时间安排", "进度安排", "应急预案",
        "风险防控", "培训方案", "培训计划", "增值服务",
    ]
    required_context = ["company_info", "team", "projects", "scoring_criteria"]

    def build_prompt(self, section, context):
        company_block = _build_company_block(context)
        team_block = _build_team_block(context)
        projects_block = _build_projects_block(context)
        skeleton = context.get("skeleton_hint", "")

        return """请为投标文件撰写以下章节：

【章节标题】{title}

【招标要求（必须逐项回应）】{hints}

【来自招标文件的原文参考】{reference}

【我方公司信息（真实数据，直接引用）】
{company}
{team}
{projects}

{skeleton}

# 写作策略：评分导向型服务方案

## 核心原则：每个评分子项 = 一个独立段落
如果上方【评分标准】中列出了子评分项，你必须为每个子评分项撰写独立段落。

## 文章结构

### 开头（200-300字）
- 对项目的深入理解，总体服务理念和方法论

### 主体：按评分子项逐一展开
每段 400-600 字，必须包含：
1. **方法论**：阐述总体思路和方法
2. **具体措施**：3-5 条可操作、可验证的具体措施
3. **数据支撑**：引用上方提供的真实数据
4. **量化承诺**：至少 1 个可量化的承诺

### 结尾（100-150字）
- 服务承诺总结，衔接后续章节

## 写作禁忌
- 不要编造公司数据（成立年份、员工人数等）
- 不要泛泛承诺，用具体措施说明

总字数：1500-2500字""".format(
            title=section.get("title", ""),
            hints=section.get("content_hints", ""),
            reference=context.get("reference_data", ""),
            company=company_block,
            team=team_block,
            projects=projects_block,
            skeleton=skeleton,
        )


class TeamPromptSkill(PromptSkill):
    """团队人员介绍类章节"""
    name = "team"
    description = "团队人员介绍"
    match_keywords = [
        "团队介绍", "人员介绍", "律师团队", "拟投入人员",
        "项目团队", "核心团队", "服务团队", "人员配置",
        "项目组成员", "拟委派",
    ]
    required_context = ["company_info", "team"]

    def build_prompt(self, section, context):
        company_block = _build_company_block(context)
        team_block = _build_team_block(context)
        skeleton = context.get("skeleton_hint", "")

        return """请为投标文件撰写以下章节：

【章节标题】{title}

【招标要求】{hints}

【来自招标文件的原文参考】{reference}

【我方公司信息】
{company}
{team}

{skeleton}

# 写作策略：团队人员介绍

## 重要：使用真实数据
上面提供的人员信息是真实的，你**必须**使用这些真实姓名和经历来撰写。
**严禁编造人员姓名或经历。**

## 结构要求
### 一、团队概述 (100-200字)
### 二、核心成员介绍 (每人200-400字)
- 姓名、职务/职称、执业年限
- 专业领域、代表案例
- 在本项目中拟担任的角色
### 三、团队优势总结 (100-200字)""".format(
            title=section.get("title", ""),
            hints=section.get("content_hints", ""),
            reference=context.get("reference_data", ""),
            company=company_block,
            team=team_block,
            skeleton=skeleton,
        )


class ProjectPerfPromptSkill(PromptSkill):
    """项目业绩展示类章节"""
    name = "project_perf"
    description = "项目业绩展示"
    match_keywords = [
        "业绩介绍", "类似业绩", "项目经验", "服务案例",
        "成功案例", "代表业绩", "项目业绩",
    ]
    required_context = ["company_info", "projects"]

    def build_prompt(self, section, context):
        company_block = _build_company_block(context)
        projects_block = _build_projects_block(context)
        skeleton = context.get("skeleton_hint", "")

        return """请为投标文件撰写以下章节：

【章节标题】{title}

【招标要求】{hints}

【来自招标文件的原文参考】{reference}

【我方公司信息】
{company}
{projects}

{skeleton}

# 写作策略：项目业绩展示

## 重要：使用真实数据
上面提供的项目信息是真实的，你**必须**使用这些真实项目来撰写。
**严禁编造项目名称或金额。**

## 结构要求
### 一、业绩概述 (100-200字)
### 二、代表项目详述 (每项200-400字)
- 项目名称、委托方、服务内容、项目成果
### 三、业绩匹配性分析 (100-200字)""".format(
            title=section.get("title", ""),
            hints=section.get("content_hints", ""),
            reference=context.get("reference_data", ""),
            company=company_block,
            projects=projects_block,
            skeleton=skeleton,
        )


class QualityControlPromptSkill(PromptSkill):
    """质量控制方案类章节"""
    name = "quality_control"
    description = "质量控制方案"
    match_keywords = [
        "质量控制", "质量管理", "质量保证", "质量保障",
        "服务质量", "品质管理", "品质保证",
    ]
    required_context = ["company_info"]

    def build_prompt(self, section, context):
        company_block = _build_company_block(context)
        skeleton = context.get("skeleton_hint", "")

        return """请为投标文件撰写以下章节：

【章节标题】{title}

【招标要求（必须逐项回应）】{hints}

【来自招标文件的原文参考】{reference}

【我方公司信息（真实数据，直接引用）】
{company}

{skeleton}

# 写作策略：质量控制方案

## 必须覆盖的五个维度（每个维度 300-500 字）

### 一、组织保障（质量管理架构）
### 二、过程控制（关键节点检查）
### 三、风险预警（风险识别机制）
### 四、投诉与反馈处理
### 五、持续改进（复盘与沉淀）

## 管理制度引用
如果公司信息中提供了管理制度，请在相应段落中引用。
如果没有提供，可以按行业最佳实践撰写，但不要编造具体制度名称。

总字数：1500-2500字""".format(
            title=section.get("title", ""),
            hints=section.get("content_hints", ""),
            reference=context.get("reference_data", ""),
            company=company_block,
            skeleton=skeleton,
        )


class CompliancePromptSkill(PromptSkill):
    """合规/保障/声明类章节"""
    name = "compliance"
    description = "合规/保障/声明类"
    match_keywords = [
        "保密", "廉洁", "合规", "利益冲突", "回避",
        "保障措施", "信誉", "诚信", "承诺",
        "知识产权", "档案管理", "文件管理", "信息安全",
        "售后服务", "投诉处理", "争议解决",
    ]
    required_context = ["company_info"]

    def build_prompt(self, section, context):
        company_block = _build_company_block(context)
        skeleton = context.get("skeleton_hint", "")

        return """请为投标文件撰写以下章节：

【章节标题】{title}

【招标要求】{hints}

【来自招标文件的原文参考】{reference}

【我方公司信息（真实数据，直接引用）】
{company}

{skeleton}

# 写作策略：合规/保障/声明类

## 写作要求
1. 引用具体法律法规条款
2. 使用正式承诺性语言，但不绝对化
3. 分条列举，每条一个承诺/保障措施
4. 包含违约责任说明
5. 300-800字""".format(
            title=section.get("title", ""),
            hints=section.get("content_hints", ""),
            reference=context.get("reference_data", ""),
            company=company_block,
            skeleton=skeleton,
        )


class GenericPromptSkill(PromptSkill):
    """通用 fallback prompt"""
    name = "generic"
    description = "通用叙述章节"
    match_keywords = []  # Never matches via keywords, used as fallback
    required_context = ["company_info", "team", "projects", "qualifications"]

    def build_prompt(self, section, context):
        company_block = _build_company_block(context)
        team_block = _build_team_block(context)
        projects_block = _build_projects_block(context)
        quals_block = _build_qualifications_block(context)
        skeleton = context.get("skeleton_hint", "")

        # Only include non-empty data blocks
        data_blocks = "\n".join(filter(None, [
            team_block, projects_block, quals_block
        ]))

        return """请为投标文件撰写以下章节的内容：

【章节标题】{title}

【招标要求（必须逐项回应）】{hints}

【来自招标文件的原文参考】{reference}

【我方公司信息（真实数据，可直接引用）】
{company}
{data_blocks}

{skeleton}

# 输出要求
1. 直接输出该章节的正文内容
2. 使用 Markdown 格式
3. 对招标要求中的每一条核心要求，都要有明确的回应段落
4. 没有真实数据的字段用 [待补充：字段名] 标注
5. 引用上方提供的真实素材数据来支撑论述
6. 800-1500字""".format(
            title=section.get("title", ""),
            hints=section.get("content_hints", ""),
            reference=context.get("reference_data", ""),
            company=company_block,
            data_blocks=data_blocks,
            skeleton=skeleton,
        )


# ── PromptSkill Registry ──

class PromptSkillRegistry:
    """Registry for prompt skills with keyword-based matching."""

    def __init__(self):
        self._skills = {}  # type: Dict[str, PromptSkill]
        self._fallback = GenericPromptSkill()

    def register(self, skill):
        # type: (PromptSkill) -> None
        self._skills[skill.name] = skill
        logger.debug("PromptSkill registered: %s" % skill.name)

    def match(self, title):
        # type: (str) -> PromptSkill
        """Find the best matching prompt skill for a section title."""
        for skill in self._skills.values():
            if skill.matches(title):
                logger.info("  PromptSkill: '%s' -> %s" % (title, skill.name))
                return skill
        logger.info("  PromptSkill: '%s' -> generic (fallback)" % title)
        return self._fallback

    def get(self, name):
        # type: (str) -> Optional[PromptSkill]
        return self._skills.get(name, self._fallback)

    def list_skills(self):
        # type: () -> List[str]
        return list(self._skills.keys())


def create_default_registry():
    # type: () -> PromptSkillRegistry
    """Create and populate the default prompt skill registry."""
    registry = PromptSkillRegistry()
    # Order matters: first match wins
    registry.register(TeamPromptSkill())
    registry.register(ProjectPerfPromptSkill())
    registry.register(FirmIntroPromptSkill())
    registry.register(QualityControlPromptSkill())
    registry.register(ServicePlanPromptSkill())
    registry.register(CompliancePromptSkill())
    return registry


# Global singleton
_default_registry = None  # type: Optional[PromptSkillRegistry]


def get_prompt_registry():
    # type: () -> PromptSkillRegistry
    """Get or create the global prompt skill registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = create_default_registry()
    return _default_registry
