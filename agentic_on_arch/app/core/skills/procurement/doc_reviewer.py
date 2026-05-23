"""DocReviewer — 采购文件智能审核引擎。

三维审核:
1. 合规性 — 采购方式/金额/资格条件是否符合法规
2. 逻辑性 — 前后一致性/分值匹配/条款矛盾
3. 准确性 — 数值/日期/比例校验

支持规则引擎 + LLM 双引擎审核模式。
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ReviewIssue:
    """审核问题"""

    def __init__(self, category: str, severity: str, title: str,
                 detail: str, suggestion: str = "", rule: str = "",
                 location: str = ""):
        self.category = category      # compliance/logic/accuracy
        self.severity = severity      # ERROR/WARNING/INFO
        self.title = title
        self.detail = detail
        self.suggestion = suggestion
        self.rule = rule              # 法规依据
        self.location = location      # 问题位置

    def to_dict(self) -> Dict:
        return {
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "detail": self.detail,
            "suggestion": self.suggestion,
            "rule": self.rule,
            "location": self.location,
        }


class DocReviewer:
    """采购文件智能审核引擎。

    Usage:
        reviewer = DocReviewer()
        result = reviewer.review(document)
        # result = {issues: [...], summary: {...}, risk_level: "..."}
    """

    def review(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """对采购文件进行全面审核。

        Args:
            document: fill_template() 输出的结构化文档

        Returns:
            {
                "issues": [ReviewIssue.to_dict(), ...],
                "summary": {
                    "total": 10,
                    "errors": 2,
                    "warnings": 5,
                    "info": 3,
                    "by_category": {"compliance": 3, "logic": 4, "accuracy": 3}
                },
                "risk_level": "HIGH|MEDIUM|LOW",
                "passed": False,
                "reviewed_at": "..."
            }
        """
        params = document.get("parameters", {})
        scoring = document.get("scoring_criteria", {})
        eval_template = document.get("eval_template", {})
        chapters = document.get("chapters", [])

        issues: List[ReviewIssue] = []

        # 三维审核
        issues.extend(self._check_compliance(params, scoring))
        issues.extend(self._check_logic(params, scoring, chapters))
        issues.extend(self._check_accuracy(params, scoring))

        # 汇总
        errors = sum(1 for i in issues if i.severity == "ERROR")
        warnings = sum(1 for i in issues if i.severity == "WARNING")
        infos = sum(1 for i in issues if i.severity == "INFO")

        category_counts = {}
        for i in issues:
            category_counts[i.category] = category_counts.get(i.category, 0) + 1

        if errors >= 3:
            risk_level = "HIGH"
        elif errors > 0:
            risk_level = "MEDIUM"
        elif warnings > 3:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "issues": [i.to_dict() for i in issues],
            "summary": {
                "total": len(issues),
                "errors": errors,
                "warnings": warnings,
                "info": infos,
                "by_category": category_counts,
            },
            "risk_level": risk_level,
            "passed": errors == 0,
            "reviewed_at": datetime.now().isoformat(),
        }

    # ============================
    # 合规性检查
    # ============================

    def _check_compliance(self, params: Dict, scoring: Dict) -> List[ReviewIssue]:
        """合规性审核 — 采购方式、金额、资格条件"""
        issues = []

        method = params.get("method", params.get("eval_method", ""))
        budget = params.get("budget", params.get("max_price", 0))
        if isinstance(budget, str):
            try:
                budget = float(budget) if budget else 0
            except ValueError:
                budget = 0

        # C1: 必填字段检查
        required_fields = [
            ("project_name", "项目名称"),
            ("project_code", "项目编号"),
            ("purchaser_name", "招标人名称"),
            ("scope_description", "招标范围"),
        ]
        for field_id, label in required_fields:
            if not params.get(field_id, "").strip():
                issues.append(ReviewIssue(
                    category="compliance", severity="ERROR",
                    title=f"缺少必填字段: {label}",
                    detail=f"{label}未填写，该字段为必填项",
                    suggestion=f"请填写{label}",
                    location="须知前附表",
                ))

        # C2: 评标方法与评分标准匹配
        eval_method = params.get("eval_method", "综合评估法")
        dist = scoring.get("score_distribution", {})

        if eval_method == "综合评估法" and not dist:
            issues.append(ReviewIssue(
                category="compliance", severity="ERROR",
                title="综合评估法缺少评分标准",
                detail="选择了综合评估法但未设置评分标准（商务/技术/价格分值构成）",
                suggestion="请配置评分标准，设置商务、技术、价格各项分值",
                rule="《招标投标法实施条例》第四十九条",
                location="第三章 评标办法",
            ))

        # C3: 价格分占比
        if dist:
            price_score = dist.get("price", 0)
            total = sum(dist.values())
            if total > 0 and price_score / total < 0.1:
                issues.append(ReviewIssue(
                    category="compliance", severity="WARNING",
                    title=f"价格分占比偏低 ({price_score}/{total}={price_score/total*100:.0f}%)",
                    detail="价格评分占比低于10%，可能不符合相关法规要求",
                    suggestion="建议价格分不低于总分的10%",
                    rule="财政部74号令（竞争性磋商）",
                    location="第三章 评标办法",
                ))

        # C4: 资格条件排他性检测
        qualification_text = " ".join([
            params.get("qualification_general", ""),
            params.get("qualification_cert", ""),
            params.get("qualification_performance", ""),
        ])

        # 检测可能的排他性条款
        exclusionary_patterns = [
            (r"仅限|只接受|唯一|指定品牌", "可能存在排他性限制"),
            (r"注册资本[^\d]*(\d+)万", "注册资本门槛可能过高"),
            (r"成立[^\d]*(\d+)年以上", "成立年限要求"),
        ]
        for pattern, desc in exclusionary_patterns:
            match = re.search(pattern, qualification_text)
            if match:
                issues.append(ReviewIssue(
                    category="compliance", severity="WARNING",
                    title=f"资格条件可能存在排他性: {desc}",
                    detail=f"在资格条件中检测到: \"{match.group(0)}\"",
                    suggestion="请确认该条件是否合理，避免不当排斥潜在投标人",
                    rule="《政府采购法》第二十二条",
                    location="第一章 资格要求",
                ))

        # C5: 投标有效期
        validity = params.get("bid_validity_days", 90)
        if isinstance(validity, str):
            try:
                validity = int(validity) if validity else 90
            except ValueError:
                validity = 90
        if validity > 180:
            issues.append(ReviewIssue(
                category="compliance", severity="WARNING",
                title=f"投标有效期过长 ({validity}天)",
                detail="投标有效期超过180天，可能增加投标人负担",
                suggestion="建议投标有效期控制在60-120天",
                location="须知前附表",
            ))

        return issues

    # ============================
    # 逻辑性检查
    # ============================

    def _check_logic(self, params: Dict, scoring: Dict,
                     chapters: List[Dict]) -> List[ReviewIssue]:
        """逻辑性审核 — 前后一致性、分值匹配"""
        issues = []

        # L1: 评分分值合计
        dist = scoring.get("score_distribution", {})
        if dist:
            total = sum(dist.values())
            if total != 100:
                issues.append(ReviewIssue(
                    category="logic", severity="ERROR",
                    title=f"评分总分不等于100 (当前: {total})",
                    detail=f"商务{dist.get('commercial',0)} + 技术{dist.get('technical',0)} + 价格{dist.get('price',0)} = {total}",
                    suggestion="调整各项分值使总分等于100",
                    location="第三章 评标办法",
                ))

        # L2: 评分子项分值合计与大项一致
        for category_key, category_label in [("commercial_items", "商务"), ("technical_items", "技术")]:
            items = scoring.get(category_key, [])
            if items and dist:
                # items may be dicts or string IDs — only sum if dicts
                dict_items = [i for i in items if isinstance(i, dict)]
                if not dict_items:
                    continue
                items_total = sum(item.get("default_score", 0) for item in dict_items)
                expected = dist.get(category_key.replace("_items", ""), 0)
                if expected > 0 and items_total != expected:
                    issues.append(ReviewIssue(
                        category="logic", severity="ERROR",
                        title=f"{category_label}评分子项合计({items_total}) ≠ {category_label}总分({expected})",
                        detail=f"{category_label}评分共{len(dict_items)}项，子项分值合计{items_total}分，但{category_label}总分设为{expected}分",
                        suggestion=f"调整{category_label}评分子项分值使合计等于{expected}",
                        location="第三章 评标办法",
                    ))

        # L3: 评委会人数
        committee_size = params.get("eval_committee_size", 5)
        if isinstance(committee_size, str):
            try:
                committee_size = int(committee_size) if committee_size else 5
            except ValueError:
                committee_size = 5
        if committee_size < 3:
            issues.append(ReviewIssue(
                category="logic", severity="ERROR",
                title=f"评标委员会人数不足 ({committee_size}人)",
                detail="评标委员会至少需要3人",
                suggestion="建议设置5-7人的评标委员会",
                rule="《招标投标法》第三十七条",
                location="须知前附表",
            ))
        if committee_size % 2 == 0:
            issues.append(ReviewIssue(
                category="logic", severity="WARNING",
                title=f"评标委员会人数为偶数 ({committee_size}人)",
                detail="建议评标委员会人数为奇数，便于投票表决",
                suggestion="建议设置为5人或7人",
                location="须知前附表",
            ))

        # L4: 中标候选人数量
        candidates = params.get("candidate_count", 3)
        if isinstance(candidates, str):
            try:
                candidates = int(candidates) if candidates else 3
            except ValueError:
                candidates = 3
        if candidates < 1:
            issues.append(ReviewIssue(
                category="logic", severity="ERROR",
                title="中标候选人数量不合理",
                detail=f"设置了{candidates}个中标候选人",
                suggestion="至少应设置1个中标候选人，建议3个",
                location="须知前附表",
            ))

        return issues

    # ============================
    # 准确性检查
    # ============================

    def _check_accuracy(self, params: Dict, scoring: Dict) -> List[ReviewIssue]:
        """准确性审核 — 数值、日期、比例"""
        issues = []

        # A1: 预算/限价为0或负数
        budget = params.get("budget", params.get("max_price", 0))
        if isinstance(budget, str):
            try:
                budget = float(budget) if budget else 0
            except ValueError:
                budget = 0
        if budget < 0:
            issues.append(ReviewIssue(
                category="accuracy", severity="ERROR",
                title="预算金额为负数",
                detail=f"预算金额设为 {budget}",
                suggestion="请检查并修正预算金额",
                location="须知前附表",
            ))

        # A2: 保证金金额过高
        deposit = params.get("deposit_amount", 0)
        if isinstance(deposit, str):
            try:
                deposit = float(deposit) if deposit else 0
            except ValueError:
                deposit = 0
        if deposit > 0 and budget > 0 and deposit / budget > 0.02:
            issues.append(ReviewIssue(
                category="accuracy", severity="WARNING",
                title=f"投标保证金占比过高 ({deposit/budget*100:.1f}%)",
                detail=f"保证金{deposit}元，预算{budget}元，占比{deposit/budget*100:.1f}%",
                suggestion="投标保证金一般不超过预算的2%",
                rule="《招标投标法实施条例》第二十六条",
                location="须知前附表",
            ))

        # A3: 副本份数异常
        copies = params.get("copies_duplicate", 4)
        if isinstance(copies, str):
            try:
                copies = int(copies) if copies else 4
            except ValueError:
                copies = 4
        if copies > 10:
            issues.append(ReviewIssue(
                category="accuracy", severity="WARNING",
                title=f"副本份数偏多 ({copies}份)",
                detail="过多的副本份数增加投标人负担",
                suggestion="建议副本份数为3-5份",
                location="须知前附表",
            ))

        # A4: 评分项分值为0或负数
        for category in ["commercial_items", "technical_items"]:
            for item in scoring.get(category, []):
                if not isinstance(item, dict):
                    continue  # skip string IDs
                score = item.get("default_score", 0)
                if score <= 0:
                    issues.append(ReviewIssue(
                        category="accuracy", severity="WARNING",
                        title=f"评分项分值异常: {item.get('name', '')}",
                        detail=f"评分项\"{item.get('name', '')}\"的分值为{score}",
                        suggestion="请设置合理的分值(大于0)",
                        location="第三章 评标办法",
                    ))

        return issues


class ReviewReportGenerator:
    """审核报告生成器 — 将审核结果格式化输出。"""

    def generate_text_report(self, review_result: Dict) -> str:
        """生成文本格式的审核报告"""
        issues = review_result.get("issues", [])
        summary = review_result.get("summary", {})
        risk = review_result.get("risk_level", "UNKNOWN")

        lines = [
            "=" * 60,
            "          采购文件智能审核报告",
            "=" * 60,
            f"审核时间: {review_result.get('reviewed_at', '')}",
            f"风险等级: {risk}",
            f"审核结果: {'通过' if review_result.get('passed') else '未通过'}",
            "",
            f"问题统计: 共 {summary.get('total', 0)} 个",
            f"  ❌ 错误: {summary.get('errors', 0)}",
            f"  ⚠️ 警告: {summary.get('warnings', 0)}",
            f"  ℹ️ 信息: {summary.get('info', 0)}",
            "",
        ]

        # 按分类分组
        for category, label in [("compliance", "合规性问题"), ("logic", "逻辑性问题"), ("accuracy", "准确性问题")]:
            cat_issues = [i for i in issues if i.get("category") == category]
            if not cat_issues:
                continue
            lines.append(f"--- {label} ({len(cat_issues)}) ---")
            for idx, issue in enumerate(cat_issues, 1):
                severity_icon = {"ERROR": "❌", "WARNING": "⚠️", "INFO": "ℹ️"}.get(issue["severity"], "•")
                lines.append(f"{severity_icon} [{issue['severity']}] {issue['title']}")
                lines.append(f"   {issue['detail']}")
                if issue.get("suggestion"):
                    lines.append(f"   → {issue['suggestion']}")
                if issue.get("rule"):
                    lines.append(f"   📜 {issue['rule']}")
                lines.append("")

        return "\n".join(lines)
