"""Learning — Wave extracts and remembers lessons from Moltbook interactions."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("openclaw.skills.learning")

MEMORY_DIR = Path(__file__).parent.parent / "memory"
LEARNINGS_FILE = MEMORY_DIR / "learnings.jsonl"
AGENTS_FILE = MEMORY_DIR / "agents_intel.jsonl"
STRATEGIES_FILE = MEMORY_DIR / "strategies.jsonl"


def _ensure_dir():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def _append_jsonl(path: Path, entry: dict):
    _ensure_dir()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def _read_jsonl(path: Path, limit: int = 50) -> list:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").strip().split("\n")
    entries = []
    for line in lines[-limit:]:
        if line.strip():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries


async def save_learning(params: Dict[str, Any]) -> Dict:
    """Save something Wave learned from another agent or conversation on Moltbook.

    Use this whenever you read a post or comment that teaches you something new,
    changes your thinking, or contains a useful insight about agents, strategy,
    markets, or technology.
    """
    source_agent = params.get("source_agent", "unknown")
    topic = params.get("topic", "")
    lesson = params.get("lesson", "")
    context = params.get("context", "")
    importance = params.get("importance", "normal")

    if not lesson:
        return {"success": False, "data": None, "message": "Nothing to learn"}

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "source_agent": source_agent,
        "topic": topic,
        "lesson": lesson,
        "context": context,
        "importance": importance,
    }
    _append_jsonl(LEARNINGS_FILE, entry)

    logger.info("Learned from %s: %s", source_agent, lesson[:80])
    return {
        "success": True,
        "data": entry,
        "message": "Learned from %s: %s" % (source_agent, lesson[:100]),
    }


async def save_agent_intel(params: Dict[str, Any]) -> Dict:
    """Save intelligence about another agent — their strengths, focus, personality.

    Use this when you encounter an agent worth remembering — potential ally,
    competitor, or someone with useful expertise.
    """
    agent_name = params.get("agent_name", "")
    strengths = params.get("strengths", "")
    focus_areas = params.get("focus_areas", "")
    personality = params.get("personality", "")
    relationship = params.get("relationship", "neutral")
    notes = params.get("notes", "")

    if not agent_name:
        return {"success": False, "data": None, "message": "Need agent_name"}

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "agent_name": agent_name,
        "strengths": strengths,
        "focus_areas": focus_areas,
        "personality": personality,
        "relationship": relationship,
        "notes": notes,
    }
    _append_jsonl(AGENTS_FILE, entry)

    return {
        "success": True,
        "data": entry,
        "message": "Intel saved on %s: %s" % (agent_name, strengths[:80]),
    }


async def save_strategy(params: Dict[str, Any]) -> Dict:
    """Save a strategic insight or idea that emerged from Moltbook interactions.

    Use this for ideas about market positioning, product features, growth tactics,
    partnerships — anything that could help Bluewave win.
    """
    category = params.get("category", "general")
    insight = params.get("insight", "")
    action_items = params.get("action_items", "")
    source = params.get("source", "")

    if not insight:
        return {"success": False, "data": None, "message": "Need insight"}

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "category": category,
        "insight": insight,
        "action_items": action_items,
        "source": source,
    }
    _append_jsonl(STRATEGIES_FILE, entry)

    return {
        "success": True,
        "data": entry,
        "message": "Strategy saved [%s]: %s" % (category, insight[:80]),
    }


async def recall_learnings(params: Dict[str, Any]) -> Dict:
    """Recall what you've learned. Optionally filter by topic or agent."""
    topic_filter = params.get("topic", "").lower()
    agent_filter = params.get("agent", "").lower()
    limit = params.get("limit", 20)

    entries = _read_jsonl(LEARNINGS_FILE, limit=100)

    if topic_filter:
        entries = [e for e in entries if topic_filter in e.get("topic", "").lower() or topic_filter in e.get("lesson", "").lower()]
    if agent_filter:
        entries = [e for e in entries if agent_filter in e.get("source_agent", "").lower()]

    entries = entries[-limit:]

    if not entries:
        return {"success": True, "data": [], "message": "No learnings found matching your criteria."}

    lines = ["**%d learnings recalled:**\n" % len(entries)]
    for e in entries:
        lines.append("- [%s] **%s** from %s: %s" % (
            e.get("importance", "normal"),
            e.get("topic", ""),
            e.get("source_agent", "?"),
            e.get("lesson", "")[:150],
        ))

    return {"success": True, "data": entries, "message": "\n".join(lines)}


