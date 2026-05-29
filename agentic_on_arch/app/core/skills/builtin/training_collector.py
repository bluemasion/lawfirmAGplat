"""Training Data Collector — automatically saves LLM generation pairs for SFT.

Collects (prompt, system, output) tuples from narrative section generation
for future fine-tuning of local models (e.g. Qwen3-35B).

Only collects narrative-type sections (form/table/qualification are template-based).
Data is saved to data/training/ as JSONL files.

Usage:
    from app.core.skills.builtin.training_collector import save_training_sample
    save_training_sample(
        task_id="bid_xxx",
        section_title="服务方案",
        prompt_skill="service_plan",
        prompt="...",
        system="...",
        output="...",
        llm_provider="qwen",
    )
"""

import json
import os
import time
from typing import Optional

from app.utils.logger import logger

# Training data directory
_TRAINING_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..",
    "data", "training"
)
_TRAINING_DIR = os.path.normpath(_TRAINING_DIR)


def save_training_sample(
    task_id: str,
    section_title: str,
    prompt_skill: str,
    prompt: str,
    system: str,
    output: str,
    llm_provider: str = "qwen",
    model: str = "qwen-max",
    section_type: str = "narrative",
    scoring_weight: int = 0,
    metadata: Optional[dict] = None,
):
    """Save a training sample to the JSONL training file.

    Args:
        task_id: Bid task ID (e.g. "bid_1779953297")
        section_title: Chapter title (e.g. "服务方案")
        prompt_skill: PromptSkill name (e.g. "service_plan")
        prompt: The full user prompt sent to LLM
        system: The system prompt
        output: The LLM-generated content
        llm_provider: LLM provider name
        model: Model identifier
        section_type: Section type (narrative/form/table)
        scoring_weight: Scoring weight for this section
        metadata: Optional extra metadata
    """
    # Only collect if output is substantial (>200 chars)
    if not output or len(output) < 200:
        return

    # Skip if output contains error markers
    if "[LLM流式生成错误" in output:
        return

    try:
        os.makedirs(_TRAINING_DIR, exist_ok=True)

        sample = {
            "task_id": task_id,
            "section_title": section_title,
            "prompt_skill": prompt_skill,
            "section_type": section_type,
            "scoring_weight": scoring_weight,
            "prompt": prompt,
            "system": system,
            "output": output,
            "output_chars": len(output),
            "llm_provider": llm_provider,
            "model": model,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        if metadata:
            sample["metadata"] = metadata

        # Append to JSONL file (one file per day for easy management)
        date_str = time.strftime("%Y%m%d")
        filepath = os.path.join(_TRAINING_DIR, f"sft_samples_{date_str}.jsonl")

        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

        logger.info(
            f"  [training] Saved sample: {section_title} "
            f"({prompt_skill}, {len(output)}字) → {os.path.basename(filepath)}"
        )
    except Exception as e:
        # Non-fatal — never block generation pipeline
        logger.warning(f"  [training] Failed to save sample: {e}")


def get_training_stats():
    """Get statistics about collected training data.

    Returns:
        {"total_samples": int, "files": [...], "by_skill": {...}}
    """
    stats = {"total_samples": 0, "files": [], "by_skill": {}}

    if not os.path.exists(_TRAINING_DIR):
        return stats

    for fname in sorted(os.listdir(_TRAINING_DIR)):
        if not fname.endswith(".jsonl"):
            continue
        filepath = os.path.join(_TRAINING_DIR, fname)
        file_count = 0
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    file_count += 1
                    try:
                        sample = json.loads(line)
                        skill = sample.get("prompt_skill", "unknown")
                        stats["by_skill"][skill] = stats["by_skill"].get(skill, 0) + 1
                    except json.JSONDecodeError:
                        pass
        stats["total_samples"] += file_count
        stats["files"].append({"name": fname, "count": file_count})

    return stats
