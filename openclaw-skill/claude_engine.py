"""
claude_engine.py — Backward-compatible wrapper around inference_engine.

All logic now lives in inference_engine.py. This file re-exports gemini_call
so existing imports (`from claude_engine import gemini_call`) keep working.
"""

from inference_engine import gemini_call  # noqa: F401

__all__ = ["gemini_call"]