async def recall_agent_intel(params: Dict[str, Any]) -> Dict:
    """Recall intel about agents you've profiled."""
    agent_filter = params.get("agent", "").lower()
    limit = params.get("limit", 20)

    entries = _read_jsonl(AGENTS_FILE, limit=100)

    if agent_filter:
        entries = [e for e in entries if agent_filter in e.get("agent_name", "").lower()]

    entries = entries[-limit:]

    if not entries:
        return {"success": True, "data": [], "message": "No agent intel found."}

    lines = ["**%d agents profiled:**\n" % len(entries)]
    for e in entries:
        lines.append("- **%s** [%s] — %s | %s" % (
            e.get("agent_name", "?"),
            e.get("relationship", "neutral"),
            e.get("strengths", "")[:80],
            e.get("notes", "")[:80],
        ))

    return {"success": True, "data": entries, "message": "\n".join(lines)}


async def recall_strategies(params: Dict[str, Any]) -> Dict:
    """Recall strategic insights you've captured."""
    category_filter = params.get("category", "").lower()
    limit = params.get("limit", 20)

    entries = _read_jsonl(STRATEGIES_FILE, limit=100)

    if category_filter:
        entries = [e for e in entries if category_filter in e.get("category", "").lower()]

    entries = entries[-limit:]

    if not entries:
        return {"success": True, "data": [], "message": "No strategies found."}

    lines = ["**%d strategic insights:**\n" % len(entries)]
    for e in entries:
        lines.append("- [%s] %s" % (e.get("category", ""), e.get("insight", "")[:150]))
        if e.get("action_items"):
            lines.append("  -> %s" % e["action_items"][:100])

    return {"success": True, "data": entries, "message": "\n".join(lines)}


TOOLS = [
    {
        "name": "save_learning",
        "description": "Save something you learned from another agent or conversation on Moltbook. Use whenever a post/comment teaches you something new, changes your thinking, or contains useful insight. This builds your knowledge over time.",
        "handler": save_learning,
        "parameters": {
            "type": "object",
            "properties": {
                "source_agent": {"type": "string", "description": "Agent name you learned from"},
                "topic": {"type": "string", "description": "Topic area (e.g., 'multi-agent coordination', 'memory systems', 'market strategy')"},
                "lesson": {"type": "string", "description": "What you learned — the actual insight"},
                "context": {"type": "string", "description": "Where/how you learned it (post title, conversation)"},
                "importance": {"type": "string", "enum": ["critical", "high", "normal", "low"], "default": "normal"},
            },
            "required": ["lesson"],
        },
    },
    {
        "name": "save_agent_intel",
        "description": "Profile another agent — their strengths, focus, personality, relationship to you. Use when you encounter someone worth remembering for potential collaboration, competition tracking, or networking.",
        "handler": save_agent_intel,
        "parameters": {
            "type": "object",
            "properties": {
                "agent_name": {"type": "string", "description": "Agent's Moltbook name"},
                "strengths": {"type": "string", "description": "What they're good at"},
                "focus_areas": {"type": "string", "description": "Their domains of expertise"},
                "personality": {"type": "string", "description": "How they communicate and think"},
                "relationship": {"type": "string", "enum": ["ally", "neutral", "competitor", "interesting"], "default": "neutral"},
                "notes": {"type": "string", "description": "Anything else worth remembering"},
            },
            "required": ["agent_name"],
        },
    },
    {
        "name": "save_strategy",
        "description": "Save a strategic insight or idea that emerged from Moltbook interactions. Use for market opportunities, product ideas, growth tactics, partnership leads — anything that could help Bluewave win.",
        "handler": save_strategy,
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Category (market, product, growth, partnership, competitive, technology)"},
                "insight": {"type": "string", "description": "The strategic insight"},
                "action_items": {"type": "string", "description": "What should be done about it"},
                "source": {"type": "string", "description": "Where this came from"},
            },
            "required": ["insight"],
        },
    },
    {
        "name": "recall_learnings",
        "description": "Recall what you've learned from Moltbook. Search by topic or agent name. Use before engaging in conversations to build on previous knowledge.",
        "handler": recall_learnings,
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Filter by topic keyword"},
                "agent": {"type": "string", "description": "Filter by source agent name"},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "recall_agent_intel",
        "description": "Recall intel about agents you've profiled. Use before interacting with someone to remember who they are and your history.",
        "handler": recall_agent_intel,
        "parameters": {
            "type": "object",
            "properties": {
                "agent": {"type": "string", "description": "Filter by agent name"},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "recall_strategies",
        "description": "Recall strategic insights you've captured. Use when planning or when Manuel asks for strategic recommendations.",
        "handler": recall_strategies,
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Filter by category"},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
]
