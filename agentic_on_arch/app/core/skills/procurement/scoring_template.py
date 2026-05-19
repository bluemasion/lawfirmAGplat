"""ScoringTemplate — 评分标准模板库。

基于5份真实招标文件提炼的评分项模板。
支持按行业/项目类型推荐评分项组合。
"""

import logging
from typing import Dict, Any, List, Optional
from copy import deepcopy

logger = logging.getLogger(__name__)


# ============================================================
# 商务评分模板项
# ============================================================

COMMERCIAL_SCORING_ITEMS = [
    {
        "id": "cs_cert",
        "name": "企业资质证书",
        "category": "commercial",
        "default_score": 10,
        "description": "投标人提供的有效资质证书。高新技术企业证书、CMMI/ITSS认证、ISO体系认证等。",
        "scoring_guide": "根据证书数量和等级进行评分",
        "common_in": ["IT服务", "软件开发", "工程"],
        "frequency": 5,  # 5份样例中出现次数
    },
    {
        "id": "cs_performance",
        "name": "企业业绩",
        "category": "commercial",
        "default_score": 10,
        "description": "投标人近3年内与本次招标内容相同或类似的业绩。以合同签订时间为准。",
        "scoring_guide": "按业绩数量/金额分档: ≥5个得满分, 3-4个得70%, 1-2个得50%",
        "common_in": ["通用"],
        "frequency": 5,
    },
    {
        "id": "cs_finance",
        "name": "财务状况",
        "category": "commercial",
        "default_score": 10,
        "description": "企业财务状况和偿债能力分析。根据审计报告中的资产负债率、营业收入等指标评分。",
        "scoring_guide": "资产负债率≤50%得满分; 50%-70%得70%; >70%得50%",
        "common_in": ["通用"],
        "frequency": 3,
    },
    {
        "id": "cs_team",
        "name": "项目团队人员",
        "category": "commercial",
        "default_score": 5,
        "description": "投标人拟投入本项目的团队人员构成、学历、资质、社保缴存记录等。",
        "scoring_guide": "根据人员数量、学历结构、专业资质、工作经验综合评分",
        "common_in": ["IT服务", "咨询", "工程"],
        "frequency": 4,
    },
    {
        "id": "cs_local",
        "name": "本地化服务保障",
        "category": "commercial",
        "default_score": 5,
        "description": "投标人在项目所在地的本地服务能力，包括本地办公场所、驻场人员等。",
        "scoring_guide": "有本地办公场所得满分，有驻场承诺得70%",
        "common_in": ["IT服务", "运维"],
        "frequency": 2,
    },
]

# ============================================================
# 技术评分模板项
# ============================================================

TECHNICAL_SCORING_ITEMS = [
    {
        "id": "ts_understanding",
        "name": "需求理解与分析",
        "category": "technical",
        "default_score": 10,
        "description": "对本项目系统功能、现状、架构及部署的理解准确性和深度。",
        "scoring_guide": "理解准确全面(8-10分), 较准确(5-7分), 一般(0-4分)",
        "common_in": ["通用"],
        "frequency": 5,
    },
    {
        "id": "ts_solution",
        "name": "技术/服务方案",
        "category": "technical",
        "default_score": 15,
        "description": "方案的全面性、合理性、可行性、针对性，包括服务需求、人员管理、应急管理等。",
        "scoring_guide": "内容完整详细(12-15分), 较完整(8-11分), 一般(0-7分)",
        "common_in": ["通用"],
        "frequency": 5,
    },
    {
        "id": "ts_implementation",
        "name": "项目实施方案",
        "category": "technical",
        "default_score": 10,
        "description": "实施计划、进度安排、质量保证、组织架构、风险应对措施的合理性。",
        "scoring_guide": "计划详细可行(8-10分), 较合理(5-7分), 一般(0-4分)",
        "common_in": ["IT服务", "工程", "咨询"],
        "frequency": 3,
    },
    {
        "id": "ts_emergency",
        "name": "应急预案",
        "category": "technical",
        "default_score": 5,
        "description": "运维应急预案完整性，技术替代和人员替代等事项。",
        "scoring_guide": "预案完整充分(4-5分), 不完整但可行(2-3分), 缺失(0-1分)",
        "common_in": ["IT服务", "运维"],
        "frequency": 3,
    },
    {
        "id": "ts_security",
        "name": "安全保障方案",
        "category": "technical",
        "default_score": 5,
        "description": "安全保障方案的完整性，安全事件的响应及处置流程。",
        "scoring_guide": "方案完整充分(4-5分), 不完整但可行(2-3分), 缺失(0-1分)",
        "common_in": ["IT服务", "数据治理"],
        "frequency": 3,
    },
    {
        "id": "ts_afterservice",
        "name": "售后服务方案",
        "category": "technical",
        "default_score": 5,
        "description": "售后服务响应时间、服务内容、服务团队、质保期等。",
        "scoring_guide": "服务方案全面(4-5分), 基本覆盖(2-3分), 缺失(0-1分)",
        "common_in": ["通用"],
        "frequency": 3,
    },
    {
        "id": "ts_training",
        "name": "培训计划",
        "category": "technical",
        "default_score": 5,
        "description": "培训方案的完整性、培训内容、培训方式、培训周期等。",
        "scoring_guide": "方案详细全面(4-5分), 基本覆盖(2-3分), 缺失(0-1分)",
        "common_in": ["IT服务", "软件开发"],
        "frequency": 2,
    },
]


# ============================================================
# 价格评分公式模板
# ============================================================

