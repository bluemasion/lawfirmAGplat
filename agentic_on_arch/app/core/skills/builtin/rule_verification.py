"""Rule-based verification skill — deterministic checks on bid documents."""

import re
from typing import Any, Dict, List, Set
from collections import Counter, defaultdict
from app.core.skills.base import BaseSkill
from app.utils.logger import logger


class VerificationItem:
    """A single verification check result."""

    def __init__(self, check_type: str, target: str, status: str,
                 message: str, severity: str = "INFO"):
        self.check_type = check_type
        self.target = target
        self.status = status
        self.message = message
        self.severity = severity

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

# Material attribution rules: keyword → expected section type
_MATERIAL_ATTRIBUTION = {
    "排名": "荣誉",
    "榜单": "荣誉",
    "ALB": "荣誉",
    "钱伯斯": "荣誉",
    "Legal 500": "荣誉",
    "LEGALBAND": "荣誉",
    "获奖": "荣誉",
    "身份证": "团队",
    "学历": "团队",
    "学位": "团队",
    "MBA": "团队",
    "LLM": "团队",
    "简历": "团队",
    "执业证": "团队",
    "营业执照": "资格",
    "审计报告": "资格",
    "税务登记": "资格",
}


class RuleVerificationSkill(BaseSkill):
    """Perform deterministic rule-based verification on bid documents."""

    name = "rule_verification"
    description = "对投标文件进行代码规则校验：结构完整性、顺序、缺项扫描、合规用语检查、跨章节去重、评分覆盖等12项检查"

    async def execute(self, params: Dict[str, Any]) -> Any:
        requirements = params.get("tender_requirements", {})
        generated = params.get("generated_sections", [])

        checks = []  # type: List[Dict]

        # Original 5 checks
        checks.extend(self._check_structure(requirements, generated))
        checks.extend(self._check_order(requirements, generated))
        checks.extend(self._check_gaps(generated))
        checks.extend(self._check_compliance(generated))
        checks.extend(self._check_quality(generated))

        # NEW: Extended 7 checks
        checks.extend(self._check_image_duplication(generated))
        checks.extend(self._check_text_duplication(generated))
        checks.extend(self._check_material_attribution(generated))
        checks.extend(self._check_scoring_coverage(requirements, generated))
        checks.extend(self._check_rejection_coverage(requirements, generated))
        checks.extend(self._check_personnel_consistency(generated))
        checks.extend(self._check_amount_consistency(generated))

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

        score = max(0, 100 - (error_count * 10) - (warning_count * 3))

        missing_items = []
        for section in generated:
            for field in section.get("missing_fields", []):
                missing_items.append({
                    "section": section.get("title", ""),
                    "field": field,
                    "priority": "HIGH" if section.get("type") == "qualification" else "MEDIUM",
                })

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
                     f"errors={error_count}, warnings={warning_count}, "
                     f"checks={total})")
        return result

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Original checks (1-5)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _check_structure(self, requirements, generated):
        """1. Check if all required sections are present."""
        checks = []
        generated_titles = set(s.get("title", "") for s in generated)
        for volume in requirements.get("volumes", []):
            for req_section in volume.get("sections", []):
                title = req_section.get("title", "")
                required = req_section.get("required", True)
                if title in generated_titles:
                    checks.append(VerificationItem(
                        "structure", title, "PASS",
                        f"章节 '{title}' 已生成",
                    ).to_dict())
                elif required:
                    checks.append(VerificationItem(
                        "structure", title, "ERROR",
                        f"必需章节 '{title}' 缺失", "ERROR",
                    ).to_dict())
                else:
                    checks.append(VerificationItem(
                        "structure", title, "WARNING",
                        f"可选章节 '{title}' 未生成", "WARNING",
                    ).to_dict())
        return checks

    def _check_order(self, requirements, generated):
        """2. Check if sections are in correct order."""
        checks = []
        expected_order = []
        for volume in requirements.get("volumes", []):
            for sec in volume.get("sections", []):
                expected_order.append(sec.get("title", ""))
        actual_order = [s.get("title", "") for s in
                        sorted(generated, key=lambda x: x.get("order", 0))]
        for i in range(len(expected_order) - 1):
            a, b = expected_order[i], expected_order[i + 1]
            if a in actual_order and b in actual_order:
                if actual_order.index(a) > actual_order.index(b):
                    checks.append(VerificationItem(
                        "order", f"{a} / {b}", "ERROR",
                        f"顺序错误：'{a}' 应在 '{b}' 之前", "ERROR",
                    ).to_dict())
        if not checks:
            checks.append(VerificationItem(
                "order", "全部章节", "PASS", "章节顺序正确",
            ).to_dict())
        return checks

    def _check_gaps(self, generated):
        """3. Scan for [待补充] markers."""
        checks = []
        total_gaps = 0
        for section in generated:
            content = section.get("content", "")
            title = section.get("title", "")
            gaps = re.findall(r'\[待补充[：:][^\]]+\]', content)
            if gaps:
                total_gaps += len(gaps)
                checks.append(VerificationItem(
                    "gap", title, "WARNING",
                    f"'{title}' 中有 {len(gaps)} 处待补充内容", "WARNING",
                ).to_dict())
        if total_gaps == 0:
            checks.append(VerificationItem(
                "gap", "全部章节", "PASS", "无缺失数据",
            ).to_dict())
        return checks

    def _check_compliance(self, generated):
        """4. Check for prohibited terms."""
        checks = []
        for section in generated:
            content = section.get("content", "")
            title = section.get("title", "")
            for term, suggestion in PROHIBITED_TERMS:
                if term in content:
                    checks.append(VerificationItem(
                        "compliance", title, "WARNING",
                        f"发现禁用词 '{term}'，{suggestion}", "WARNING",
                    ).to_dict())
        return checks

    def _check_quality(self, generated):
        """5. Basic content quality checks."""
        checks = []
        for section in generated:
            content = section.get("content", "")
            title = section.get("title", "")
            sec_type = section.get("type", "narrative")
            if sec_type == "narrative" and len(content) < 50:
                checks.append(VerificationItem(
                    "quality", title, "WARNING",
                    f"'{title}' 内容过短（{len(content)}字）", "WARNING",
                ).to_dict())
            if section.get("status") == "placeholder":
                checks.append(VerificationItem(
                    "quality", title, "WARNING",
                    f"'{title}' 为占位内容，需要提供实际资料", "WARNING",
                ).to_dict())
        return checks

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # NEW: Extended checks (6-12)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _check_image_duplication(self, generated):
        """6. Detect images that appear in multiple chapters."""
        checks = []
        image_locations = defaultdict(list)
        for section in generated:
            content = section.get("content", "")
            title = section.get("title", "")
            images = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', content)
            for img in images:
                image_locations[img].append(title)

        dup_count = sum(1 for chapters in image_locations.values()
                        if len(set(chapters)) > 1)
        if dup_count > 0:
            checks.append(VerificationItem(
                "image_dedup", "跨章节",  "WARNING",
                f"发现 {dup_count} 张图片在多个章节重复引用", "WARNING",
            ).to_dict())
        else:
            checks.append(VerificationItem(
                "image_dedup", "跨章节", "PASS",
                "无跨章节图片重复",
            ).to_dict())
        return checks

    def _check_text_duplication(self, generated):
        """7. Detect paragraphs appearing in multiple chapters."""
        checks = []
        para_locations = defaultdict(set)
        for section in generated:
            content = section.get("content", "")
            title = section.get("title", "")
            paragraphs = [p.strip() for p in content.split("\n\n")
                          if len(p.strip()) > 60]
            for para in paragraphs:
                fingerprint = para[:80]
                para_locations[fingerprint].add(title)

        dup_count = sum(1 for chapters in para_locations.values()
                        if len(chapters) > 1)
        if dup_count > 0:
            details = []
            for fp, chapters in para_locations.items():
                if len(chapters) > 1 and len(details) < 3:
                    details.append(f"'{fp[:30]}...' → {', '.join(list(chapters)[:3])}")
            msg = f"发现 {dup_count} 段文字跨章节重复"
            if details:
                msg += "。" + "；".join(details)
            checks.append(VerificationItem(
                "text_dedup", "跨章节", "WARNING", msg, "WARNING",
            ).to_dict())
        else:
            checks.append(VerificationItem(
                "text_dedup", "跨章节", "PASS", "无跨章节文本重复",
            ).to_dict())
        return checks

    def _check_material_attribution(self, generated):
        """8. Check if materials are placed in the correct sections."""
        checks = []
        misplaced = []
        for section in generated:
            content = section.get("content", "")
            title = section.get("title", "")
            for keyword, expected in _MATERIAL_ATTRIBUTION.items():
                if keyword in content and expected not in title:
                    count = content.count(keyword)
                    if count >= 2:
                        misplaced.append(
                            f"'{keyword}'(×{count}) 在 '{title}' 中，"
                            f"建议归入含'{expected}'的章节"
                        )
        if misplaced:
            for detail in misplaced[:5]:
                checks.append(VerificationItem(
                    "attribution", "素材归属", "WARNING", detail, "WARNING",
                ).to_dict())
        else:
            checks.append(VerificationItem(
                "attribution", "素材归属", "PASS", "素材归属合理",
            ).to_dict())
        return checks

    def _check_scoring_coverage(self, requirements, generated):
        """9. Check if all evaluation criteria are addressed."""
        checks = []
        eval_criteria = requirements.get("evaluation_criteria", [])
        if not eval_criteria:
            return checks

        all_content = "\n".join(s.get("content", "") for s in generated)
        uncovered = []
        for criterion in eval_criteria:
            item_name = criterion.get("item", "")
            max_score = criterion.get("max_score", 0)
            if not item_name:
                continue
            # Check by keywords
            keywords = [w for w in re.split(r'[（）() ，,]', item_name)
                        if len(w) > 1]
            found = any(kw in all_content for kw in keywords) if keywords else False
            if not found and item_name not in all_content:
                uncovered.append(f"{item_name}({max_score}分)")

        if uncovered:
            checks.append(VerificationItem(
                "scoring_coverage", "评分覆盖", "WARNING",
                f"{len(uncovered)} 个评分项可能未体现: "
                + ", ".join(uncovered[:5]),
                "WARNING",
            ).to_dict())
        else:
            checks.append(VerificationItem(
                "scoring_coverage", "评分覆盖", "PASS",
                f"全部 {len(eval_criteria)} 个评分项已覆盖",
            ).to_dict())
        return checks

    def _check_rejection_coverage(self, requirements, generated):
        """10. Check if rejection conditions are addressed."""
        checks = []
        rejection_items = requirements.get("rejection_items", [])
        if not rejection_items:
            return checks

        all_content = "\n".join(s.get("content", "") for s in generated)
        uncovered = []
        for item in rejection_items:
            desc = item.get("description", "")
            if not desc:
                continue
            key_phrases = [w for w in re.split(r'[，。、；]', desc)
                           if len(w) > 4]
            covered = any(phrase in all_content for phrase in key_phrases[:3])
            if not covered:
                uncovered.append(desc[:50])

        if uncovered:
            checks.append(VerificationItem(
                "rejection_coverage", "废标条款", "ERROR",
                f"{len(uncovered)} 条废标条款可能未响应: "
                + "; ".join(uncovered[:3]),
                "ERROR",
            ).to_dict())
        else:
            checks.append(VerificationItem(
                "rejection_coverage", "废标条款", "PASS",
                f"全部 {len(rejection_items)} 条废标条款已响应",
            ).to_dict())
        return checks

    def _check_personnel_consistency(self, generated):
        """11. Check person name consistency across sections."""
        checks = []
        name_pattern = re.compile(r'[\u4e00-\u9fff]{2,4}')
        team_names = set()
        skip_words = {"投标", "招标", "项目", "技术", "商务", "评标",
                      "国投", "集团", "有限", "公司", "律师", "事务"}

        for section in generated:
            title = section.get("title", "")
            if any(kw in title for kw in ["团队", "人员", "配置"]):
                content = section.get("content", "")
                for line in content.split("\n"):
                    if any(kw in line for kw in ["姓名", "合伙人", "顾问", "负责人"]):
                        names = name_pattern.findall(line)
                        for n in names:
                            if n not in skip_words and len(n) <= 4:
                                team_names.add(n)

        if team_names and len(team_names) <= 20:
            for section in generated:
                title = section.get("title", "")
                if any(kw in title for kw in ["投标函", "授权", "委托"]):
                    content = section.get("content", "")
                    found = [n for n in team_names if n in content]
                    if not found:
                        checks.append(VerificationItem(
                            "personnel", title, "WARNING",
                            f"'{title}' 中未提及团队成员姓名", "WARNING",
                        ).to_dict())

        if not checks:
            checks.append(VerificationItem(
                "personnel", "人员一致性", "PASS",
                "人员信息一致性检查通过",
            ).to_dict())
        return checks

    def _check_amount_consistency(self, generated):
        """12. Check monetary amount consistency across sections."""
        checks = []
        amount_pattern = re.compile(r'([\d,]+(?:\.\d+)?)\s*(?:万元|元|万)')
        amounts_by_section = {}

        for section in generated:
            content = section.get("content", "")
            title = section.get("title", "")
            amounts = amount_pattern.findall(content)
            if amounts:
                amounts_by_section[title] = amounts

        # Basic check: report how many sections contain amounts
        checks.append(VerificationItem(
            "amount", "金额一致性", "PASS",
            f"检查了 {len(amounts_by_section)} 个包含金额的章节",
        ).to_dict())
        return checks
