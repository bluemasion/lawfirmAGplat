"""NER Masker — de-identifies PII before sending to LLM."""

from typing import Dict, Tuple
from app.core.ner.detector import NERDetector


class NERMasker:
    """Replace PII entities with placeholder tokens."""

    def __init__(self):
        self.detector = NERDetector()

    def mask(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Mask all PII in text.

        Returns:
            (masked_text, mapping): mapping is {placeholder: original_value}
            e.g. {"[PER-001]": "张三", "[PHONE-001]": "13812345678"}
        """
        entities = self.detector.detect(text)
        mapping = {}
        counters = {}
        masked = text

        for etype, value, start, end in entities:
            if value in [v for v in mapping.values()]:
                # Same entity appeared before, reuse the same placeholder
                placeholder = [k for k, v in mapping.items() if v == value][0]
            else:
                counters[etype] = counters.get(etype, 0) + 1
                placeholder = f"[{etype}-{counters[etype]:03d}]"
                mapping[placeholder] = value

            masked = masked[:start] + placeholder + masked[end:]

        return masked, mapping
