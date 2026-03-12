"""Register all builtin skills."""

from app.core.skills.registry import skill_registry
from app.core.skills.builtin.tender_parsing import TenderParsingSkill
from app.core.skills.builtin.requirement_extraction import RequirementExtractionSkill
from app.core.skills.builtin.content_generation import ContentGenerationSkill
from app.core.skills.builtin.template_filling import TemplateFillingSkill
from app.core.skills.builtin.docx_assembly import DocxAssemblySkill
from app.core.skills.builtin.rule_verification import RuleVerificationSkill
from app.core.skills.builtin.template_store import TemplateStoreSkill
from app.core.skills.builtin.data_retrieval import DataRetrievalSkill


def register_builtin_skills():
    """Register all builtin skills with the global registry."""
    skills = [
        TenderParsingSkill(),
        RequirementExtractionSkill(),
        ContentGenerationSkill(),
        TemplateFillingSkill(),
        DocxAssemblySkill(),
        RuleVerificationSkill(),
        TemplateStoreSkill(),
        DataRetrievalSkill(),
    ]
    for skill in skills:
        skill_registry.register(skill)


# Auto-register on import
register_builtin_skills()

