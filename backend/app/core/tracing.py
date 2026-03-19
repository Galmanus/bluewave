"""Centralized LangSmith tracing for AI observability.

Provides:
- init_tracing(): called at app startup to configure LangSmith
- trace_llm_call(): context manager that wraps an LLM call with tracing
- is_tracing_enabled(): check if tracing is active

All tracing is OPTIONAL — if LANGSMITH_API_KEY is empty, everything
is a silent no-op with zero overhead.
"""

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any

logger = logging.getLogger("bluewave.tracing")

_tracing_enabled: bool = False
_ls_client: Any = None


def is_tracing_enabled() -> bool:
    return _tracing_enabled


def get_langsmith_client() -> Any:
    """Return the LangSmith client (or None if tracing disabled)."""
    return _ls_client


def init_tracing() -> None:
    """Initialize LangSmith tracing. Call once at app startup."""
    global _tracing_enabled, _ls_client

    from app.core.config import settings

    if not settings.LANGSMITH_API_KEY:
        logger.info("LangSmith tracing disabled (no API key)")
        return

    if not settings.LANGSMITH_TRACING_ENABLED:
        logger.info("LangSmith tracing disabled (LANGSMITH_TRACING_ENABLED=false)")
        return

    try:
        import langsmith

        # Set env vars the SDK expects (legacy names)
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT

        _ls_client = langsmith.Client(
            api_key=settings.LANGSMITH_API_KEY,
        )
        _tracing_enabled = True
        logger.info("LangSmith tracing enabled for project: %s", settings.LANGSMITH_PROJECT)
    except Exception:
        logger.exception("Failed to initialize LangSmith — tracing disabled")
        _tracing_enabled = False


@asynccontextmanager
async def trace_llm_call(
    name: str,
    *,
    run_type: str = "llm",
    inputs: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    parent_run: Any = None,
):
    """Context manager that creates a LangSmith run for an LLM call.

    If tracing is disabled, yields a no-op context with .run_id = None.

    Usage:
        async with trace_llm_call("bluewave.caption", inputs={...}, metadata={...}) as run:
            resp = await client.messages.create(...)
            run.log_output({"caption": caption, "tokens": ...})
    """
    # TEMPORARY: Force NoOp due to LangSmith 0.7.20 async generator bug
    # Tracing works in openclaw-skill (sync SDK). Backend tracing disabled
    # until langsmith SDK is updated to >=0.10.x in the Docker image.
    # The openclaw-skill layer handles all LangSmith tracing.
    yield _NoOpRun()
    return

    if not _tracing_enabled or not _ls_client:
        yield _NoOpRun()
        return

    try:
        from langsmith.run_trees import RunTree

        run_tree = RunTree(
            name=name,
            run_type=run_type,
            inputs=inputs or {},
            extra={"metadata": metadata or {}},
            tags=tags or [],
            parent_run=parent_run,
            project_name=os.environ.get("LANGCHAIN_PROJECT", "bluewave"),
        )
        run_tree.post()

        wrapper = _RunWrapper(run_tree)
        t0 = time.perf_counter()
        try:
            yield wrapper
        except Exception as exc:
            # Business code raised an error — trace it, then re-raise
            try:
                duration_ms = round((time.perf_counter() - t0) * 1000, 1)
                run_tree.end(error=str(exc), outputs={**wrapper._outputs, "duration_ms": duration_ms})
                run_tree.patch()
            except Exception:
                pass
            raise
        else:
            # Success — record trace
            try:
                duration_ms = round((time.perf_counter() - t0) * 1000, 1)
                run_tree.end(outputs={**wrapper._outputs, "duration_ms": duration_ms})
                run_tree.patch()
            except Exception:
                logger.debug("LangSmith trace end/patch failed for %s", name)
    except GeneratorExit:
        # Generator being closed — don't yield again
        return
    except Exception:
        # Tracing init failure must NEVER break business functionality
        logger.debug("LangSmith trace failed for %s — continuing without trace", name)
        yield _NoOpRun()


class _NoOpRun:
    """No-op placeholder when tracing is disabled."""

    run_id: str | None = None
    run_tree: Any = None

    def log_output(self, outputs: dict[str, Any]) -> None:
        pass

    def add_metadata(self, metadata: dict[str, Any]) -> None:
        pass

    def add_tags(self, tags: list[str]) -> None:
        pass


class _RunWrapper:
    """Wrapper around RunTree to collect outputs incrementally."""

    def __init__(self, run_tree: Any) -> None:
        self.run_tree = run_tree
        self.run_id: str = str(run_tree.id)
        self._outputs: dict[str, Any] = {}

    def log_output(self, outputs: dict[str, Any]) -> None:
        self._outputs.update(outputs)

    def add_metadata(self, metadata: dict[str, Any]) -> None:
        try:
            if self.run_tree.extra is None:
                self.run_tree.extra = {}
            existing = self.run_tree.extra.get("metadata", {})
            existing.update(metadata)
            self.run_tree.extra["metadata"] = existing
        except Exception:
            pass

    def add_tags(self, tags: list[str]) -> None:
        try:
            existing = self.run_tree.tags or []
            self.run_tree.tags = list(set(existing + tags))
        except Exception:
            pass


# ── Cost calculation ─────────────────────────────────────────────────────

# Anthropic pricing (millicents per token)
_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-20250514": {"input": 0.3, "output": 1.5},
    # Default for unknown models
    "default": {"input": 0.3, "output": 1.5},
}


def calculate_actual_cost_millicents(
    model: str, input_tokens: int, output_tokens: int
) -> int:
    """Calculate actual cost in millicents from token counts."""
    pricing = _PRICING.get(model, _PRICING["default"])
    return round(input_tokens * pricing["input"] + output_tokens * pricing["output"])


def cost_metadata(
    model: str,
    input_tokens: int,
    output_tokens: int,
    estimated_cost_millicents: int,
) -> dict:
    """Return cost comparison metadata for a trace."""
    actual = calculate_actual_cost_millicents(model, input_tokens, output_tokens)
    delta_pct = round((actual - estimated_cost_millicents) / max(estimated_cost_millicents, 1) * 100, 1)
    return {
        "estimated_cost_millicents": estimated_cost_millicents,
        "actual_cost_millicents": actual,
        "cost_delta_pct": delta_pct,
    }


def send_feedback(
    run_id: str,
    key: str,
    *,
    score: float,
    comment: str = "",
) -> None:
    """Send feedback to LangSmith for a specific run (fire-and-forget)."""
    if not _tracing_enabled or not _ls_client:
        return
    try:
        _ls_client.create_feedback(
            run_id=run_id,
            key=key,
            score=score,
            comment=comment,
        )
    except Exception:
        logger.debug("Failed to send LangSmith feedback for run %s", run_id)
