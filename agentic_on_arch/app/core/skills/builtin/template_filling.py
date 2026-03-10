"""Template filling skill — fill structured data into templates."""

from typing import Any, Dict, List, Optional
from app.core.skills.base import BaseSkill
from app.utils.logger import logger


# Default company data template — can be overridden at runtime
DEFAULT_COMPANY_DATA = {
    "company_name": "[待补充：律所名称]",
    "license_no": "[待补充：执业许可证号]",
    "legal_rep": "[待补充：法定代表人]",
    "address": "[待补充：律所地址]",
    "phone": "[待补充：联系电话]",
    "fax": "[待补充：传真号码]",
    "email": "[待补充：电子邮箱]",
    "bank_name": "[待补充：开户银行]",
    "bank_account": "[待补充：银行账号]",
    "registered_capital": "[待补充：注册资本]",
    "established_year": "[待补充：成立年份]",
    "lawyer_count": "[待补充：律师人数]",
    "partner_count": "[待补充：合伙人人数]",
}


class TemplateFillingSkill(BaseSkill):
    """Fill templates with structured data from company profile."""

    name = "template_filling"
    description = "将律所预设数据填充到表格/表单模板中，缺失数据标记[待补充]"

    async def execute(self, params: Dict[str, Any]) -> Any:
        """
        Params:
            template_fields (List[str]): Fields that need to be filled
            company_data (Dict, optional): Override company data
            section_title (str, optional): Context for filling

        Returns:
            Dict with:
            - filled_data (Dict[str, str]): Field → Value mapping
            - missing_fields (List[str]): Fields that couldn't be filled
            - fill_rate (float): Percentage of fields filled
        """
        template_fields = params.get("template_fields", [])
        custom_data = params.get("company_data", {})
        section_title = params.get("section_title", "")

        # Merge custom data with defaults
        data = dict(DEFAULT_COMPANY_DATA)
        data.update(custom_data)

        filled = {}  # type: Dict[str, str]
        missing = []  # type: List[str]

        for field in template_fields:
            # Try exact match
            value = data.get(field)
            if value and not value.startswith("[待补充"):
                filled[field] = value
            else:
                # Try fuzzy match
                matched = self._fuzzy_match(field, data)
                if matched:
                    filled[field] = matched
                else:
                    filled[field] = f"[待补充：{field}]"
                    missing.append(field)

        fill_rate = (len(template_fields) - len(missing)) / max(len(template_fields), 1)

        logger.info(f"Template filling for '{section_title}': "
                     f"{len(template_fields) - len(missing)}/{len(template_fields)} filled "
                     f"({fill_rate:.0%})")

        return {
            "filled_data": filled,
            "missing_fields": missing,
            "fill_rate": fill_rate,
        }

    def _fuzzy_match(self, field: str, data: Dict[str, str]) -> Optional[str]:
        """Try to match a field name to available data using simple rules."""
        field_lower = field.lower()

        # Common field name mappings
        mappings = {
            "律所名称": "company_name",
            "投标人名称": "company_name",
            "公司名称": "company_name",
            "单位名称": "company_name",
            "法定代表人": "legal_rep",
            "法人代表": "legal_rep",
            "地址": "address",
            "联系地址": "address",
            "通讯地址": "address",
            "电话": "phone",
            "联系电话": "phone",
            "传真": "fax",
            "邮箱": "email",
            "电子邮箱": "email",
            "开户银行": "bank_name",
            "银行账号": "bank_account",
            "注册资本": "registered_capital",
            "成立时间": "established_year",
            "成立年份": "established_year",
            "执业证号": "license_no",
            "许可证号": "license_no",
        }

        for keyword, data_key in mappings.items():
            if keyword in field_lower or field_lower in keyword:
                value = data.get(data_key, "")
                if value and not value.startswith("[待补充"):
                    return value

        return None

    @staticmethod
    def get_company_info_summary(company_data: Optional[Dict] = None) -> str:
        """Get a text summary of company info for LLM prompts."""
        data = dict(DEFAULT_COMPANY_DATA)
        if company_data:
            data.update(company_data)

        lines = []
        for key, value in data.items():
            if not value.startswith("[待补充"):
                # Convert key to Chinese label
                labels = {
                    "company_name": "律所名称",
                    "license_no": "执业许可证号",
                    "legal_rep": "法定代表人",
                    "address": "地址",
                    "phone": "电话",
                    "established_year": "成立年份",
                    "lawyer_count": "律师人数",
                    "partner_count": "合伙人人数",
                }
                label = labels.get(key, key)
                lines.append(f"- {label}: {value}")

        return "\n".join(lines) if lines else "暂无律所信息"
