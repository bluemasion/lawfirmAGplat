"""Template store skill — save, match, list, and manage bidding templates."""

import json
import os
import re
import time
from typing import Any, Dict, List, Optional

from app.core.skills.base import BaseSkill
from app.utils.logger import logger


TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "templates")


class TemplateStoreSkill(BaseSkill):
    """Manage bidding templates — structure + content skeletons."""

    name = "template_store"
    description = "投标模板库管理：保存、匹配、浏览、删除投标模板"

    async def execute(self, params: Dict[str, Any]) -> Any:
        action = params.get("action", "list")
        if action == "save":
            return self.save_template(params)
        elif action == "match":
            return self.match_template(params)
        elif action == "list":
            return self.list_templates()
        elif action == "get":
            return self.get_template(params.get("template_id", ""))
        elif action == "delete":
            return self.delete_template(params.get("template_id", ""))
        else:
            return {"error": f"Unknown action: {action}"}

    # ── Save ──

    def save_template(self, params: Dict[str, Any]) -> Dict:
        """Save a completed bid task as a reusable template.

        Extracts structure + content skeletons, sanitizes sensitive data.
        """
        requirements = params.get("requirements", {})
        generated_sections = params.get("generated_sections", [])
        source_file = params.get("source_file", "unknown")
        name = params.get("name", requirements.get("bid_title", "未命名模板"))
        industry = params.get("industry", self._guess_industry(name))
        bid_type = params.get("type", "通用")

        template_id = f"TPL-{int(time.time())}"

        # Extract skeletons — content with sensitive data replaced
        skeletons = {}
        for sec in generated_sections:
            title = sec.get("title", "")
            content = sec.get("content", "")
            skeletons[title] = {
                "type": sec.get("type", "narrative"),
                "skeleton": self._sanitize_content(content),
                "original_length": len(content),
            }

        template = {
            "template_id": template_id,
            "name": name,
            "industry": industry,
            "type": bid_type,
            "source_file": source_file,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "volumes": requirements.get("volumes", []),
            "qualification_requirements": requirements.get("qualification_requirements", []),
            "format_requirements": requirements.get("format_requirements", {}),
            "section_skeletons": skeletons,
            "tags": self._extract_tags(name, industry),
        }

        # Persist
        os.makedirs(TEMPLATES_DIR, exist_ok=True)
        path = os.path.join(TEMPLATES_DIR, f"{template_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(template, f, ensure_ascii=False, indent=2)

        logger.info(f"Template saved: {template_id} ({name}, {len(skeletons)} skeletons)")
        return {"template_id": template_id, "name": name, "sections": len(skeletons)}

    # ── Match ──

    def match_template(self, params: Dict[str, Any]) -> Dict:
        """Find the best matching template for a new tender.

        Uses keyword + industry + structural similarity.
        """
        requirements = params.get("requirements", {})
        bid_title = requirements.get("bid_title", "")
        volumes = requirements.get("volumes", [])
        new_sections = set()
        for vol in volumes:
            for sec in vol.get("sections", []):
                new_sections.add(sec.get("title", ""))

        templates = self._load_all_templates()
        if not templates:
            return {"matched": False, "reason": "模板库为空"}

        best_match = None
        best_score = 0.0

        for tpl in templates:
            score = self._compute_similarity(bid_title, new_sections, tpl)
            if score > best_score:
                best_score = score
                best_match = tpl

        if best_score >= 0.3 and best_match:
            logger.info(f"Template matched: {best_match['template_id']} "
                         f"({best_match['name']}) score={best_score:.2f}")
            return {
                "matched": True,
                "template_id": best_match["template_id"],
                "template_name": best_match["name"],
                "score": round(best_score, 2),
                "industry": best_match.get("industry", ""),
                "section_count": len(best_match.get("section_skeletons", {})),
                "skeletons": best_match.get("section_skeletons", {}),
            }

        return {"matched": False, "reason": f"最佳匹配分 {best_score:.2f} 低于阈值 0.3"}

    # ── List / Get / Delete ──

    def list_templates(self) -> Dict:
        templates = self._load_all_templates()
        items = []
        for t in templates:
            items.append({
                "template_id": t["template_id"],
                "name": t.get("name", ""),
                "industry": t.get("industry", ""),
                "type": t.get("type", ""),
                "created_at": t.get("created_at", ""),
                "section_count": len(t.get("section_skeletons", {})),
                "tags": t.get("tags", []),
            })
        return {"templates": items, "total": len(items)}

    def get_template(self, template_id: str) -> Dict:
        path = os.path.join(TEMPLATES_DIR, f"{template_id}.json")
        if not os.path.exists(path):
            return {"error": f"模板 {template_id} 不存在"}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def delete_template(self, template_id: str) -> Dict:
        path = os.path.join(TEMPLATES_DIR, f"{template_id}.json")
        if not os.path.exists(path):
            return {"error": f"模板 {template_id} 不存在"}
        os.remove(path)
        logger.info(f"Template deleted: {template_id}")
        return {"deleted": template_id}

    # ── Internal helpers ──

    def _load_all_templates(self) -> List[Dict]:
        if not os.path.exists(TEMPLATES_DIR):
            return []
        templates = []
        for fn in os.listdir(TEMPLATES_DIR):
            if fn.endswith(".json"):
                try:
                    with open(os.path.join(TEMPLATES_DIR, fn), "r", encoding="utf-8") as f:
                        templates.append(json.load(f))
                except Exception:
                    continue
        return templates

    def _compute_similarity(self, title: str, new_sections: set, tpl: Dict) -> float:
        """Compute similarity using embedding model (with keyword fallback)."""
        try:
            from app.core.rag.embedding_service import embedding_service

            # Title semantic similarity (weight: 0.4)
            tpl_name = tpl.get("name", "")
            if title and tpl_name:
                title_sim = embedding_service.similarity(title, tpl_name)
            else:
                title_sim = 0.0

            # Section title similarity (weight: 0.5)
            tpl_sections = list(tpl.get("section_skeletons", {}).keys())
            if new_sections and tpl_sections:
                new_list = list(new_sections)
                sim_matrix = embedding_service.similarity_matrix(new_list, tpl_sections)
                # For each new section, find best match in template
                import numpy as np
                best_matches = np.max(sim_matrix, axis=1)  # best match per new section
                section_sim = float(np.mean(best_matches[best_matches > 0.5]))  # average of good matches
                if np.isnan(section_sim):
                    section_sim = 0.0
            else:
                section_sim = 0.0

            # Tag overlap (weight: 0.1)
            tpl_tags = set(tpl.get("tags", []))
            title_tags = set(self._extract_tags(title, ""))
            tag_score = 0.0
            if tpl_tags and title_tags:
                tag_score = min(len(tpl_tags & title_tags) * 0.1, 0.2)

            score = title_sim * 0.4 + section_sim * 0.5 + tag_score
            return score

        except Exception:
            # Fallback: keyword overlap (original logic)
            return self._compute_similarity_keyword(title, new_sections, tpl)

    def _compute_similarity_keyword(self, title: str, new_sections: set, tpl: Dict) -> float:
        """Fallback: simple keyword + structural overlap scoring."""
        score = 0.0

        # Title keyword overlap
        title_words = set(title)
        tpl_words = set(tpl.get("name", ""))
        if title_words and tpl_words:
            overlap = len(title_words & tpl_words) / max(len(title_words | tpl_words), 1)
            score += overlap * 0.3

        # Section title overlap
        tpl_sections = set(tpl.get("section_skeletons", {}).keys())
        if new_sections and tpl_sections:
            overlap = len(new_sections & tpl_sections) / max(len(new_sections | tpl_sections), 1)
            score += overlap * 0.5

        # Tag overlap
        tpl_tags = set(tpl.get("tags", []))
        title_tags = set(self._extract_tags(title, ""))
        if tpl_tags and title_tags:
            overlap = len(tpl_tags & title_tags)
            score += min(overlap * 0.1, 0.2)

        return score

    def _sanitize_content(self, content: str) -> str:
        """Replace sensitive data with placeholders for template reuse."""
        result = content
        # Replace specific company names, amounts, dates etc.
        result = re.sub(r'湖南天衡律师事务所', '{{company_name}}', result)
        result = re.sub(r'张建明|李文华|王大明|刘芳|陈志远', '{{team_member}}', result)
        result = re.sub(r'\d{4}年\d{1,2}月\d{1,2}日', '{{date}}', result)
        result = re.sub(r'\d+万元', '{{amount}}', result)
        result = re.sub(r'0731-\d{8}', '{{phone}}', result)
        return result

    def _guess_industry(self, title: str) -> str:
        """Guess industry from bid title keywords."""
        keywords = {
            "通信": ["移动", "联通", "电信", "通信", "5G"],
            "政府": ["政府", "公共", "财政", "城管", "住建"],
            "金融": ["银行", "保险", "证券", "基金"],
            "交通": ["高速", "交通", "公路", "铁路"],
            "能源": ["电力", "能源", "石油", "水务"],
            "教育": ["大学", "学院", "教育", "学校"],
        }
        for industry, words in keywords.items():
            if any(w in title for w in words):
                return industry
        return "综合"

    def _extract_tags(self, title: str, industry: str) -> List[str]:
        tags = []
        if industry:
            tags.append(industry)
        tag_words = ["法律服务", "法律顾问", "采购", "招标", "工程", "咨询",
                      "审计", "PPP", "知识产权", "合规"]
        for w in tag_words:
            if w in title:
                tags.append(w)
        return tags
