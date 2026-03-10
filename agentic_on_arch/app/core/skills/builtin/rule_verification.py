"""Rule-based verification skill — deterministic checks on bid documents."""

import re
from typing import Any, Dict, List
from app.core.skills.base import BaseSkill
from app.utils.logger import logger


class VerificationItem:
    """A single verification check result."""

    def __init__(self, check_type: str, target: str, status: str,
                 message: str, severity: str = "INFO"):
        self.check_type = check_type  # structure | order | gap | compliance | format
        self.target = target          # Section or field name
        self.status = status          # PASS | WARNING | ERROR
        self.message = message
        self.severity = severity      # INFO | WARNING | ERROR

    def to_dict(self) -> Dict[str, str]:
        return {
            "check_type": self.check_type,
            "target": self.target,
            "status": self.status,
            "message": self.message,
            "severity": self.severity,
        }


# Words that should not appear in bidding documents
PROHIBITED_TERMS = [
    ("全国第一", '建议改为"处于行业领先地位"'),
    ("绝对安全", '建议改为"最大程度保障安全"'),
    ("零风险", '建议改为"最大程度降低风险"'),
    ("确保", '建议改为"积极推进/尽最大努力"'),
    ("保证不会", '建议改为"采取措施防范"'),
    ("唯一", '建议改为"具有独特优势"'),
    ("100%", '建议改为"尽可能全面覆盖"'),
    ("绝无", '建议改为"极力避免"'),
    ("最好的", '建议改为"优质的/高水平的"'),
    ("最强的", '建议改为"具有突出实力的"'),
]


