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
            "scoring_criteria": parameters.get("scoring_criteria", {}),
            "chapters": self._generate_chapters(parameters, eval_template),
        }

        return document

    def _generate_chapters(self, params: Dict, eval_template: Dict) -> List[Dict]:
        """根据参数生成各章节内容"""
        chapters = []

        # 第一章：招标公告
        chapters.append({
            "id": "ch1",
            "title": "第一章 招标公告",
            "content": self._gen_chapter1(params),
        })

        # 第二章：投标人须知
        chapters.append({
            "id": "ch2",
            "title": "第二章 投标人须知",
            "content": self._gen_chapter2(params),
        })

        # 第三章：评标办法
        chapters.append({
            "id": "ch3",
            "title": "第三章 评标办法",
            "content": self._gen_chapter3(params, eval_template),
        })

        # 第四章~第七章: 基本框架
        for ch_id, title in [
            ("ch4", "第四章 合同条款及格式"),
            ("ch5", "第五章 技术标准和要求"),
            ("ch6", "第六章 投标文件格式"),
            ("ch7", "第七章 其他资料"),
        ]:
            chapters.append({"id": ch_id, "title": title, "content": ""})

        return chapters

    def _gen_chapter1(self, p: Dict) -> str:
        """生成第一章：招标公告"""
        name = p.get("project_name", "____")
        code = p.get("project_code", "____")
        purchaser = p.get("purchaser_name", "____")
        scope = p.get("scope_description", "详见招标文件")

        return f"""{purchaser}
{name}
（项目编号：{code}）

1．招标条件
{name}（项目编号：{code}）招标人为{purchaser}，招标项目资金来自{p.get('fund_source', '企业自筹')}。该项目已具备招标条件，现进行公开招标。

2．项目概况与招标范围
{scope}

3．投标人资格要求
{p.get('qualification_general', '')}
{p.get('qualification_cert', '')}
{p.get('qualification_finance', '')}
{p.get('qualification_performance', '')}
{p.get('qualification_personnel', '')}

4．联系方式
联系人：{p.get('contact_person', '____')}
电话：{p.get('contact_phone', '____')}
邮箱：{p.get('contact_email', '____')}
"""

    def _gen_chapter2(self, p: Dict) -> str:
        """生成第二章：投标人须知（须知前附表+正文条款）"""
        return f"""投标人须知前附表

项目名称：{p.get('project_name', '')}
项目编号：{p.get('project_code', '')}
招标人：{p.get('purchaser_name', '')}
招标代理：{p.get('agent_name', '无')}
资金来源：{p.get('fund_source', '企业自筹')}
招标范围：{p.get('scope_description', '')}
服务周期：{p.get('service_period', '')}
服务地点：{p.get('service_location', '')}
最高限价：{p.get('max_price', '无') or '无'}
投标有效期：{p.get('bid_validity_days', 90)}天
投标保证金：{p.get('deposit_required', '不要求')}
联合体投标：{p.get('allow_consortium', '不允许')}
分包：{p.get('allow_subcontract', '不允许')}
正本份数：{p.get('copies_original', 1)}
副本份数：{p.get('copies_duplicate', 4)}
"""

    def _gen_chapter3(self, p: Dict, eval_tpl: Dict) -> str:
        """生成第三章：评标办法"""
        method = p.get("eval_method", "综合评估法")
        content = f"""评标办法（{method}）

{eval_tpl.get('description', '')}

评审标准：

"""
        scoring = p.get("scoring_criteria", {})
        if scoring:
            dist = scoring.get("score_distribution", {})
            if dist:
                content += "分值构成（总分100分）：\n"
                for k, v in dist.items():
                    label = {"commercial": "商务部分", "technical": "技术部分", "price": "价格部分"}.get(k, k)
                    content += f"  {label}：{v}分\n"

        return content
