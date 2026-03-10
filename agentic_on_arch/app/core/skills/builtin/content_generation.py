"""Content generation skill — generate bid section content using LLM."""

from typing import Any, Dict, List, Optional
from app.core.skills.base import BaseSkill
from app.core.llm import get_llm
from app.utils.logger import logger


SECTION_GENERATION_SYSTEM = """你是一位资深的律所投标文件撰写专家。你的任务是根据招标要求和参考资料，
为投标文件的指定章节撰写专业、精准的内容。

写作要求：
1. 语言正式、专业，符合法律文书规范
2. 如果提供了参考资料，必须基于参考资料撰写，不要编造
3. 涉及具体数据（公司名、人名、金额、日期等）时，如果没有提供真实数据，
   用 [待补充：xxx] 格式标注，不要编造假数据
4. 内容要完整覆盖招标要求的每一项
5. 使用标准投标文件的格式和措辞"""


NARRATIVE_PROMPT = """请为投标文件撰写以下章节的内容：

【章节标题】
{section_title}

【招标要求】
{content_hints}

【参考资料】
{reference_data}

【律所基本信息】
{company_info}

请直接输出该章节的正文内容，使用 Markdown 格式：
- 二级标题用 ## 
- 三级标题用 ###
- 表格用 Markdown 表格
- 需要填写的具体数据如果没有，用 [待补充：字段名] 标注"""


FORM_PROMPT = """请为投标文件生成以下格式文件的内容：

【文件标题】
{section_title}

【招标要求】
{content_hints}

【律所基本信息】
{company_info}

请生成该文件的完整内容，包含所有必要的格式化文字。
对于需要手动填写的信息（如签字、盖章、日期等），用 [待补充：xxx] 标注。
直接输出文件内容，使用 Markdown 格式。"""


class ContentGenerationSkill(BaseSkill):
    """Generate content for individual bid sections using LLM."""

    name = "content_generation"
    description = "使用LLM为投标文件的各个章节生成专业内容"

    async def execute(self, params: Dict[str, Any]) -> Any:
        """
        Params:
            section (Dict): Section info with title, type, content_hints, data_fields
            company_info (str, optional): Pre-set company data
            reference_data (str, optional): RAG retrieved reference content
            llm_provider (str, optional): LLM provider name

        Returns:
            Dict with:
            - title (str): Section title
            - content (str): Generated content (Markdown)
            - missing_fields (List[str]): Fields marked [待补充]
            - status (str): "generated" | "template" | "placeholder"
        """
        section = params.get("section", {})
        company_info = params.get("company_info", "暂无律所信息")
        reference_data = params.get("reference_data", "暂无参考资料")
        llm_provider = params.get("llm_provider", "qwen")

        title = section.get("title", "未知章节")
        sec_type = section.get("type", "narrative")
        content_hints = section.get("content_hints", "")
        data_fields = section.get("data_fields", [])

        logger.info(f"Generating content for: [{sec_type}] {title}")

        if sec_type == "qualification":
            # Qualification sections: just list what's needed
            content = self._generate_qualification_placeholder(title, content_hints, data_fields)
            return {
                "title": title,
                "content": content,
                "missing_fields": data_fields if data_fields else [title],
                "status": "placeholder",
            }

        if sec_type == "table":
            # Table sections: generate with template + LLM
            content = await self._generate_table_section(
                title, content_hints, data_fields, company_info, llm_provider
            )
        elif sec_type == "form":
            # Form sections: formal documents (投标函, 声明函)
            content = await self._generate_form_section(
                title, content_hints, company_info, llm_provider
            )
        else:
            # Narrative sections: main content generation
            content = await self._generate_narrative_section(
                title, content_hints, reference_data, company_info, llm_provider
            )

        # Scan for [待补充] markers
        import re
        missing = re.findall(r'\[待补充[：:]([^\]]+)\]', content)

        return {
            "title": title,
            "content": content,
            "missing_fields": missing,
            "status": "generated",
        }

    async def _generate_narrative_section(self, title: str, hints: str,
                                           reference: str, company_info: str,
                                           llm_provider: str) -> str:
        llm = get_llm(llm_provider)
        prompt = NARRATIVE_PROMPT.format(
            section_title=title,
            content_hints=hints or "按照招标要求撰写",
            reference_data=reference,
            company_info=company_info,
        )
        return await llm.generate(prompt, system=SECTION_GENERATION_SYSTEM)

    async def _generate_form_section(self, title: str, hints: str,
                                      company_info: str, llm_provider: str) -> str:
        llm = get_llm(llm_provider)
        prompt = FORM_PROMPT.format(
            section_title=title,
            content_hints=hints or "按照标准格式生成",
            company_info=company_info,
        )
        return await llm.generate(prompt, system=SECTION_GENERATION_SYSTEM)

    async def _generate_table_section(self, title: str, hints: str,
                                       data_fields: List[str], company_info: str,
                                       llm_provider: str) -> str:
        llm = get_llm(llm_provider)
        fields_str = "、".join(data_fields) if data_fields else "请根据标题推断需要的字段"
        prompt = f"""请为投标文件生成以下表格章节：

【章节标题】{title}
【招标要求】{hints or '标准表格'}
【需要包含的字段】{fields_str}
【律所基本信息】{company_info}

要求：
1. 使用 Markdown 表格格式
2. 表头清晰
3. 没有具体数据的单元格填写 [待补充：字段名]
4. 如果有多行数据，至少提供表头和一行示例"""

        return await llm.generate(prompt, system=SECTION_GENERATION_SYSTEM)

    def _generate_qualification_placeholder(self, title: str, hints: str,
                                             data_fields: List[str]) -> str:
        """Generate placeholder for qualification/certificate sections."""
        content_parts = [
            f"## {title}\n",
            f"> ⚠️ 本章节需要提供资质文件，请确认是否具备以下资质：\n",
        ]

        if hints:
            content_parts.append(f"**招标要求**：{hints}\n")

        if data_fields:
            content_parts.append("**需要提供的材料**：\n")
            for field in data_fields:
                content_parts.append(f"- [ ] {field} [待补充：{field}]")
        else:
            content_parts.append(f"- [ ] {title} [待补充：{title}]")

        content_parts.append("\n\n*请将相关证书扫描件附在投标文件相应位置。*")
        return "\n".join(content_parts)
