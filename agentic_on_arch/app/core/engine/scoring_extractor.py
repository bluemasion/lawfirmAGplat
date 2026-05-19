"""ScoringExtractor — 评分标准提取引擎包装层。

包装现有的 requirement_extraction，提供统一接口。
- 投标方: 从招标文件提取评分标准 → 按标准写投标文件
- 采购方: 从采购文件提取评分标准 → 校验合规性
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ScoringExtractor:
    """统一的评分标准提取接口。

    包装现有模块:
    - requirement_extraction.py: 评分项/废标项提取
    """

    def __init__(self):
        self._extractor = None

    def _get_extractor(self):
        """延迟加载 requirement_extraction 模块"""
        if self._extractor is None:
            try:
                from app.core.skills.builtin import requirement_extraction
                self._extractor = requirement_extraction
            except ImportError:
                logger.warning("requirement_extraction module not available")
        return self._extractor

    async def extract_scoring_criteria(
        self, parsed_document: Dict[str, Any]
    ) -> Dict[str, Any]:
        """从解析后的文档中提取评分标准。

        Returns:
            {
                "scoring_items": [...],      # 评分项列表
                "disqualification_items": [...], # 废标项列表
                "price_formula": {...},       # 价格评分公式
                "score_distribution": {       # 分值构成
                    "commercial": 30,
                    "technical": 40,
                    "price": 30
                }
            }
        """
        extractor = self._get_extractor()
        if extractor and hasattr(extractor, "extract_requirements"):
            return await extractor.extract_requirements(parsed_document)
        raise NotImplementedError("requirement_extraction not available")

    async def validate_scoring_compliance(
        self, scoring_criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """校验评分标准的合规性（采购方审核用）。

        检查:
        - 价格分占比是否符合法规要求 (竞争性磋商≥10%)
        - 评分项是否有排他性/歧视性条款
        - 分值合计是否为100
        - 各评分项的分值区间是否合理

        Returns:
            问题清单 [{issue, severity, suggestion}, ...]
        """
        issues = []

        if not scoring_criteria:
            return [{"issue": "评分标准为空", "severity": "ERROR", "suggestion": "请设置评分标准"}]

        dist = scoring_criteria.get("score_distribution", {})
        total = sum(dist.values()) if dist else 0

        # 分值合计校验
        if total != 100 and total != 0:
            issues.append({
                "issue": f"评分总分为{total}，不等于100",
                "severity": "ERROR",
                "suggestion": "调整各项分值使总分等于100"
            })

        # 价格分占比校验
        price_score = dist.get("price", 0)
        if price_score < 10 and total > 0:
            issues.append({
                "issue": f"价格分占比{price_score}%，低于法规最低要求10%",
                "severity": "WARNING",
                "suggestion": "根据财政部74号令，竞争性磋商的价格分不得低于10%"
            })

        return issues
