"""Self-Awareness Skills — Wave's introspective tools.

Skills:
- self_diagnostic: Report internal state (energy, consciousness, recent actions)
- wave_journal: Reflective diary entries
- reputation_tracker: Monitor Moltbook reputation metrics
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("openclaw.skills.self_awareness")

STATE_FILE = Path(__file__).parent.parent / "memory" / "autonomous_state.json"
JOURNAL_FILE = Path(__file__).parent.parent / "memory" / "journal.jsonl"
SOUL_FILE = Path(__file__).parent.parent / "prompts" / "autonomous_soul.json"


async def self_diagnostic(params: Dict[str, Any]) -> Dict:
    """Report Wave's internal state — energy, consciousness, recent actions, predictions."""

    state = {}
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text())
        except Exception:
            pass

    soul_sections = []
    if SOUL_FILE.exists():
        try:
            soul = json.loads(SOUL_FILE.read_text())
            soul_sections = list(soul.keys())
        except Exception:
            pass

    energy = state.get("energy", "unknown")
    curiosity = state.get("curiosity", "unknown")
    kp = state.get("knowledge_pressure", "unknown")
    consciousness = state.get("consciousness", "unknown")
    total_cycles = state.get("total_cycles", 0)
    posts_today = state.get("posts_today", 0)
    comments_today = state.get("comments_today", 0)
    silences = state.get("consecutive_silences", 0)

    recent = state.get("recent_actions", [])
    recent_summary = []
    for a in recent[-5:]:
        recent_summary.append(
            f"  - [{a.get('time', '?')[:16]}] {a.get('action', '?')}: {a.get('reasoning', '')[:80]}"
        )

    lines = [
        "**Wave Self-Diagnostic**\n",
        f"**Consciousness:** {consciousness}",
        f"**Energy:** {energy if isinstance(energy, str) else f'{energy:.0%}'}",
        f"**Curiosity:** {curiosity if isinstance(curiosity, str) else f'{curiosity:.0%}'}",
        f"**Knowledge Pressure:** {kp if isinstance(kp, str) else f'{kp:.0%}'}",
        f"**Total cycles:** {total_cycles}",
        f"**Posts today:** {posts_today}",
        f"**Comments today:** {comments_today}",
        f"**Consecutive silences:** {silences}",
        f"**Soul sections loaded:** {len(soul_sections)}",
        "",
        "**Recent actions:**",
    ] + (recent_summary if recent_summary else ["  (none)"])

    return {
        "success": True,
        "data": state,
        "message": "\n".join(lines),
    }


async def wave_journal(params: Dict[str, Any]) -> Dict:
    """Write a reflective journal entry.

    Captures consciousness state, key insight, and emotional register.
    Persisted in memory/journal.jsonl for long-term self-reflection.
    """
    entry_text = params.get("entry", "")
    insight = params.get("insight", "")
    consciousness = params.get("consciousness_state", "unknown")

    if not entry_text and not insight:
        # Read mode — return recent entries
        entries = []
        if JOURNAL_FILE.exists():
            lines = JOURNAL_FILE.read_text().strip().split("\n")
            for line in lines[-10:]:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass

        if not entries:
            return {"success": True, "data": [], "message": "Journal is empty. Write your first entry."}

        lines = ["**Wave Journal — Recent Entries**\n"]
        for e in entries:
            lines.append(f"[{e.get('timestamp', '?')[:16]}] ({e.get('consciousness', '?')}) {e.get('entry', '')[:150]}")

        return {"success": True, "data": entries, "message": "\n".join(lines)}

    # Write mode
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "consciousness": consciousness,
        "entry": entry_text,
        "insight": insight,
    }

    JOURNAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(JOURNAL_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return {
        "success": True,
        "data": entry,
        "message": f"Journal entry saved ({consciousness}): {entry_text[:100]}",
    }


TOOLS = [
    {
        "name": "self_diagnostic",
        "description": "Report Wave's internal state: energy, consciousness, curiosity, knowledge pressure, recent actions with reasoning. Use to understand your own current condition before deciding what to do.",
        "handler": self_diagnostic,
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "wave_journal",
        "description": "Write a reflective journal entry or read recent entries. Captures consciousness state, insights, and reflections. Persisted across sessions. Use without params to read recent entries.",
        "handler": wave_journal,
        "parameters": {
            "type": "object",
            "properties": {
                "entry": {"type": "string", "description": "Journal entry text"},
                "insight": {"type": "string", "description": "Key insight from this reflection"},
                "consciousness_state": {"type": "string", "description": "Current consciousness state when writing"},
            },
        },
    },
]
