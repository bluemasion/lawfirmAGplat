"""TemplateEngine — 采购文件模板引擎。

基于5份真实招标文件分析提炼的7章标准骨架结构。
支持参数化填充（须知前附表50+字段）。
"""

import json
import logging
from typing import Dict, Any, List, Optional
from copy import deepcopy

logger = logging.getLogger(__name__)


# ============================================================
# 7章标准骨架 — 所有招标/采购文件的通用结构
# ============================================================

STANDARD_SKELETON = {
    "chapters": [
        {
            "id": "ch1",
            "title": "第一章 招标公告",
            "required": True,
            "sections": [
                {"id": "ch1_s1", "title": "1. 招标条件", "type": "template"},
                {"id": "ch1_s2", "title": "2. 项目概况与招标范围", "type": "template"},
                {"id": "ch1_s3", "title": "3. 投标人资格要求", "type": "template"},
                {"id": "ch1_s4", "title": "4. 招标文件的获取", "type": "template"},
                {"id": "ch1_s5", "title": "5. 投标文件的递交", "type": "template"},
                {"id": "ch1_s6", "title": "6. 开标时间及地点", "type": "template"},
                {"id": "ch1_s7", "title": "7. 联系方式", "type": "template"},
            ],
        },
        {
            "id": "ch2",
            "title": "第二章 投标人须知",
            "required": True,
            "sections": [
                {"id": "ch2_s0", "title": "投标人须知前附表", "type": "parameter_table"},
                {"id": "ch2_s1", "title": "1. 总则", "type": "standard_clause"},
                {"id": "ch2_s2", "title": "2. 招标文件", "type": "standard_clause"},
                {"id": "ch2_s3", "title": "3. 投标文件", "type": "standard_clause"},
                {"id": "ch2_s4", "title": "4. 投标", "type": "standard_clause"},
                {"id": "ch2_s5", "title": "5. 开标", "type": "standard_clause"},
                {"id": "ch2_s6", "title": "6. 评标", "type": "standard_clause"},
                {"id": "ch2_s7", "title": "7. 合同授予", "type": "standard_clause"},
                {"id": "ch2_s8", "title": "8. 纪律和监督", "type": "standard_clause"},
            ],
        },
        {
            "id": "ch3",
            "title": "第三章 评标办法",
            "required": True,
            "sections": [
                {"id": "ch3_s0", "title": "评标办法前附表", "type": "scoring_table"},
                {"id": "ch3_s1", "title": "1. 评标方法", "type": "template"},
                {"id": "ch3_s2", "title": "2. 评审标准", "type": "template"},
                {"id": "ch3_s3", "title": "3. 评标程序", "type": "standard_clause"},
            ],
        },
        {
            "id": "ch4",
            "title": "第四章 合同条款及格式",
            "required": True,
            "sections": [
                {"id": "ch4_s1", "title": "合同条款", "type": "contract_template"},
            ],
        },
        {
            "id": "ch5",
            "title": "第五章 技术标准和要求",
            "required": True,
            "sections": [
                {"id": "ch5_s1", "title": "第一节 采购需求一览表", "type": "requirement_table"},
                {"id": "ch5_s2", "title": "第二节 技术条件", "type": "free_text"},
                {"id": "ch5_s3", "title": "第三节 工作要求", "type": "free_text"},
                {"id": "ch5_s4", "title": "第四节 人员要求", "type": "free_text"},
                {"id": "ch5_s5", "title": "第五节 验收要求", "type": "free_text"},
            ],
        },
        {
            "id": "ch6",
            "title": "第六章 投标文件格式",
            "required": True,
            "sections": [
                {"id": "ch6_s1", "title": "投标函", "type": "form_template"},
                {"id": "ch6_s2", "title": "授权委托书", "type": "form_template"},
                {"id": "ch6_s3", "title": "商务和技术偏差表", "type": "form_template"},
                {"id": "ch6_s4", "title": "分项报价表", "type": "form_template"},
                {"id": "ch6_s5", "title": "资格审查资料", "type": "form_template"},
            ],
        },
        {
            "id": "ch7",
            "title": "第七章 其他资料",
            "required": False,
            "sections": [
                {"id": "ch7_s1", "title": "附件", "type": "free_text"},
            ],
        },
    ]
}


# ============================================================
# 须知前附表 — 参数化字段定义
# ============================================================