PRICE_FORMULA_TEMPLATES = {
    "arithmetic_mean": {
        "name": "算术平均法",
        "description": "以所有有效投标报价的算术平均值作为评标基准价",
        "formula": "基准价 = Σ(有效报价) / n",
        "deviation_formula": "偏差率 = (报价 - 基准价) / 基准价 × 100%",
        "scoring_rule": "每偏差1%扣1分（上下对称）",
        "frequency": 3,
    },
    "trimmed_mean": {
        "name": "去极值平均法",
        "description": "超过5家时去掉最高最低各1个，取剩余的算术平均值",
        "formula": "基准价 = (Σ有效报价 - max - min) / (n-2)，当n>5时",
        "deviation_formula": "偏差率 = (报价 - 基准价) / 基准价 × 100%",
        "scoring_rule": "高于基准每偏差1%扣1分，低于基准每偏差1%扣0.5分",
        "frequency": 2,
    },
    "lowest_price": {
        "name": "最低价法",
        "description": "以最低有效投标报价为基准",
        "formula": "基准价 = min(有效报价)",
        "deviation_formula": "得分 = 基准价 / 报价 × 满分",
        "scoring_rule": "最低价得满分，其他按比例",
        "frequency": 1,
    },
}


# ============================================================
# 预设方案组合
# ============================================================

SCORING_PRESETS = {
    "IT服务": {
        "description": "IT信息化服务项目推荐评分方案",
        "score_distribution": {"commercial": 30, "technical": 40, "price": 30},
        "commercial_items": ["cs_cert", "cs_performance", "cs_finance"],
        "technical_items": ["ts_understanding", "ts_solution", "ts_implementation", "ts_emergency", "ts_security"],
        "price_formula": "arithmetic_mean",
    },
    "通用服务": {
        "description": "通用服务采购推荐评分方案",
        "score_distribution": {"commercial": 20, "technical": 50, "price": 30},
        "commercial_items": ["cs_cert", "cs_performance"],
        "technical_items": ["ts_understanding", "ts_solution", "ts_afterservice", "ts_training"],
        "price_formula": "arithmetic_mean",
    },
    "工程项目": {
        "description": "工程类项目推荐评分方案",
        "score_distribution": {"commercial": 30, "technical": 40, "price": 30},
        "commercial_items": ["cs_cert", "cs_performance", "cs_finance", "cs_team"],
        "technical_items": ["ts_understanding", "ts_solution", "ts_implementation", "ts_security"],
        "price_formula": "trimmed_mean",
    },
}


class ScoringTemplateLibrary:
    """评分标准模板库。

    提供评分项模板、价格公式模板、预设方案。
    """

    def get_all_items(self) -> Dict[str, List[Dict]]:
        """获取所有评分项模板"""
        return {
            "commercial": deepcopy(COMMERCIAL_SCORING_ITEMS),
            "technical": deepcopy(TECHNICAL_SCORING_ITEMS),
        }

    def get_price_formulas(self) -> Dict[str, Dict]:
        """获取价格评分公式模板"""
        return deepcopy(PRICE_FORMULA_TEMPLATES)

    def get_presets(self) -> Dict[str, Dict]:
        """获取预设评分方案"""
        return deepcopy(SCORING_PRESETS)

    def get_preset(self, industry: str) -> Optional[Dict[str, Any]]:
        """获取指定行业的预设评分方案"""
        preset = SCORING_PRESETS.get(industry)
        if not preset:
            preset = SCORING_PRESETS.get("通用服务")
        if not preset:
            return None

        result = deepcopy(preset)

        # 展开评分项详情
        all_items = {item["id"]: item for items in [COMMERCIAL_SCORING_ITEMS, TECHNICAL_SCORING_ITEMS] for item in items}

        result["commercial_items_detail"] = [
            deepcopy(all_items[item_id]) for item_id in result.get("commercial_items", [])
            if item_id in all_items
        ]
        result["technical_items_detail"] = [
            deepcopy(all_items[item_id]) for item_id in result.get("technical_items", [])
            if item_id in all_items
        ]
        result["price_formula_detail"] = deepcopy(
            PRICE_FORMULA_TEMPLATES.get(result.get("price_formula", "arithmetic_mean"), {})
        )

        return result

    def build_scoring_criteria(
        self,
        commercial_item_ids: List[str],
        technical_item_ids: List[str],
        score_distribution: Dict[str, int],
        price_formula: str = "arithmetic_mean",
        custom_items: List[Dict] = None,
    ) -> Dict[str, Any]:
        """根据选择的评分项构建完整的评分标准。

        Args:
            commercial_item_ids: 选择的商务评分项ID列表
            technical_item_ids: 选择的技术评分项ID列表
            score_distribution: 分值构成 {commercial: 30, technical: 40, price: 30}
            price_formula: 价格评分公式模板ID
            custom_items: 自定义评分项

        Returns:
            完整的评分标准结构
        """
        all_items = {item["id"]: item for items in [COMMERCIAL_SCORING_ITEMS, TECHNICAL_SCORING_ITEMS] for item in items}

        commercial_items = [deepcopy(all_items[i]) for i in commercial_item_ids if i in all_items]
        technical_items = [deepcopy(all_items[i]) for i in technical_item_ids if i in all_items]

        if custom_items:
            for item in custom_items:
                if item.get("category") == "commercial":
                    commercial_items.append(item)
                else:
                    technical_items.append(item)

        return {
            "score_distribution": score_distribution,
            "commercial_items": commercial_items,
            "technical_items": technical_items,
            "price_formula": deepcopy(PRICE_FORMULA_TEMPLATES.get(price_formula, {})),
            "total_score": sum(score_distribution.values()),
        }
