"""Content generation skill — generate bid section content.

Phase 2 refactor: only narrative sections use LLM.
Table/form/qualification sections use code templates + RAG data.
"""

from typing import Any, Dict, List, Optional

from app.core.skills.base import BaseSkill
from app.core.skills.builtin.data_retrieval import DataRetrievalSkill
from app.core.llm import get_llm
from app.utils.logger import logger


# ── LLM Prompts (only used for narrative sections) ──

SECTION_GENERATION_SYSTEM = """你是一位资深的律所投标文件撰写专家，拥有10年以上政府采购和企业招标经验。
你的任务是根据招标要求和参考资料，为投标文件的指定章节撰写专业、精准的内容。

# 核心规则（必须严格遵守）

1. **禁止编造**：不得编造律师姓名、资质编号、案例名称、金额等具体事实数据。
   如无真实数据，必须用 [待补充：xxx] 格式标注。
2. **逐项回应**：招标要求的每一条必须在投标内容中有对应回应段落，不得遗漏。
3. **引用参考**：如果提供了参考资料（来自招标原文），必须基于参考资料的具体要求
   来组织内容，不要泛泛而谈。
4. **使用真实律所信息**：提供的律所基本信息中的数据是真实的，直接引用即可。

# 格式规范
- 正式法律文书语言，避免口语化
- 段落清晰，逻辑分明
- 引用法律法规时精确到条款
- 方案类内容需有：目标→方法→保障措施→时间安排的完整逻辑"""

