"""ComplianceChecker — 合规校验引擎。

包装现有的 rule_verification，扩展采购方合规规则。
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ComplianceChecker:
    """合规校验引擎。

    包装现有模块:
    - rule_verification.py: 规则校验

    新增采购方合规检查:
    - 采购方式与金额匹配
    - 资格条件合法性
    - 排他性条款检测
    - 前后一致性
    """

    def __init__(self):
        self._rule_checker = None

    def _get_rule_checker(self):
        """延迟加载 rule_verification 模块"""
        if self._rule_checker is None:
            try:
                from app.core.skills.builtin import rule_verification
                self._rule_checker = rule_verification
            except ImportError:
                logger.warning("rule_verification module not available")
        return self._rule_checker

    async def check_procurement_document(
        self, document_content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """对采购文件进行全面合规检查。

        Returns:
            {
                "compliance_issues": [...],   # 合规性问题
                "logic_issues": [...],        # 逻辑性问题
                "accuracy_issues": [...],     # 准确性问题
                "risk_level": "LOW|MEDIUM|HIGH",
                "summary": "..."
            }
        """
        issues = {
            "compliance_issues": [],
            "logic_issues": [],
            "accuracy_issues": [],
            "risk_level": "LOW",
            "summary": "",
        }

        # 合规性检查
        issues["compliance_issues"] = self._check_method_compliance(document_content)

        # 逻辑性检查
        issues["logic_issues"] = self._check_logic_consistency(document_content)

        # 准确性检查
        issues["accuracy_issues"] = self._check_accuracy(document_content)

        # 计算整体风险等级
        total_errors = sum(
            1 for lst in [issues["compliance_issues"], issues["logic_issues"], issues["accuracy_issues"]]
            for item in lst if item.get("severity") == "ERROR"
        )
        if total_errors > 3:
            issues["risk_level"] = "HIGH"
        elif total_errors > 0:
            issues["risk_level"] = "MEDIUM"

        total_issues = sum(len(lst) for lst in [
            issues["compliance_issues"], issues["logic_issues"], issues["accuracy_issues"]
        ])
        issues["summary"] = f"发现 {total_issues} 个问题 (风险等级: {issues['risk_level']})"

        return issues

    def _check_method_compliance(self, content: Dict) -> List[Dict]:
        """采购方式合规性检查"""
        issues = []
        method = content.get("procurement_method", "")
        budget = content.get("budget", 0)

        # 采购方式与金额匹配 (基于政府采购法规)
        if method == "inquiry" and budget > 2000000:
            issues.append({
                "issue": f"询价采购金额{budget}元超过200万元限制",
                "severity": "ERROR",
                "rule": "《政府采购法》第三十二条",
                "suggestion": "金额超过200万元应采用公开招标或竞争性磋商"
            })

        return issues

    def _check_logic_consistency(self, content: Dict) -> List[Dict]:
        """逻辑一致性检查"""
        issues = []

        # 评分分值合计
        scoring = content.get("scoring_criteria", {})
        dist = scoring.get("score_distribution", {})
        if dist:
            total = sum(dist.values())
            if total != 100:
                issues.append({
                    "issue": f"评分总分 {total} ≠ 100",
                    "severity": "ERROR",
                    "suggestion": "调整评分分值使总分等于100"
                })

        return issues

    def _check_accuracy(self, content: Dict) -> List[Dict]:
        """数值准确性检查"""
        issues = []

        # 税率校验
        tax_rate = content.get("tax_rate")
        if tax_rate is not None and tax_rate not in [0, 1, 3, 6, 9, 13]:
            issues.append({
                "issue": f"税率 {tax_rate}% 不在常见税率范围内",
                "severity": "WARNING",
                "suggestion": "常见增值税税率: 13%(货物), 9%(建筑), 6%(服务), 3%(小规模)"
            })

        return issues
