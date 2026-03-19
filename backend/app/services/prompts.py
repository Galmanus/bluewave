"""Centralized prompt versioning for AI calls.

All system/user prompts are defined here with explicit versions.
This enables:
- A/B testing of prompt variants via LangSmith
- Tracking which prompt version generated which output
- Easy rollback if a new prompt degrades quality
"""

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Prompt:
    name: str
    version: str
    text: str


# ── Caption prompts ────────────────────────────────────────────────────────

CAPTION_SYSTEM_V1 = Prompt(
    name="caption_system",
    version="v1",
    text=(
        "You are a creative marketing copywriter for a digital asset "
        "management platform. Generate a single concise, engaging caption "
        "for the media asset described. The caption should be professional, "
        "brand-friendly, and suitable for social media or internal use. "
        "Reply ONLY with the caption text, no quotes or extra formatting."
    ),
)

# ── Hashtag prompts ────────────────────────────────────────────────────────

HASHTAGS_SYSTEM_V1 = Prompt(
    name="hashtags_system",
    version="v1",
    text=(
        "You are a social media strategist. Generate 6-10 relevant hashtags "
        'for the media asset described. Return ONLY a JSON array of strings, '
        'each starting with #. Example: ["#branding", "#design"]. '
        "No other text."
    ),
)

# ── Compliance prompts ─────────────────────────────────────────────────────

COMPLIANCE_USER_V1 = Prompt(
    name="compliance_user",
    version="v1",
    text="(inline in compliance_service.py — structured prompt built dynamically)",
)

# ── Active prompt registry ─────────────────────────────────────────────────

# Map of prompt name → list of (Prompt, weight) for A/B testing.
# Weight 100 = 100% traffic. To A/B test, add a v2 with weight 10 (= 10%).
_REGISTRY: dict[str, list[tuple[Prompt, int]]] = {
    "caption_system": [(CAPTION_SYSTEM_V1, 100)],
    "hashtags_system": [(HASHTAGS_SYSTEM_V1, 100)],
}


def get_prompt(name: str) -> Prompt:
    """Get the active prompt for a given name, respecting A/B weights."""
    variants = _REGISTRY.get(name)
    if not variants:
        raise KeyError(f"Unknown prompt: {name}")

    if len(variants) == 1:
        return variants[0][0]

    # Weighted random selection for A/B testing
    total_weight = sum(w for _, w in variants)
    r = random.randint(1, total_weight)
    cumulative = 0
    for prompt, weight in variants:
        cumulative += weight
        if r <= cumulative:
            return prompt

    return variants[0][0]  # fallback


def get_prompt_metadata(prompt: Prompt) -> dict:
    """Return metadata dict for LangSmith tracing."""
    return {
        "prompt_name": prompt.name,
        "prompt_version": prompt.version,
    }
