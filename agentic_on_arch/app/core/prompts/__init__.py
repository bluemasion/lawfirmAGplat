# ── Prompt Registry ──
# Central registry for all prompt templates.
# Prompts are loaded from individual module files for clean separation.
#
# Usage:
#   from app.core.prompts import get_prompt, get_system_prompt
#   prompt = get_prompt("firm_intro")
#   system = get_system_prompt("content_generation")

from app.core.prompts.content_generation_prompts import (
    SECTION_GENERATION_SYSTEM,
    PROMPT_FIRM_INTRO,
    PROMPT_SERVICE_PLAN,
    PROMPT_COMPLIANCE,
    PROMPT_TEAM,
    PROMPT_PROJECT_PERF,
    NARRATIVE_PROMPT,
    PROMPT_ROUTING,
)

from app.core.prompts.requirement_prompts import (
    ANALYSIS_SYSTEM,
    ANALYSIS_PROMPT,
    STRUCTURE_SYSTEM,
    STRUCTURE_PROMPT,
    BATCH_CLASSIFY_SYSTEM,
    BATCH_CLASSIFY_PROMPT,
)

# ── Convenience accessors ──

_SYSTEM_PROMPTS = {
    "content_generation": SECTION_GENERATION_SYSTEM,
    "analysis": ANALYSIS_SYSTEM,
    "structure": STRUCTURE_SYSTEM,
    "batch_classify": BATCH_CLASSIFY_SYSTEM,
}

_PROMPTS = {
    "firm_intro": PROMPT_FIRM_INTRO,
    "service_plan": PROMPT_SERVICE_PLAN,
    "compliance": PROMPT_COMPLIANCE,
    "team": PROMPT_TEAM,
    "project_perf": PROMPT_PROJECT_PERF,
    "narrative": NARRATIVE_PROMPT,
    "analysis": ANALYSIS_PROMPT,
    "structure": STRUCTURE_PROMPT,
    "batch_classify": BATCH_CLASSIFY_PROMPT,
}


def get_prompt(name: str) -> str:
    """Get a prompt template by name."""
    if name not in _PROMPTS:
        raise KeyError(f"Unknown prompt: '{name}'. Available: {list(_PROMPTS.keys())}")
    return _PROMPTS[name]


def get_system_prompt(name: str) -> str:
    """Get a system prompt by name."""
    if name not in _SYSTEM_PROMPTS:
        raise KeyError(f"Unknown system prompt: '{name}'. Available: {list(_SYSTEM_PROMPTS.keys())}")
    return _SYSTEM_PROMPTS[name]


def list_prompts() -> dict:
    """List all registered prompts with their line counts."""
    return {
        "system_prompts": {k: len(v.splitlines()) for k, v in _SYSTEM_PROMPTS.items()},
        "prompts": {k: len(v.splitlines()) for k, v in _PROMPTS.items()},
    }
