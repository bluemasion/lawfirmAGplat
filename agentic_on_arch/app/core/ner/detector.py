"""NER entity detector — Phase 1: regex rules, Phase 2: Legal-BERT.

Detects personally identifiable information (PII) in Chinese legal text:
- 人名 (PER), 身份证号 (ID), 银行卡号 (BANK), 手机号 (PHONE),
  地址 (ADDR), 公司名 (ORG), 案号 (CASE_NO)
"""

import re
from typing import List, Tuple

# Entity type → regex pattern
PATTERNS = {
    "PHONE": re.compile(r"1[3-9]\d{9}"),
    "ID_CARD": re.compile(r"[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]"),
    "BANK_CARD": re.compile(r"[1-9]\d{15,18}"),
    "EMAIL": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "CASE_NO": re.compile(r"[\(（]\d{4}[\)）][\u4e00-\u9fa5]+\d+号"),
}

# Common Chinese surnames for name detection (simplified)
SURNAMES = set("赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳酆鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄")


class NERDetector:
    """Detect PII entities in text using regex patterns."""

    def detect(self, text: str) -> List[Tuple[str, str, int, int]]:
        """
        Returns list of (entity_type, entity_value, start_pos, end_pos).
        Sorted by start position descending (for safe replacement).
        """
        entities = []

        # Regex-based detection
        for etype, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                entities.append((etype, match.group(), match.start(), match.end()))

        # Simple name detection (2-4 char after common surname)
        name_pattern = re.compile(r"(?<=[：:，,。\s])([" + "".join(SURNAMES) + r"][\u4e00-\u9fa5]{1,3})(?=[，,。、\s])")
        for match in name_pattern.finditer(text):
            entities.append(("PER", match.group(), match.start(), match.end()))

        # Sort by start position descending for safe replacement
        entities.sort(key=lambda x: x[2], reverse=True)
        return entities