class RuleVerificationSkill(BaseSkill):
    """Perform deterministic rule-based verification on bid documents."""

    name = "rule_verification"
    description = "对投标文件进行代码规则校验：结构完整性、顺序、缺项扫描、合规用语检查"

    async def execute(self, params: Dict[str, Any]) -> Any:
        """
        Params:
            tender_requirements (Dict): Structured tender requirements (from extraction)
            generated_sections (List[Dict]): Generated bid sections
                [{title, content, order, type, missing_fields, status}]

        Returns:
            Dict with:
            - overall_status (str): PASS | WARNING | ERROR
            - overall_score (int): 0-100
            - checks (List[Dict]): Individual check results
            - summary (Dict): Counts by status
            - missing_items (List[Dict]): All [待补充] items
            - compliance_warnings (List[Dict]): Prohibited term warnings
        """
        requirements = params.get("tender_requirements", {})
        generated = params.get("generated_sections", [])

        checks = []  # type: List[Dict]

        # 1. Structure completeness check
        structure_checks = self._check_structure(requirements, generated)
        checks.extend(structure_checks)

        # 2. Order correctness check
        order_checks = self._check_order(requirements, generated)
        checks.extend(order_checks)

        # 3. Gap analysis (missing fields)
        gap_checks = self._check_gaps(generated)
        checks.extend(gap_checks)

        # 4. Compliance check (prohibited terms)
        compliance_checks = self._check_compliance(generated)
        checks.extend(compliance_checks)

        # 5. Content quality basic checks
        quality_checks = self._check_quality(generated)
        checks.extend(quality_checks)

        # Calculate overall status
        error_count = sum(1 for c in checks if c["status"] == "ERROR")
        warning_count = sum(1 for c in checks if c["status"] == "WARNING")
        pass_count = sum(1 for c in checks if c["status"] == "PASS")
        total = len(checks)

        if error_count > 0:
            overall_status = "ERROR"
        elif warning_count > 0:
            overall_status = "WARNING"
        else:
            overall_status = "PASS"

        # Score: 100 - (errors * 10) - (warnings * 3)
        score = max(0, 100 - (error_count * 10) - (warning_count * 3))

        # Collect missing items
        missing_items = []
        for section in generated:
            for field in section.get("missing_fields", []):
                missing_items.append({
                    "section": section.get("title", ""),
                    "field": field,
                    "priority": "HIGH" if section.get("type") == "qualification" else "MEDIUM",
                })

        # Collect compliance warnings
        compliance_warnings = [c for c in checks if c["check_type"] == "compliance"]

        result = {
            "overall_status": overall_status,
            "overall_score": score,
            "checks": checks,
            "summary": {
                "total": total,
                "pass": pass_count,
                "warning": warning_count,
                "error": error_count,
            },
            "missing_items": missing_items,
            "compliance_warnings": compliance_warnings,
        }

        logger.info(f"Verification complete: {overall_status} (score={score}, "
                     f"errors={error_count}, warnings={warning_count})")
        return result

    def _check_structure(self, requirements: Dict,
                         generated: List[Dict]) -> List[Dict]:
        """Check if all required sections are present."""
        checks = []
        generated_titles = set(s.get("title", "") for s in generated)

        for volume in requirements.get("volumes", []):
            for req_section in volume.get("sections", []):
                title = req_section.get("title", "")
                required = req_section.get("required", True)

                if title in generated_titles:
                    checks.append(VerificationItem(
                        check_type="structure",
                        target=title,
                        status="PASS",
                        message=f"章节 '{title}' 已生成",
                    ).to_dict())
                elif required:
                    checks.append(VerificationItem(
                        check_type="structure",
                        target=title,
                        status="ERROR",
                        message=f"必需章节 '{title}' 缺失",
                        severity="ERROR",
                    ).to_dict())
                else:
                    checks.append(VerificationItem(
                        check_type="structure",
                        target=title,
                        status="WARNING",
                        message=f"可选章节 '{title}' 未生成",
                        severity="WARNING",
                    ).to_dict())

        return checks

    def _check_order(self, requirements: Dict,
                     generated: List[Dict]) -> List[Dict]:
        """Check if sections are in correct order."""
        checks = []
        expected_order = []
        for volume in requirements.get("volumes", []):
            for sec in volume.get("sections", []):
                expected_order.append(sec.get("title", ""))

        actual_order = [s.get("title", "") for s in
                        sorted(generated, key=lambda x: x.get("order", 0))]

        # Check pairwise ordering
        for i in range(len(expected_order) - 1):
            title_a = expected_order[i]
            title_b = expected_order[i + 1]

            if title_a in actual_order and title_b in actual_order:
                idx_a = actual_order.index(title_a)
                idx_b = actual_order.index(title_b)
                if idx_a > idx_b:
                    checks.append(VerificationItem(
                        check_type="order",
                        target=f"{title_a} / {title_b}",
                        status="ERROR",
                        message=f"顺序错误：'{title_a}' 应在 '{title_b}' 之前",
                        severity="ERROR",
                    ).to_dict())

        if not checks:
            checks.append(VerificationItem(
                check_type="order",
                target="全部章节",
                status="PASS",
                message="章节顺序正确",
            ).to_dict())

        return checks

    def _check_gaps(self, generated: List[Dict]) -> List[Dict]:
        """Scan for [待补充] markers."""
        checks = []
        total_gaps = 0

        for section in generated:
            content = section.get("content", "")
            title = section.get("title", "")
            gaps = re.findall(r'\[待补充[：:][^\]]+\]', content)

            if gaps:
                total_gaps += len(gaps)
                checks.append(VerificationItem(
                    check_type="gap",
                    target=title,
                    status="WARNING",
                    message=f"'{title}' 中有 {len(gaps)} 处待补充内容",
                    severity="WARNING",
                ).to_dict())

        if total_gaps == 0:
            checks.append(VerificationItem(
                check_type="gap",
                target="全部章节",
                status="PASS",
                message="无缺失数据",
            ).to_dict())

        return checks

    def _check_compliance(self, generated: List[Dict]) -> List[Dict]:
        """Check for prohibited terms."""
        checks = []

        for section in generated:
            content = section.get("content", "")
            title = section.get("title", "")

            for term, suggestion in PROHIBITED_TERMS:
                if term in content:
                    checks.append(VerificationItem(
                        check_type="compliance",
                        target=title,
                        status="WARNING",
                        message=f"发现禁用词 '{term}'，{suggestion}",
                        severity="WARNING",
                    ).to_dict())

        return checks

    def _check_quality(self, generated: List[Dict]) -> List[Dict]:
        """Basic content quality checks."""
        checks = []

        for section in generated:
            content = section.get("content", "")
            title = section.get("title", "")
            sec_type = section.get("type", "narrative")

            # Check minimum content length for narrative sections
            if sec_type == "narrative" and len(content) < 50:
                checks.append(VerificationItem(
                    check_type="quality",
                    target=title,
                    status="WARNING",
                    message=f"'{title}' 内容过短（{len(content)}字），可能不够详细",
                    severity="WARNING",
                ).to_dict())

            # Check for placeholder-only sections
            if section.get("status") == "placeholder":
                checks.append(VerificationItem(
                    check_type="quality",
                    target=title,
                    status="WARNING",
                    message=f"'{title}' 为占位内容，需要提供实际资料",
                    severity="WARNING",
                ).to_dict())

        return checks