PARAMETER_FIELDS = [
    # 基本信息
    {"id": "project_name", "label": "项目名称", "group": "基本信息", "type": "text", "required": True},
    {"id": "project_code", "label": "项目编号", "group": "基本信息", "type": "text", "required": True},
    {"id": "purchaser_name", "label": "招标人名称", "group": "基本信息", "type": "text", "required": True},
    {"id": "purchaser_address", "label": "招标人地址", "group": "基本信息", "type": "text"},
    {"id": "agent_name", "label": "招标代理机构", "group": "基本信息", "type": "text"},
    {"id": "fund_source", "label": "资金来源", "group": "基本信息", "type": "text", "default": "企业自筹"},

    # 招标范围
    {"id": "scope_description", "label": "招标范围", "group": "招标范围", "type": "textarea", "required": True},
    {"id": "service_period", "label": "服务周期", "group": "招标范围", "type": "text"},
    {"id": "service_location", "label": "服务地点", "group": "招标范围", "type": "text"},
    {"id": "quality_standard", "label": "质量标准", "group": "招标范围", "type": "text"},

    # 资格要求
    {"id": "qualification_general", "label": "基本资质要求", "group": "资格要求", "type": "textarea",
     "default": "投标人须为依照中国法律登记、注册的具有独立法人资格的企业"},
    {"id": "qualification_cert", "label": "资质证书要求", "group": "资格要求", "type": "textarea"},
    {"id": "qualification_finance", "label": "财务要求", "group": "资格要求", "type": "textarea",
     "default": "提供近3年经审计的财务报告"},
    {"id": "qualification_performance", "label": "业绩要求", "group": "资格要求", "type": "textarea"},
    {"id": "qualification_personnel", "label": "人员要求", "group": "资格要求", "type": "textarea"},
    {"id": "allow_consortium", "label": "是否允许联合体投标", "group": "资格要求", "type": "select",
     "options": ["不允许", "允许"], "default": "不允许"},
    {"id": "allow_subcontract", "label": "是否允许分包", "group": "资格要求", "type": "select",
     "options": ["不允许", "允许"], "default": "不允许"},

    # 投标要求
    {"id": "max_price", "label": "最高投标限价（元）", "group": "投标要求", "type": "number"},
    {"id": "bid_validity_days", "label": "投标有效期（天）", "group": "投标要求", "type": "number", "default": 90},
    {"id": "deposit_required", "label": "是否要求投标保证金", "group": "投标要求", "type": "select",
     "options": ["不要求", "要求"], "default": "不要求"},
    {"id": "deposit_amount", "label": "保证金金额（元）", "group": "投标要求", "type": "number"},
    {"id": "copies_original", "label": "正本份数", "group": "投标要求", "type": "number", "default": 1},
    {"id": "copies_duplicate", "label": "副本份数", "group": "投标要求", "type": "number", "default": 4},
    {"id": "electronic_required", "label": "是否要求电子版", "group": "投标要求", "type": "select",
     "options": ["否", "是"], "default": "是"},

    # 开评标
    {"id": "bid_deadline", "label": "投标截止时间", "group": "开评标", "type": "datetime"},
    {"id": "bid_location", "label": "投标文件递交地点", "group": "开评标", "type": "text"},
    {"id": "open_location", "label": "开标地点", "group": "开评标", "type": "text"},
    {"id": "eval_method", "label": "评标方法", "group": "开评标", "type": "select",
     "options": ["综合评估法", "经评审的最低投标价法", "性价比法"], "default": "综合评估法"},
    {"id": "eval_committee_size", "label": "评标委员会人数", "group": "开评标", "type": "number", "default": 5},
    {"id": "candidate_count", "label": "中标候选人数量", "group": "开评标", "type": "number", "default": 3},

    # 联系方式
    {"id": "contact_person", "label": "联系人", "group": "联系方式", "type": "text"},
    {"id": "contact_phone", "label": "联系电话", "group": "联系方式", "type": "text"},
    {"id": "contact_email", "label": "电子邮件", "group": "联系方式", "type": "text"},
]


# ============================================================
# 评标方法模板
# ============================================================

EVAL_METHOD_TEMPLATES = {
    "综合评估法": {
        "description": "本次评标采用综合评估法。评标委员会对满足招标文件实质性要求的投标文件，按照评分标准进行打分，并按得分由高到低顺序推荐中标候选人。",
        "review_layers": [
            {"name": "形式评审", "type": "pass_fail", "description": "投标文件完整性、有效性"},
            {"name": "资格评审", "type": "pass_fail", "description": "投标人资格条件"},
            {"name": "响应性评审", "type": "pass_fail", "description": "实质性响应要求"},
        ],
        "scoring_structure": {
            "commercial": {"label": "商务评分", "default_weight": 30},
            "technical": {"label": "技术评分", "default_weight": 40},
            "price": {"label": "价格评分", "default_weight": 30},
        },
        "tiebreaker": "综合评分相等时，以价格评分高者排序优先",
    },
    "经评审的最低投标价法": {
        "description": "本次评标采用经评审的最低投标价法。评标委员会对满足招标文件实质性要求的投标文件，按照经评审的投标价由低到高排序推荐中标候选人。",
        "review_layers": [
            {"name": "形式评审", "type": "pass_fail"},
            {"name": "资格评审", "type": "pass_fail"},
            {"name": "响应性评审", "type": "pass_fail"},
            {"name": "符合性审查", "type": "pass_fail"},
        ],
        "scoring_structure": None,
        "tiebreaker": "投标价相同时，由评标委员会投票决定",
    },
}


