"""Bid Document LLM Reviewer — AI-powered deep review of generated bid documents.

This is the 4th layer of quality control after:
  1. MaterialMatcher context-aware dedup
  2. DocxAssembly image dedup
  3. RuleVerification deterministic checks

Uses Qwen to perform semantic-level review that code-based rules cannot catch:
  - Cross-chapter semantic duplication (same idea, different words)
  - Logical contradictions (conflicting facts across chapters)
  - Requirement coverage gaps (tender asks for X, bid doesn't address it)
  - Expression quality (tone, coherence, professionalism)
"""

import asyncio
import json
import time
from typing import Any, Dict, List

from app.core.skills.base import BaseSkill
from app.utils.logger import logger


class BidDocReviewerSkill(BaseSkill):
    """LLM-based deep review of generated bid documents."""

    name = "bid_doc_reviewer"
    description = "对生成的投标文件进行 AI 深度语义审查"

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run LLM review on generated sections.

        Args:
            params: {
                "generated_sections": [{title, content}, ...],
                "tender_requirements": {...},
                "llm_provider": "qwen" (default),
            }

        Returns:
            {
                "issues": [{"category", "severity", "title", "detail", "chapters"}, ...],
                "summary": {"total", "semantic_dedup", "contradiction", "coverage", "quality"},
                "overall_assessment": "...",
                "elapsed": 12.3,
            }
        """
        start = time.time()
        sections = params.get("generated_sections", [])
        requirements = params.get("tender_requirements", {})
        llm_provider = params.get("llm_provider", "qwen")

        if not sections:
            return {"issues": [], "summary": {}, "overall_assessment": "无章节可审查",
                    "elapsed": 0}

        # Build chapter overview for LLM (first 300 chars per section)
        overview = self._build_overview(sections)

        # Build requirement summary
        req_summary = self._build_requirement_summary(requirements)

        # Call LLM for review
        issues = await self._llm_review(overview, req_summary, llm_provider)

        # Categorize
        categories = {
            "semantic_dedup": 0, "contradiction": 0,
            "coverage": 0, "quality": 0
        }
        for issue in issues:
            cat = issue.get("category", "quality")
            if cat in categories:
                categories[cat] += 1

        elapsed = round(time.time() - start, 1)
        logger.info(
            f"[bid_doc_reviewer] Review complete: {len(issues)} issues "
            f"found in {elapsed}s"
        )

        return {
            "issues": issues,
            "summary": {"total": len(issues), **categories},
            "overall_assessment": self._overall_assessment(issues),
            "elapsed": elapsed,
        }

    def _build_overview(self, sections: List[Dict]) -> str:
        """Build chapter overview for LLM — first 300 chars per section."""
        lines = []
        for i, sec in enumerate(sections):
            title = sec.get("title", f"第{i+1}章")
            content = sec.get("content", "")
            # Strip markdown image refs for cleaner overview
            import re
            clean = re.sub(r'!\[.*?\]\(.*?\)', '[图片]', content)
            excerpt = clean[:300].replace('\n', ' ')
            lines.append(f"【第{i+1}章 {title}】\n{excerpt}...")
        return "\n\n".join(lines)

    def _build_requirement_summary(self, requirements: Dict) -> str:
        """Build requirement summary for coverage check."""
        parts = []

        # Evaluation criteria
        eval_criteria = requirements.get("evaluation_criteria", [])
        if eval_criteria:
            criteria_text = []
            for ec in eval_criteria[:10]:
                if isinstance(ec, dict):
                    criteria_text.append(
                        f"- {ec.get('item', '')}: {ec.get('max_score', '')}分"
                    )
            if criteria_text:
                parts.append("评分标准:\n" + "\n".join(criteria_text))

        # Rejection items
        rejection = requirements.get("rejection_items", [])
        if rejection:
            rej_text = []
            for r in rejection[:10]:
                if isinstance(r, dict):
                    rej_text.append(f"- {r.get('condition', '')}")
            if rej_text:
                parts.append("废标条件:\n" + "\n".join(rej_text))

        return "\n\n".join(parts) if parts else "（无明确评分/废标要求）"

    async def _llm_review(
        self, overview: str, req_summary: str, provider: str
    ) -> List[Dict]:
        """Call LLM to perform semantic review."""

        prompt = f"""你是一位资深投标文件审查专家。请审查以下投标文件的各章节摘要，找出以下问题：

