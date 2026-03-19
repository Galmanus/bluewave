"""Prompt Template Loader — externalizes AI prompts for testability and iteration.

Load prompts from .txt files in this directory. Templates use Python str.format()
syntax for variable interpolation.

Usage:
    from app.prompts import load_prompt

    system_prompt = load_prompt("caption_system")
    user_prompt = load_prompt("compliance_check", guidelines_text="...", asset_info="...")
"""

import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger("bluewave.prompts")

PROMPTS_DIR = Path(__file__).parent


@lru_cache(maxsize=32)
def _read_template(name: str) -> str:
    """Read and cache a prompt template file."""
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        logger.error("Prompt template not found: %s", path)
        raise FileNotFoundError(f"Prompt template not found: {name}")
    return path.read_text(encoding="utf-8")


def load_prompt(name: str, **kwargs) -> str:
    """Load a prompt template and optionally interpolate variables.

    Args:
        name: Template filename without extension (e.g., "caption_system")
        **kwargs: Variables to interpolate into the template

    Returns:
        The rendered prompt string
    """
    template = _read_template(name)
    if kwargs:
        return template.format(**kwargs)
    return template


def reload_prompts():
    """Clear the template cache (useful for development hot-reload)."""
    _read_template.cache_clear()