NARRATIVE_PROMPT = """请为投标文件撰写以下章节的内容：

【章节标题】
{section_title}

【招标要求（必须逐项回应）】
{content_hints}

【来自招标文件的原文参考】
{reference_data}

【我方律所信息（真实数据，可直接引用）】
{company_info}

{skeleton_hint}

# 输出要求
1. 直接输出该章节的正文内容
2. 使用 Markdown 格式（## 二级标题，### 三级标题，| 表格）
3. 对招标要求中的每一条核心要求，都要有明确的回应段落
4. 没有真实数据的字段用 [待补充：字段名] 标注
5. 内容应具体、有针对性，不得使用空泛的承诺性语句"""


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
            title, content_hints, reference_data, company_info, llm_provider, skeleton
        )
        missing = self._scan_missing(content)
        return self._result(title, content, missing, "generated")

    # ── Form: code templates ──

    def _generate_form_by_template(self, title: str, hints: str) -> str:
        """Generate form content using built-in templates."""
        profile = self._data_retrieval.get_company_profile()

        # Find matching form template
        for tpl_name, tpl_content in FORM_TEMPLATES.items():
            if tpl_name in title or any(kw in title for kw in tpl_name):
                logger.info(f"  → Form template matched: {tpl_name}")
                return tpl_content.format(
                    company_name=profile.get("company_name", "[待补充：律所名称]"),
                    legal_rep=profile.get("legal_rep", "[待补充：法定代表人]"),
                    address=profile.get("address", "[待补充：地址]"),
                    phone=profile.get("phone", "[待补充：电话]"),
                    fax=profile.get("fax", "[待补充：传真]"),
                    email=profile.get("email", "[待补充：邮箱]"),
                    total_staff=profile.get("total_staff", "[待补充：员工人数]"),
                    招标方名称="[待补充：招标方名称]",
                    项目名称="[待补充：项目名称]",
                )

        # No match → generic form template
        logger.info(f"  → No form template match for '{title}', using generic")
        return self._generic_form(title, hints, profile)

    # ── Table: code templates + data ──

    async def _generate_table_by_template(self, title: str, hints: str, data_fields: List[str]) -> str:
        """Generate table section using code templates and RAG data."""
        profile = self._data_retrieval.get_company_profile()

        for tpl_name, tpl_info in TABLE_TEMPLATES.items():
            if any(kw in title for kw in tpl_info["match_keywords"]):
                generator_name = tpl_info["generator"]
                generator = getattr(self, generator_name, None)
                if generator:
                    logger.info(f"  → Table template matched: {tpl_name}")
                    return generator(title, profile)

        # No match → generic table
        logger.info(f"  → No table template match for '{title}', using generic")
        return self._generic_table(title, hints, data_fields)

    # ── Narrative: LLM only ──

    async def _generate_narrative_section(self, title: str, hints: str,
                                           reference: str, company_info: str,
                                           llm_provider: str,
                                           skeleton: Optional[str] = None) -> str:
        """Generate narrative section using LLM (the only LLM-calling path)."""
        llm = get_llm(llm_provider)

        skeleton_hint = ""
        if skeleton:
            skeleton_hint = f"\n【参考骨架（来自历史模板）】\n{skeleton}\n请参考以上骨架结构，结合本次招标要求改写。"

        prompt = NARRATIVE_PROMPT.format(
            section_title=title,
            content_hints=hints or "按照招标要求撰写",
            reference_data=reference,
            company_info=company_info,
            skeleton_hint=skeleton_hint,
        )
        return await llm.generate(prompt, system=SECTION_GENERATION_SYSTEM)

    # ── Table generators ──

    def _gen_company_basic_table(self, title: str, profile: Dict) -> str:
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

    def _gen_price_overview_table(self, title: str, profile: Dict) -> str:
        return f"""## {title}

| 序号 | 服务项目 | 单位 | 数量 | 单价（元） | 合计（元） | 备注 |
|------|---------|------|------|-----------|-----------|------|
| 1 | 常年法律顾问服务 | 年 | 1 | [待补充：单价] | [待补充：合计] | |
| 2 | 专项法律服务 | 项 | [待补充] | [待补充：单价] | [待补充：合计] | |
| 3 | 诉讼/仲裁代理 | 件 | [待补充] | [待补充：单价] | [待补充：合计] | |
| | **合计** | | | | **[待补充：总价]** | |

> 注：以上报价为含税价格，税率为 [待补充：税率]%。
"""

    def _gen_price_detail_table(self, title: str, profile: Dict) -> str:
        return f"""## {title}

| 序号 | 费用项目 | 计算方式 | 金额（元） | 说明 |
|------|---------|---------|-----------|------|
| 1 | 律师服务费 | [待补充] | [待补充] | 主要服务费用 |
| 2 | 调查取证费 | 实报实销 | [待补充] | 按实际发生 |
| 3 | 交通差旅费 | 实报实销 | [待补充] | 按实际发生 |
| 4 | 文印资料费 | 包含在服务费中 | — | |
| | **合计** | | **[待补充：合计]** | |
"""

    def _gen_project_history_table(self, title: str, profile: Dict) -> str:
        projects = self._data_retrieval.get_similar_projects("", 10).get("projects", [])
        if not projects:
            return f"## {title}\n\n暂无业绩数据，请补充。\n"

        lines = [f"## {title}\n"]
        lines.append("| 序号 | 项目名称 | 委托方 | 服务内容 | 合同金额 | 服务期间 | 项目负责人 |")
        lines.append("|------|---------|-------|---------|---------|---------|----------|")
        for i, p in enumerate(projects, 1):
            name = p.get('project_name', '[待补充]')
            client = p.get('client', '[待补充]')
            desc = p.get('description', '')[:30]
            amount = p.get('contract_amount', '[待补充]')
            period = f"{p.get('start_date', '?')} 至 {p.get('end_date', '?')}"
            lead = p.get('lead_lawyer', '[待补充]')
            lines.append(f"| {i} | {name} | {client} | {desc} | {amount} | {period} | {lead} |")

        lines.append("")
        lines.append("> 注：以上业绩均为本律所近五年内完成的代表性项目，相关合同文件可供查验。")
        return "\n".join(lines) + "\n"

    def _gen_team_table(self, title: str, profile: Dict) -> str:
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
            role = '项目负责人' if i == 1 else ('主办律师' if i <= 3 else '协办律师')
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

    def _gen_deviation_table(self, title: str, profile: Dict) -> str:
        return f"""## {title}

| 序号 | 招标文件条款号 | 招标文件条款内容 | 偏离情况 | 说明 |
|------|-------------|----------------|---------|------|
| 1 | | | 无偏离 | 完全响应 |
| 2 | | | 无偏离 | 完全响应 |

> 本公司对招标文件商务条款无偏离，完全接受招标文件的全部商务条款要求。
"""

    def _gen_tech_deviation_table(self, title: str, profile: Dict) -> str:
        return f"""## {title}

| 序号 | 招标文件条款号 | 技术要求 | 投标人响应 | 偏离程度 | 说明 |
|------|-------------|---------|-----------|---------|------|
| 1 | | | 响应 | 无偏离 | |
| 2 | | | 响应 | 无偏离 | |

> 本公司对招标文件技术要求无偏离，完全响应招标文件的全部技术规格要求。
"""

    def _gen_review_index_table(self, title: str, profile: Dict) -> str:
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

    def _gen_shareholder_table(self, title: str, profile: Dict) -> str:
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
        cn = profile.get("company_name", "[待补充：律所名称]")
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

    def _generate_qualification_placeholder(self, title: str, hints: str, data_fields: List[str]) -> str:
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

    # ── Helpers ──

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
