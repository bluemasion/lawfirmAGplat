"""Classification Engine — loads industry-specific rules from JSON config.

Replaces hardcoded classification rules in material_store.py,
material_matcher.py, and rule_verification.py with a configurable,
industry-switchable engine.

Usage:
    engine = ClassificationEngine("legal")  # loads legal_industry.json
    entity_type = engine.classify_entity_type("钱伯斯大中华区排名2026")
    sub_cat, label = engine.resolve_sub_category("ranking")
    routing = engine.get_matcher_routing()
"""

import json
import os
from typing import Any, Dict, List, Optional, Tuple

from app.utils.logger import logger


_CONFIG_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "config", "classification"
)

# Module-level singleton cache
_engines = {}  # type: Dict[str, "ClassificationEngine"]


def get_engine(industry: str = "legal") -> "ClassificationEngine":
    """Get or create a ClassificationEngine for the given industry."""
    if industry not in _engines:
        _engines[industry] = ClassificationEngine(industry)
    return _engines[industry]


class ClassificationEngine:
    """Load and apply industry-specific classification rules."""

    def __init__(self, industry: str = "legal"):
        self.industry = industry
        self.rules = self._load_rules(industry)
        logger.info(
            f"ClassificationEngine loaded: industry={industry}, "
            f"version={self.rules.get('version', '?')}, "
            f"{len(self.rules.get('entity_type_rules', []))} entity rules"
        )

    def _load_rules(self, industry: str) -> Dict[str, Any]:
        """Load rules from JSON config file."""
        config_path = os.path.join(
            _CONFIG_DIR, f"{industry}_industry.json"
        )
        if not os.path.exists(config_path):
            logger.warning(
                f"Classification config not found: {config_path}, "
                f"falling back to legal_industry.json"
            )
            config_path = os.path.join(_CONFIG_DIR, "legal_industry.json")

        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ── Entity Type Classification ──

    def classify_entity_type(self, name: str, item: dict = None) -> str:
        """Classify a qualification record into an entity_type.

        Args:
            name: Material name/title
            item: Full item dict (optional, for issuer-based hints)

        Returns:
            entity_type string like 'award', 'ranking', 'firm_license', etc.
        """
        text = name
        if item:
            issuer = item.get("issuer", "") or ""
            text = f"{name} {issuer}"

        for rule in self.rules.get("entity_type_rules", []):
            keywords = rule.get("keywords", [])
            if any(kw in text for kw in keywords):
                return rule["type"]

        return "other_qual"

    # ── Sub-category Resolution ──

    def resolve_sub_category(
        self, entity_type: str, source_file: str = "", item: dict = None
    ) -> Tuple[str, str]:
        """Resolve sub_category from entity_type.

        Returns:
            (sub_category, label) tuple
        """
        sub_map = self.rules.get("sub_category_map", {})
        if entity_type and entity_type in sub_map:
            pair = sub_map[entity_type]
            return (pair[0], pair[1])

        # Filename-based fallback
        fname = (source_file or "").lower()
        if any(kw in fname for kw in ["保证金", "保函", "投标保证"]):
            return ("bond", "保证金")
        if any(kw in fname for kw in ["诚信", "信用", "无违法"]):
            return ("compliance", "诚信证明")

        return ("", "")

    # ── Cert Type Classification ──

    def classify_cert_type(self, name_or_title: str) -> Tuple[str, str]:
        """Classify certificate type from name/title.

        Returns:
            (cert_type, label) tuple
        """
        for rule in self.rules.get("cert_type_rules", []):
            if any(kw in name_or_title for kw in rule["keywords"]):
                return (rule["type"], rule["label"])
        return ("other", "其他证件")

    # ── Material Attribution ──

    def get_material_attribution(self) -> Dict[str, str]:
        """Get keyword → expected section type mapping for attribution check."""
        return self.rules.get("material_attribution", {})

    # ── Matcher Routing ──

    def get_matcher_routing(self) -> Dict[str, List[str]]:
        """Get keyword lists for MaterialMatcher entity_type routing."""
        return self.rules.get("matcher_routing", {})

    # ── Prohibited Terms ──

    def get_prohibited_terms(self) -> List[Tuple[str, str]]:
        """Get prohibited terms list for compliance checking."""
        terms = self.rules.get("prohibited_terms", [])
        return [(t[0], t[1]) for t in terms if len(t) >= 2]

    # ── Filename-based sub_category fallback ──

    def resolve_sub_from_filename(self, source_file: str) -> Tuple[str, str]:
        """Resolve sub_category from filename hints."""
        fname = (source_file or "").lower()
        if any(kw in fname for kw in ["保证金", "保函", "投标保证"]):
            return ("bond", "保证金")
        if any(kw in fname for kw in ["诚信", "信用", "无违法"]):
            return ("compliance", "诚信证明")
        return ("", "")