## 审查维度

1. **语义重复** (semantic_dedup)：不同章节用不同措辞表达了相同的内容或观点
2. **逻辑矛盾** (contradiction)：不同章节中的事实、数据或说法相互矛盾
3. **需求覆盖** (coverage)：招标要求中的关键点在投标文件中未被充分响应
4. **表述质量** (quality)：用语不规范、逻辑不连贯、表述不专业的地方

## 投标文件各章节摘要

{overview}

## 招标要求摘要

{req_summary}

## 输出要求

请以 JSON 数组格式输出发现的问题，每个问题格式如下：
```json
[
  {{
    "category": "semantic_dedup|contradiction|coverage|quality",
    "severity": "ERROR|WARNING|INFO",
    "title": "问题标题（10字以内）",
    "detail": "具体描述（说明哪些章节有什么问题，50字以内）",
    "chapters": ["涉及的章节名1", "章节名2"]
  }}
]
```

注意：
- 只输出确实存在的问题，不要编造
- severity: ERROR=严重影响得分，WARNING=可能影响，INFO=建议优化
- 如果没有发现问题，输出空数组 []
- 只输出JSON数组，不要其他文字"""

        try:
            from app.core.llm import get_llm
            llm = get_llm(provider)
            response = await llm.generate(
                prompt=prompt,
                system="你是一位资深投标文件审查专家，请严格按照JSON格式输出。",
                temperature=0.1,
                max_tokens=2000,
            )

            # Parse JSON from response (response is a string)
            text = response if isinstance(response, str) else str(response)
            return self._parse_issues(text)

        except Exception as e:
            logger.error(f"[bid_doc_reviewer] LLM review failed: {e}")
            return [{
                "category": "quality",
                "severity": "INFO",
                "title": "AI审查未完成",
                "detail": f"LLM调用失败: {str(e)[:50]}",
                "chapters": [],
            }]

    def _parse_issues(self, text: str) -> List[Dict]:
        """Parse LLM output into structured issues."""
        import re

        # Try to extract JSON array from response
        # Handle markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', text, re.DOTALL)
        if json_match:
            text = json_match.group(1)
        else:
            # Try bare JSON array
            arr_match = re.search(r'\[.*\]', text, re.DOTALL)
            if arr_match:
                text = arr_match.group(0)

        try:
            issues = json.loads(text)
            if not isinstance(issues, list):
                return []

            # Validate each issue
            valid = []
            for issue in issues:
                if not isinstance(issue, dict):
                    continue
                valid.append({
                    "category": issue.get("category", "quality"),
                    "severity": issue.get("severity", "INFO"),
                    "title": issue.get("title", ""),
                    "detail": issue.get("detail", ""),
                    "chapters": issue.get("chapters", []),
                })
            return valid

        except json.JSONDecodeError:
            logger.warning(f"[bid_doc_reviewer] Failed to parse LLM output")
            return []

    def _overall_assessment(self, issues: List[Dict]) -> str:
        """Generate overall assessment text."""
        if not issues:
            return "AI审查通过，未发现明显问题"

        errors = sum(1 for i in issues if i.get("severity") == "ERROR")
        warnings = sum(1 for i in issues if i.get("severity") == "WARNING")

        if errors > 0:
            return f"发现{errors}个严重问题需要修正，建议重新审阅相关章节"
        elif warnings > 0:
            return f"发现{warnings}个需要关注的问题，建议检查后再提交"
        else:
            return f"发现{len(issues)}个可优化项，整体质量良好"
