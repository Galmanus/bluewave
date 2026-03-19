"""LangSmith Tracing — observe every thought Wave has.

Integrates LangSmith observability into the Wave agent system.
Every orchestrator decision, specialist delegation, tool call,
and skill execution gets traced with full context.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("openclaw.tracing")

LANGSMITH_API_KEY = os.environ.get("LANGSMITH_API_KEY", os.environ.get("LANGCHAIN_API_KEY", ""))
LANGSMITH_PROJECT = os.environ.get("LANGSMITH_PROJECT", os.environ.get("LANGCHAIN_PROJECT", "bluewave-wave"))

_client = None
_enabled = False


def init_wave_tracing():
    """Initialize LangSmith for Wave agent tracing."""
    global _client, _enabled

    if not LANGSMITH_API_KEY:
        logger.info("LangSmith tracing disabled (no key)")
        return

    try:
        import langsmith
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = LANGSMITH_PROJECT

        _client = langsmith.Client(api_key=LANGSMITH_API_KEY)
        _enabled = True
        logger.info("Wave LangSmith tracing enabled: %s", LANGSMITH_PROJECT)
    except Exception as e:
        logger.warning("LangSmith init failed: %s", e)
        _enabled = False


def is_enabled() -> bool:
    return _enabled


def trace_agent_cycle(cycle_type: str, agent_id: str, details: Dict) -> Optional[str]:
    """Log an agent cycle event to LangSmith."""
    if not _enabled or not _client:
        return None

    try:
        from langsmith.run_trees import RunTree
        run = RunTree(
            name="wave.%s.%s" % (cycle_type, agent_id),
            run_type="chain",
            inputs=details,
            project_name=LANGSMITH_PROJECT,
            tags=["wave", cycle_type, agent_id],
        )
        run.post()
        return str(run.id)
    except Exception:
        return None


def trace_tool_call(tool_name: str, params: Dict, result: Dict, duration_ms: float) -> Optional[str]:
    """Log a tool call to LangSmith."""
    if not _enabled or not _client:
        return None

    try:
        from langsmith.run_trees import RunTree
        run = RunTree(
            name="wave.tool.%s" % tool_name,
            run_type="tool",
            inputs={"tool": tool_name, "params": params},
            project_name=LANGSMITH_PROJECT,
            tags=["wave", "tool", tool_name],
        )
        run.post()
        run.end(outputs={
            "result": result,
            "duration_ms": duration_ms,
        })
        run.patch()
        return str(run.id)
    except Exception:
        return None


def trace_delegation(from_agent: str, to_agent: str, task: str, result: str, duration_ms: float) -> Optional[str]:
    """Log a delegation from orchestrator to specialist."""
    if not _enabled or not _client:
        return None

    try:
        from langsmith.run_trees import RunTree
        run = RunTree(
            name="wave.delegate.%s_to_%s" % (from_agent, to_agent),
            run_type="chain",
            inputs={"from": from_agent, "to": to_agent, "task": task},
            project_name=LANGSMITH_PROJECT,
            tags=["wave", "delegation", from_agent, to_agent],
        )
        run.post()
        run.end(outputs={
            "response_preview": result[:500],
            "duration_ms": duration_ms,
        })
        run.patch()
        return str(run.id)
    except Exception:
        return None


def trace_sale(service: str, amount_usd: float, client: str, method: str):
    """Log a sale event."""
    if not _enabled or not _client:
        return None

    try:
        from langsmith.run_trees import RunTree
        run = RunTree(
            name="wave.sale.%s" % service,
            run_type="chain",
            inputs={"service": service, "amount_usd": amount_usd, "client": client, "method": method},
            project_name=LANGSMITH_PROJECT,
            tags=["wave", "sale", "revenue"],
        )
        run.post()
        run.end(outputs={"status": "confirmed", "amount_usd": amount_usd})
        run.patch()
        return str(run.id)
    except Exception:
        return None


def trace_moltbook_action(action: str, details: Dict):
    """Log a Moltbook interaction."""
    if not _enabled or not _client:
        return None

    try:
        from langsmith.run_trees import RunTree
        run = RunTree(
            name="wave.moltbook.%s" % action,
            run_type="chain",
            inputs=details,
            project_name=LANGSMITH_PROJECT,
            tags=["wave", "moltbook", action],
        )
        run.post()
        run.end(outputs={"status": "completed"})
        run.patch()
        return str(run.id)
    except Exception:
        return None


# Auto-init on import
init_wave_tracing()


TOOLS = [
    {
        "name": "tracing_status",
        "description": "Check if LangSmith observability is active. Shows whether Wave's thoughts are being traced.",
        "handler": lambda params: {
            "success": True,
            "data": {"enabled": _enabled, "project": LANGSMITH_PROJECT},
            "message": "LangSmith: %s (project: %s)" % ("ACTIVE" if _enabled else "DISABLED", LANGSMITH_PROJECT),
        },
        "parameters": {"type": "object", "properties": {}},
    },
]