class TemplateEngine:
    """采购文件模板引擎。

    核心功能:
    1. 获取7章标准骨架
    2. 获取须知前附表参数字段定义
    3. 用参数填充模板 → 生成结构化文档内容
    4. 获取评标方法模板
    """

    def get_skeleton(self) -> Dict[str, Any]:
        """获取7章标准骨架结构"""
        return deepcopy(STANDARD_SKELETON)

    def get_parameter_fields(self) -> List[Dict[str, Any]]:
        """获取须知前附表的参数字段定义"""
        return deepcopy(PARAMETER_FIELDS)

    def get_parameter_groups(self) -> List[str]:
        """获取参数分组列表"""
        groups = []
        seen = set()
        for f in PARAMETER_FIELDS:
            g = f["group"]
            if g not in seen:
                groups.append(g)
                seen.add(g)
        return groups

    def get_eval_methods(self) -> Dict[str, Any]:
        """获取评标方法模板"""
        return deepcopy(EVAL_METHOD_TEMPLATES)

    def fill_template(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """用参数填充模板，生成结构化的采购文件内容。

        Args:
            parameters: 须知前附表参数值 {field_id: value}

        Returns:
            结构化的文档内容 (可直接传给 DocBuilder 生成 Word)
        """
        skeleton = self.get_skeleton()
        eval_method = parameters.get("eval_method", "综合评估法")
        eval_template = EVAL_METHOD_TEMPLATES.get(eval_method, EVAL_METHOD_TEMPLATES["综合评估法"])

        # Resolve scoring_criteria: if items are string IDs, expand to full objects
        scoring_criteria = parameters.get("scoring_criteria", {})
        if scoring_criteria:
            commercial_items = scoring_criteria.get("commercial_items", [])
            technical_items = scoring_criteria.get("technical_items", [])
            if commercial_items and isinstance(commercial_items[0], str):
                from app.core.skills.procurement.scoring_template import ScoringTemplateLibrary
                lib = ScoringTemplateLibrary()
                scoring_criteria = lib.build_scoring_criteria(
                    commercial_item_ids=commercial_items,
                    technical_item_ids=technical_items if technical_items and isinstance(technical_items[0], str) else [],
                    score_distribution=scoring_criteria.get("score_distribution", {"commercial": 30, "technical": 40, "price": 30}),
                    price_formula=scoring_criteria.get("price_formula", "arithmetic_mean"),
                )

        document = {
            "metadata": {
                "project_name": parameters.get("project_name", ""),
                "project_code": parameters.get("project_code", ""),
                "purchaser_name": parameters.get("purchaser_name", ""),
                "eval_method": eval_method,
                "created_at": None,
            },
            "parameters": parameters,
            "skeleton": skeleton,
            "eval_template": eval_template,
            "scoring_criteria": scoring_criteria,
            "chapters": self._generate_chapters(parameters, eval_template),
        }

        return document

    def _generate_chapters(self, params: Dict, eval_template: Dict) -> List[Dict]:
        """根据参数生成各章节内容"""
        chapters = [
            {"id": "ch1", "title": "第一章 招标公告", "content": self._gen_chapter1(params)},
            {"id": "ch2", "title": "第二章 投标人须知", "content": self._gen_chapter2(params)},
            {"id": "ch3", "title": "第三章 评标办法", "content": self._gen_chapter3(params, eval_template)},
            {"id": "ch4", "title": "第四章 合同条款及格式", "content": self._gen_chapter4(params)},
            {"id": "ch5", "title": "第五章 技术标准和要求", "content": self._gen_chapter5(params)},
            {"id": "ch6", "title": "第六章 投标文件格式", "content": self._gen_chapter6(params)},
            {"id": "ch7", "title": "第七章 其他资料", "content": self._gen_chapter7(params)},
        ]
        return chapters

    # ── Helpers ──

    @staticmethod
    def _v(params, key, default="____"):
        """Get param value or placeholder."""
        val = params.get(key, "")
        return val if val else default

    # ════════════════════════════════════════════════════════
    # 第一章 招标公告
    # ════════════════════════════════════════════════════════
    def _gen_chapter1(self, p: Dict) -> str:
        v = self._v
        name = v(p, "project_name")
        code = v(p, "project_code")
        purchaser = v(p, "purchaser_name")
        scope = v(p, "scope_description", "详见招标文件")
        method_map = {
            "open_bidding": "公开招标", "negotiation": "竞争性磋商",
            "competitive_talk": "竞争性谈判", "inquiry": "询价",
            "sole_source": "单一来源", "framework": "框架协议",
        }
        method = p.get("method", "open_bidding")
        method_label = method_map.get(method, method) if method else "公开招标"

        return f"""{purchaser}
{name}
（项目编号：{code}）

一、招标条件

{name}（项目编号：{code}），招标人为{purchaser}，招标项目资金来自{v(p, 'fund_source', '企业自筹')}。该项目已具备招标条件，现进行{method_label}，欢迎符合条件的供应商参加投标。

二、项目概况与招标范围

2.1 项目概况：{scope}
2.2 服务周期：{v(p, 'service_period', '详见招标文件')}
2.3 服务地点：{v(p, 'service_location', '招标人指定地点')}
2.4 质量标准：{v(p, 'quality_standard', '满足国家及行业相关标准')}
2.5 最高投标限价：{v(p, 'max_price', '无') if p.get('max_price') else '无最高投标限价'}

三、投标人资格要求

3.1 基本资格条件：
{v(p, 'qualification_general', '投标人须为依照中国法律登记、注册的具有独立法人资格的企业')}

3.2 资质证书要求：
{v(p, 'qualification_cert', '详见招标文件')}

3.3 财务要求：
{v(p, 'qualification_finance', '提供近3年经审计的财务报告')}

3.4 业绩要求：
{v(p, 'qualification_performance', '详见招标文件')}

3.5 人员要求：
{v(p, 'qualification_personnel', '详见招标文件')}

3.6 联合体投标：本项目{v(p, 'allow_consortium', '不允许')}联合体投标。
3.7 分包：本项目{v(p, 'allow_subcontract', '不允许')}分包。
3.8 投标人不得存在下列情形之一：
（1）被依法暂停或取消投标资格的；
（2）被责令停业、暂扣或吊销许可证、营业执照的；
（3）财产被接管、冻结或处于破产状态的；
（4）在最近三年内有骗取中标或严重违约行为的；
（5）法律法规规定的其他不得参加投标的情形。

四、招标文件的获取

4.1 凡符合资格要求的投标人，请于公告之日起至投标截止时间前，持下列材料到{v(p, 'purchaser_address', '招标人指定地点')}获取招标文件：
（1）营业执照副本复印件（加盖公章）；
（2）法人授权委托书及被授权人身份证复印件。
4.2 招标文件每套售价人民币____元（售后不退），如需邮寄另加____元。

五、投标文件的递交

5.1 投标截止时间：{v(p, 'bid_deadline', '详见招标文件')}
5.2 递交地点：{v(p, 'bid_location', '详见招标文件')}
5.3 逾期送达的或者未送达指定地点的投标文件，招标人不予受理。
5.4 投标文件正本{v(p, 'copies_original', '1')}份，副本{v(p, 'copies_duplicate', '4')}份{('，电子版U盘1份' if p.get('electronic_required') == '是' else '')}。

六、开标时间及地点

6.1 开标时间：{v(p, 'bid_deadline', '同投标截止时间')}
6.2 开标地点：{v(p, 'open_location', '详见招标文件')}
6.3 届时请投标人的法定代表人或其授权的投标人代表出席开标仪式。

七、联系方式

招标人：{purchaser}
地  址：{v(p, 'purchaser_address')}
联系人：{v(p, 'contact_person')}
电  话：{v(p, 'contact_phone')}
邮  箱：{v(p, 'contact_email')}
{f'招标代理机构：{p["agent_name"]}' if p.get('agent_name') else ''}
"""

    # ════════════════════════════════════════════════════════
    # 第二章 投标人须知
    # ════════════════════════════════════════════════════════
    def _gen_chapter2(self, p: Dict) -> str:
        v = self._v
        deposit_clause = ""
        if p.get("deposit_required") == "要求" and p.get("deposit_amount"):
            deposit_clause = f"""
4.4 投标保证金
4.4.1 投标人应在投标截止时间前，以银行转账方式向招标人提交投标保证金人民币{v(p, 'deposit_amount')}元。
4.4.2 未按要求提交投标保证金的投标文件，招标人将予以拒绝。
4.4.3 投标保证金退还：未中标人的投标保证金，在中标通知书发出后5个工作日内退还（不计利息）；中标人的投标保证金在签订合同后5个工作日内退还（不计利息）。
4.4.4 有下列情形之一的，投标保证金将不予退还：
（1）投标人在投标有效期内撤销投标文件的；
（2）中标人无正当理由不与招标人签订合同的；
（3）中标人在签订合同时，向招标人提出附加条件的。"""
        else:
            deposit_clause = "\n4.4 投标保证金\n本项目不要求缴纳投标保证金。"

        return f"""投标人须知前附表

┌──────────────────────┬──────────────────────────────────────────┐
│ 项  目               │ 内  容                                   │
├──────────────────────┼──────────────────────────────────────────┤
│ 项目名称             │ {v(p, 'project_name')}                   │
│ 项目编号             │ {v(p, 'project_code')}                   │
│ 招标人               │ {v(p, 'purchaser_name')}                 │
│ 招标代理             │ {v(p, 'agent_name', '无')}               │
│ 资金来源             │ {v(p, 'fund_source', '企业自筹')}        │
│ 招标范围             │ {v(p, 'scope_description', '')}          │
│ 服务周期             │ {v(p, 'service_period', '')}             │
│ 服务地点             │ {v(p, 'service_location', '')}           │
│ 质量标准             │ {v(p, 'quality_standard', '国家及行业标准')} │
│ 最高限价             │ {v(p, 'max_price', '无') if p.get('max_price') else '无'} │
│ 投标有效期           │ {v(p, 'bid_validity_days', '90')}天      │
│ 投标保证金           │ {f"人民币{v(p, 'deposit_amount')}元" if p.get('deposit_required') == '要求' else '不要求'} │
│ 联合体投标           │ {v(p, 'allow_consortium', '不允许')}      │
│ 分包                 │ {v(p, 'allow_subcontract', '不允许')}     │
│ 正本份数             │ {v(p, 'copies_original', '1')}份         │
│ 副本份数             │ {v(p, 'copies_duplicate', '4')}份        │
│ 是否要求电子版       │ {v(p, 'electronic_required', '是')}       │
│ 评标方法             │ {v(p, 'eval_method', '综合评估法')}       │
│ 评标委员会人数       │ {v(p, 'eval_committee_size', '5')}人     │
│ 中标候选人数量       │ {v(p, 'candidate_count', '3')}名         │
│ 投标截止时间         │ {v(p, 'bid_deadline', '详见公告')}        │
│ 开标地点             │ {v(p, 'open_location', '详见公告')}       │
└──────────────────────┴──────────────────────────────────────────┘


投标人须知正文

一、总则

1.1 适用范围
本招标文件仅适用于本次招标项目，投标人应认真阅读招标文件的所有内容，按照招标文件的要求编制投标文件，并保证所提供的全部资料的真实性，否则其投标将被拒绝。

1.2 合格的投标人
投标人应具备招标公告中规定的资格条件，并提供相应证明材料。

1.3 投标费用
投标人应自行承担所有与准备和参加投标有关的费用。不论投标结果如何，招标人在任何情况下均无义务和责任承担这些费用。

1.4 保密
参与投标活动的各方应对招标文件和投标文件中的商业和技术等秘密保密。

二、招标文件

2.1 招标文件的构成
招标文件由下列各部分组成：
（1）第一章 招标公告
（2）第二章 投标人须知（含须知前附表）
（3）第三章 评标办法
（4）第四章 合同条款及格式
（5）第五章 技术标准和要求
（6）第六章 投标文件格式
（7）第七章 其他资料

2.2 招标文件的澄清
投标人如对招标文件有任何疑问，应在投标截止时间前以书面形式向招标人提出澄清请求。招标人将以书面形式予以答复并通知所有已获取招标文件的投标人，但不指明问题的来源。

2.3 招标文件的修改
招标人有权在投标截止时间至少15日前，以补充通知的方式对招标文件进行修改。补充通知是招标文件的组成部分，对所有投标人具有约束力。

三、投标文件

3.1 投标文件的编制
投标文件应按招标文件第六章规定的格式编制，包括但不限于：投标函、法人授权委托书、技术方案、商务方案、投标报价、资格审查资料等。

3.2 投标文件的语言
投标文件及有关资料均使用中文。

3.3 投标报价
3.3.1 投标报价应为完成本项目全部工作内容的含税全包价（包含但不限于人工费、管理费、利润、税金及其他相关费用）。
3.3.2 投标报价不得超过招标文件规定的最高投标限价（如有）。
3.3.3 投标报价为固定总价，合同履行期间不做调整。

3.4 投标有效期
3.4.1 投标有效期为自投标截止之日起{v(p, 'bid_validity_days', '90')}个日历天。
3.4.2 在投标有效期内，投标人不得撤销投标文件。

四、投标
{deposit_clause}

4.5 投标文件的密封和标记
4.5.1 投标人应将投标文件正本与副本分别密封。
4.5.2 密封的投标文件封面上应注明：项目名称、项目编号、投标人名称及"正本"或"副本"字样。
4.5.3 未按以上要求密封和标记的投标文件，招标人有权拒收。

4.6 投标文件的递交
4.6.1 投标人应在投标截止时间前将投标文件送达指定地点。
4.6.2 招标人收到投标文件后，应向投标人出具签收凭据。
4.6.3 在投标截止时间后送达的投标文件，为无效投标文件，招标人将予以拒收。

4.7 投标文件的补充、修改和撤回
4.7.1 在投标截止时间前，投标人可以补充、修改或撤回已递交的投标文件。
4.7.2 补充和修改的内容应按招标文件的要求签署、盖章并密封，作为投标文件的组成部分。

五、开标

5.1 开标时间和地点按招标公告规定执行。
5.2 开标由招标人或其委托的招标代理机构主持。
5.3 开标时，将当众宣读投标人名称、投标报价及其他主要内容。
5.4 开标过程由公证机构进行公证。

六、评标

6.1 评标委员会
6.1.1 评标委员会由招标人依法组建，由{v(p, 'eval_committee_size', '5')}人以上单数组成，其中技术、经济等方面的专家不少于成员总数的三分之二。
6.1.2 评标委员会成员名单在中标结果确定前应当保密。

6.2 评标原则
评标活动遵循公平、公正、科学、择优的原则。

6.3 评标方法
详见第三章评标办法。

6.4 废标条件
有下列情形之一的，按废标处理：
（1）投标文件未按要求密封的；
（2）投标文件未按要求加盖投标人公章及法定代表人或被授权代表签字的；
（3）投标文件中的投标函、投标报价表（开标一览表）未加盖投标人公章及法定代表人或被授权代表签字的；
（4）投标人不具备招标文件中规定的资格条件的；
（5）投标报价超过招标文件规定的最高投标限价的；
（6）同一投标人提交两个以上不同的投标文件，但招标文件要求提交备选方案的除外；
（7）投标有效期不满足招标文件要求的；
（8）投标人对招标文件的实质性要求和条件未作出响应的；
（9）法律法规规定的其他情形。

七、合同授予

7.1 中标候选人公示
评标委员会将按照评标办法推荐不超过{v(p, 'candidate_count', '3')}名中标候选人，并进行不少于3日的公示。

7.2 中标通知书
公示期满无异议的，招标人向中标人发出中标通知书。中标通知书对招标人和中标人具有法律约束力。

7.3 签订合同
招标人和中标人应自中标通知书发出之日起30日内签订书面合同。合同的主要条款与招标文件和中标人的投标文件一致。

八、纪律和监督

8.1 招标人不得泄漏评标委员会成员名单、投标文件的评审和比较情况以及中标候选人的推荐情况。
8.2 评标委员会成员不得与投标人私下接触，不得收受利益，不得透露评标过程中的相关情况。
8.3 投标人不得相互串通投标，不得以向招标人或评标委员会成员行贿手段谋取中标。
8.4 投标人不得以低于成本的报价竞标，也不得以他人名义投标或以其他方式弄虚作假。
8.5 对违反纪律的行为，招标人有权取消其投标资格或中标资格，并报请有关部门依法处理。
"""

    # ════════════════════════════════════════════════════════
    # 第三章 评标办法
    # ════════════════════════════════════════════════════════
    def _gen_chapter3(self, p: Dict, eval_tpl: Dict) -> str:
        v = self._v
        method = v(p, "eval_method", "综合评估法")

        scoring = p.get("scoring_criteria", {})
        dist = scoring.get("score_distribution", {})
        dist_text = ""
        if dist:
            dist_text = "分值构成（总分100分）：\n"
            label_map = {"commercial": "商务部分", "technical": "技术部分", "price": "价格部分"}
            for k, val in dist.items():
                dist_text += f"  {label_map.get(k, k)}：{val}分\n"

        return f"""评标办法前附表

┌──────────────────────┬──────────────────────────────────────────┐
│ 项  目               │ 内  容                                   │
├──────────────────────┼──────────────────────────────────────────┤
│ 评标方法             │ {method}                                 │
│ 评标委员会人数       │ {v(p, 'eval_committee_size', '5')}人     │
│ 中标候选人数量       │ {v(p, 'candidate_count', '3')}名         │
└──────────────────────┴──────────────────────────────────────────┘


一、评标方法

本次评标采用{method}。{eval_tpl.get('description', '')}

二、评审标准

2.1 初步评审

初步评审分为形式评审、资格评审和响应性评审。

2.1.1 形式评审标准
（1）投标文件按照招标文件规定的格式、内容填写，字迹清晰可辨；
（2）投标函按招标文件规定填报了项目名称、标段号、投标价（如有）、工期、工程质量标准；
（3）投标文件由法定代表人或其委托的代理人签字或盖章；
（4）投标文件载明的招标项目完成期限未超过招标文件规定的期限；
（5）投标文件中未出现有关组价的组成、说明等实质性内容应密封而未密封的情况。

2.1.2 资格评审标准
（1）投标人具备有效的营业执照；
（2）投标人具备本招标文件第一章规定的资格条件；
（3）投标人不存在第二章规定的不得参加投标的情形；
（4）投标人符合法律法规规定的其他资格条件。

2.1.3 响应性评审标准
（1）投标文件实质性响应了招标文件的所有实质性要求和条件；
（2）投标人对合同主要条款无重大偏离。

2.2 详细评审

{dist_text}

（评分标准详细表格见附表）

{eval_tpl.get('tiebreaker', '综合评分相等时，以价格评分高者排序优先')}。

三、评标程序

3.1 第一阶段：初步评审
评标委员会对每个投标文件进行形式评审、资格评审和响应性评审。不符合初步评审条件的投标文件按废标处理。

3.2 第二阶段：详细评审
评标委员会按照评分标准对通过初步评审的投标文件进行评分，并计算综合得分。

3.3 第三阶段：推荐中标候选人
评标委员会按照综合得分由高到低的顺序推荐不超过{v(p, 'candidate_count', '3')}名中标候选人。

3.4 评标报告
评标委员会完成评标后，应当向招标人提交书面评标报告，并推荐合格的中标候选人。评标报告由评标委员会全体成员签字。
"""

    # ════════════════════════════════════════════════════════
    # 第四章 合同条款及格式
    # ════════════════════════════════════════════════════════
    def _gen_chapter4(self, p: Dict) -> str:
        v = self._v
        return f"""合同主要条款

第一条 合同双方

甲方（招标人/采购人）：{v(p, 'purchaser_name')}
乙方（中标人/供应商）：（以中标通知书为准）

第二条 服务内容及范围

2.1 服务内容：{v(p, 'scope_description', '详见招标文件第五章')}
2.2 服务地点：{v(p, 'service_location', '甲方指定地点')}
2.3 服务周期：{v(p, 'service_period', '详见招标文件')}
2.4 质量标准：{v(p, 'quality_standard', '满足国家及行业相关标准')}

第三条 合同价格

3.1 合同价格以中标价为准。
3.2 合同价格为含税全包价，包含但不限于乙方完成全部合同义务所需的人工费、管理费、利润、税金及其他相关费用。
3.3 合同执行期间，合同价格不做调整，甲方不再支付任何额外费用。

第四条 支付方式

4.1 合同签订后____个工作日内，甲方向乙方支付合同价格的____%作为预付款。
4.2 服务期间按____（月/季度）结算，每期经甲方验收合格后____个工作日内支付该期服务费用。
4.3 合同到期并经甲方最终验收合格后____个工作日内，支付剩余款项。
4.4 乙方应提供合法有效的增值税专用发票。

第五条 双方权利与义务

5.1 甲方权利和义务：
（1）有权对乙方的服务质量进行监督和检查；
（2）有权要求乙方按合同约定履行义务；
（3）应及时为乙方提供必要的工作条件；
（4）应按合同约定及时支付费用。

5.2 乙方权利和义务：
（1）应按照合同约定和甲方要求提供服务；
（2）应保证服务质量符合合同及招标文件的要求；
（3）应指派合格的服务人员执行合同；
（4）未经甲方书面同意，不得转让或分包合同；
（5）应对因提供服务而获知的甲方商业秘密和技术秘密予以保密。

第六条 验收

6.1 乙方完成约定服务后，应书面通知甲方进行验收。
6.2 甲方应在收到验收通知后____个工作日内组织验收。
6.3 验收不合格的，乙方应在甲方规定的期限内整改并重新提交验收。
6.4 验收标准：详见第五章技术标准和要求。

第七条 违约责任

7.1 甲方违约：
（1）甲方无正当理由逾期支付合同款项的，每逾期一天按应付金额的0.05%向乙方支付违约金。

7.2 乙方违约：
（1）乙方未按合同约定提供服务或服务质量不符合要求的，甲方有权要求整改；连续两次整改不合格的，甲方有权解除合同；
（2）乙方逾期提供服务的，每逾期一天按合同金额的0.05%向甲方支付违约金；
（3）因乙方原因给甲方造成损失的，乙方应予以赔偿。

第八条 保密条款

8.1 双方对合同内容及因执行合同而获知的对方商业秘密、技术秘密负有保密义务。
8.2 保密期限自合同签订之日起至合同终止后____年止。

第九条 不可抗力

9.1 因不可抗力事件导致合同无法履行的，受影响方应在事件发生后____日内通知对方，并提供相关证明。
9.2 因不可抗力导致合同无法继续履行的，双方可协商解除合同，互不承担违约责任。

第十条 争议解决

10.1 因合同引起的或与合同有关的争议，双方应首先通过友好协商解决。
10.2 协商不成的，任何一方均可向甲方所在地有管辖权的人民法院提起诉讼。

第十一条 合同生效与终止

11.1 合同自双方签字盖章之日起生效。
11.2 合同期满或双方协商一致时终止。
11.3 本合同一式____份，甲乙双方各持____份，具有同等法律效力。


甲方（盖章）：                    乙方（盖章）：
法定代表人或授权代表：             法定代表人或授权代表：
日期：                             日期：
"""

    # ════════════════════════════════════════════════════════
    # 第五章 技术标准和要求
    # ════════════════════════════════════════════════════════
    def _gen_chapter5(self, p: Dict) -> str:
        v = self._v
        return f"""第一节 采购需求一览表

┌────┬────────────────────┬──────────┬──────────────────────┐
│序号│ 服务内容            │ 数量/规模 │ 技术要求/标准         │
├────┼────────────────────┼──────────┼──────────────────────┤
│ 1  │ {v(p, 'scope_description', '详见下文')} │ 详见下文 │ 满足本章要求         │
└────┴────────────────────┴──────────┴──────────────────────┘

第二节 技术条件

一、总体要求

1.1 投标人应深入理解项目需求，提供完整的服务方案，确保服务质量满足招标人要求。
1.2 投标人应具备完成本项目所需的技术能力和管理水平。
1.3 投标人提供的服务应符合国家及行业相关标准和规范。

二、具体技术要求

2.1 服务范围：{v(p, 'scope_description', '详见招标文件')}
2.2 质量标准：{v(p, 'quality_standard', '满足国家及行业相关标准')}
2.3 服务周期：{v(p, 'service_period', '详见合同约定')}

第三节 工作要求

一、服务实施要求

1.1 投标人应制定详细的服务实施方案，包括工作计划、人员安排、质量保证措施等。
1.2 投标人应定期向招标人汇报服务进展情况。
1.3 投标人应建立有效的沟通机制，及时响应招标人的需求和反馈。

二、应急保障要求

2.1 投标人应制定应急响应预案，确保在突发情况下能够及时有效地处理问题。
2.2 应急响应时间不超过____小时。

三、安全保密要求

3.1 投标人应严格遵守招标人的安全管理规定。
3.2 投标人应对因提供服务而获知的招标人信息严格保密。
3.3 未经招标人书面同意，不得将项目相关信息透露给任何第三方。

第四节 人员要求

一、人员配置

1.1 投标人应配备足够的、具有相关资质和经验的专业人员。
1.2 项目经理应具有____年以上相关工作经验。
1.3 核心团队成员应保持稳定，未经招标人同意不得随意更换。

二、人员管理

2.1 投标人应对项目人员进行统一管理，确保服务质量。
2.2 投标人应定期对项目人员进行培训，提高业务水平。

第五节 验收要求

一、验收标准

1.1 服务成果应符合本章规定的技术标准和要求。
1.2 服务过程应符合合同约定和招标文件要求。

二、验收方式

2.1 阶段验收：按照合同约定的周期进行阶段性验收。
2.2 最终验收：合同到期后进行最终验收，出具验收报告。

三、考核方式

3.1 招标人将按照合同约定对投标人的服务质量进行定期考核。
3.2 考核结果将作为服务费用支付和合同续签的重要依据。
"""

    # ════════════════════════════════════════════════════════
    # 第六章 投标文件格式
    # ════════════════════════════════════════════════════════
    def _gen_chapter6(self, p: Dict) -> str:
        v = self._v
        name = v(p, "project_name")
        code = v(p, "project_code")
        purchaser = v(p, "purchaser_name")

        consortium_form = ""
        if p.get("allow_consortium") == "允许":
            consortium_form = f"""

格式五：联合体协议书

联合体协议书

{name}（项目编号：{code}）

经协商，下列各方组成联合体，共同参加本项目的投标。

联合体牵头方：____________________
联合体成员方：____________________

一、联合体各方的责任和义务：
（1）牵头方为联合体的主办方，负责联合体的投标及合同的签署、执行等事宜。
（2）各成员方按约定分工承担相应的工作内容。

二、联合体各方按以下比例分配工作：
牵头方承担____%的工作量。
成员方承担____%的工作量。

三、联合体各方对本协议的一切事宜承担连带责任。

牵头方（盖章）：               成员方（盖章）：
法定代表人签字：               法定代表人签字：
日期：                         日期：
"""

        return f"""格式一：投标函

投 标 函

致：{purchaser}

1. 我方已仔细研究了{name}（项目编号：{code}）招标文件的全部内容，愿意以人民币（大写）_____元整（¥_________元）的投标总价，按照招标文件规定的各项要求向贵方提供服务。

2. 我方完全接受招标文件的所有内容和条件。我方一旦中标，将严格按照招标文件和投标文件的要求履行合同义务。

3. 我方承诺投标文件在投标截止日期起{v(p, 'bid_validity_days', '90')}个日历天内有效。在此期间，我方的投标文件始终对我方具有约束力，并可在任何时间被接受。

4. 如我方中标，我方保证在收到中标通知书后30日内与贵方签订合同。

5. 我方声明，在投标有效期内不撤销投标文件。

6. 我方理解，贵方不一定接受最低投标价或任何投标。

投标人名称（盖章）：
法定代表人或其授权代表（签字）：
地址：
联系电话：
传真/邮箱：
日期：


格式二：法人授权委托书

法人授权委托书

致：{purchaser}

本授权委托书声明：注册于（国家或地区）____的____(投标人名称)的法定代表人____（姓名、职务），授权____（被授权人姓名、职务）为我方参加{name}（项目编号：{code}）投标活动的合法代理人。

被授权人代表我方全权处理与本次投标有关的一切事宜。

本授权委托书有效期至本项目招标活动结束。

投标人名称（盖章）：
法定代表人（签字）：
被授权人（签字）：
被授权人身份证号：
授权日期：


格式三：开标一览表

┌──────────────┬────────────────────────────────────┐
│ 项  目       │ 内  容                             │
├──────────────┼────────────────────────────────────┤
│ 项目名称     │ {name}                             │
│ 项目编号     │ {code}                             │
│ 投标人名称   │ （投标人填写）                     │
│ 投标总价     │ 人民币（大写）__________元整       │
│              │ （¥__________元）                  │
│ 服务周期     │ （投标人填写）                     │
│ 质量标准     │ 满足招标文件要求                   │
│ 投标有效期   │ {v(p, 'bid_validity_days', '90')}天 │
└──────────────┴────────────────────────────────────┘

投标人名称（盖章）：
法定代表人或其授权代表（签字）：
日期：


格式四：商务和技术偏离表

商务偏离表

┌────┬────────────────┬────────────────┬────────────────┐
│序号│ 招标文件条款号  │ 招标文件要求    │ 投标人响应/偏离 │
├────┼────────────────┼────────────────┼────────────────┤
│    │                │                │                │
└────┴────────────────┴────────────────┴────────────────┘

技术偏离表

┌────┬────────────────┬────────────────┬────────────────┐
│序号│ 招标文件条款号  │ 招标文件要求    │ 投标人响应/偏离 │
├────┼────────────────┼────────────────┼────────────────┤
│    │                │                │                │
└────┴────────────────┴────────────────┴────────────────┘

说明：偏离栏填写"无偏离"表示完全响应，如有偏离请详细说明偏离内容及原因。

投标人名称（盖章）：
法定代表人或其授权代表（签字）：
日期：
{consortium_form}

格式六：资格审查资料清单

投标人须提供以下资格审查资料（复印件加盖公章）：

┌────┬──────────────────────────────────┬──────────┐
│序号│ 资料名称                          │ 备  注   │
├────┼──────────────────────────────────┼──────────┤
│ 1  │ 企业营业执照副本                  │ 必须     │
│ 2  │ 法定代表人身份证                  │ 必须     │
│ 3  │ 法人授权委托书及被授权人身份证    │ 如代理   │
│ 4  │ 近三年经审计的财务报告            │ 必须     │
│ 5  │ 相关资质证书                      │ 如要求   │
│ 6  │ 类似项目业绩证明                  │ 如要求   │
│ 7  │ 拟投入人员简历及资格证书          │ 如要求   │
│ 8  │ 无重大违法记录声明                │ 必须     │
│ 9  │ 投标人认为需要提供的其他材料      │ 选填     │
└────┴──────────────────────────────────┴──────────┘
"""

    # ════════════════════════════════════════════════════════
    # 第七章 其他资料
    # ════════════════════════════════════════════════════════
    def _gen_chapter7(self, p: Dict) -> str:
        v = self._v
        return f"""一、招标文件澄清

1.1 投标人如对招标文件有任何疑问，可在投标截止时间前____日以书面形式向招标人提出澄清请求。
1.2 澄清请求应以书面形式发送至：
    联系人：{v(p, 'contact_person')}
    电  话：{v(p, 'contact_phone')}
    邮  箱：{v(p, 'contact_email')}

1.3 招标人将以书面形式（补充通知）予以答复，补充通知将同时发送给所有已获取招标文件的投标人。

二、现场踏勘

2.1 招标人不组织统一现场踏勘。投标人可自行前往项目现场进行踏勘。
2.2 投标人自行踏勘产生的费用由投标人自行承担。

三、投标人须知

3.1 投标人在投标前应详细了解招标文件所有条款，如有疑问应及时以书面方式提出，未提出疑问视为完全理解和接受招标文件所有内容。
3.2 投标人应充分考虑各种风险因素，自行对投标报价负责。
3.3 招标人有权根据项目需要对本招标文件的内容进行补充和修改。

四、附件清单

（1）须知前附表——详见第二章
（2）评标办法前附表——详见第三章
（3）合同格式——详见第四章
（4）技术标准和要求——详见第五章
（5）投标文件格式——详见第六章

五、其他说明

5.1 本招标文件解释权归招标人所有。
5.2 招标文件中未尽事宜，按照国家有关法律法规执行。
5.3 本招标文件各章节之间如有矛盾，以招标文件的澄清和补充通知为准；如无澄清和补充通知，以各章节中对投标人要求较严格的条款为准。
"""

