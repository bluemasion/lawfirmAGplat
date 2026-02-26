"""NER Demasker — restores original PII after LLM response."""

from typing import Dict


class NERDemasker:
    """Restore placeholder tokens back to original PII values."""

    def demask(self, text: str, mapping: Dict[str, str]) -> str:
        """
        Replace all placeholders in text with their original values.

        Args:
            text: LLM response text containing placeholders like [PER-001]
            mapping: {placeholder: original_value} from NERMasker
        """
        result = text
        for placeholder, original in mapping.items():
            result = result.replace(placeholder, original)
        return result
