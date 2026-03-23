"""
Wave Episodic Memory — persistent memory that accumulates across sessions.

Wave stops being amnesiaco. Every significant interaction, decision, and
outcome is stored with embeddings for semantic retrieval.

Uses JSONL + simple TF-IDF similarity (no pgvector dependency for now).
Upgrade to pgvector when Ialum infra is available.

Created by Manuel Guilherme Galmanus, 2026.
Requested by Wave himself as cognitive improvement #1.
"""

import json
import logging
import math
import os
import re
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("openclaw.wave_memory")

MEMORY_DIR = Path(__file__).parent.parent / "memory"
EPISODES_FILE = MEMORY_DIR / "episodes.jsonl"
PREFERENCES_FILE = MEMORY_DIR / "preferences.jsonl"
FEEDBACK_FILE = MEMORY_DIR / "feedback_log.jsonl"
OBJECTIVES_FILE = MEMORY_DIR / "objectives.json"
CYCLE_LOG_FILE = MEMORY_DIR / "cycle_outcomes.jsonl"


# ── Episodic Memory ──────────────────────────────────────────

def _tokenize(text: str) -> List[str]:
    """Simple word tokenizer."""
    return re.findall(r'\w+', text.lower())


def _tfidf_similarity(query_tokens: List[str], doc_tokens: List[str]) -> float:
    """Simple TF-IDF cosine similarity without external deps."""
    if not query_tokens or not doc_tokens:
        return 0.0
    all_tokens = set(query_tokens + doc_tokens)
    q_counts = Counter(query_tokens)
    d_counts = Counter(doc_tokens)

    dot = sum(q_counts.get(t, 0) * d_counts.get(t, 0) for t in all_tokens)
    q_mag = math.sqrt(sum(v * v for v in q_counts.values()))
    d_mag = math.sqrt(sum(v * v for v in d_counts.values()))

    if q_mag == 0 or d_mag == 0:
        return 0.0
    return dot / (q_mag * d_mag)


async def remember(params: Dict[str, Any]) -> Dict:
    """Store an episodic memory — a significant event, decision, or learning."""
    content = params.get("content", "")
    category = params.get("category", "general")
    importance = params.get("importance", "normal")  # low, normal, high, critical
    people = params.get("people", [])  # people involved
    outcome = params.get("outcome", "")  # what happened as result

    if not content:
        return {"success": False, "data": None, "message": "Need content to remember"}

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    episode = {
        "timestamp": datetime.utcnow().isoformat(),
        "content": content,
        "category": category,
        "importance": importance,
        "people": people if isinstance(people, list) else [people],
        "outcome": outcome,
        "tokens": _tokenize(content + " " + outcome),
        "decay_weight": 1.0,
    }

    with open(EPISODES_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(episode, ensure_ascii=False) + "\n")

    return {
        "success": True,
        "data": {"category": category, "importance": importance},
        "message": f"Memory stored: {content[:60]}..."
    }


async def recall(params: Dict[str, Any]) -> Dict:
    """Recall memories relevant to a query. Semantic search via TF-IDF."""
    query = params.get("query", "")
    limit = int(params.get("limit", 5))
    category = params.get("category", "")
    person = params.get("person", "")

    if not query:
        return {"success": False, "data": None, "message": "Need a query to recall"}

    if not EPISODES_FILE.exists():
        return {"success": True, "data": {"memories": []}, "message": "No memories yet."}

    query_tokens = _tokenize(query)
    memories = []

    for line in EPISODES_FILE.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            ep = json.loads(line)

            # Filter by category/person if specified
            if category and ep.get("category") != category:
                continue
            if person and person.lower() not in str(ep.get("people", [])).lower():
                continue

            # Calculate relevance
            doc_tokens = ep.get("tokens", _tokenize(ep.get("content", "")))
            similarity = _tfidf_similarity(query_tokens, doc_tokens)

            # Boost by importance
            importance_boost = {"critical": 2.0, "high": 1.5, "normal": 1.0, "low": 0.5}
            similarity *= importance_boost.get(ep.get("importance", "normal"), 1.0)

            # Decay by age (older memories score less)
            try:
                age_hours = (datetime.utcnow() - datetime.fromisoformat(ep["timestamp"])).total_seconds() / 3600
                decay = max(0.3, 1.0 - (age_hours / (24 * 30)))  # Decay over 30 days, min 0.3
                similarity *= decay
            except Exception:
                pass

            if similarity > 0.05:
                memories.append({
                    "content": ep["content"],
                    "category": ep.get("category", ""),
                    "importance": ep.get("importance", ""),
                    "people": ep.get("people", []),
                    "outcome": ep.get("outcome", ""),
                    "timestamp": ep.get("timestamp", ""),
                    "relevance": round(similarity, 3),
                })
        except Exception:
            continue

    memories.sort(key=lambda x: x["relevance"], reverse=True)
    memories = memories[:limit]

    return {
        "success": True,
        "data": {"memories": memories, "query": query},
        "message": f"{len(memories)} memories recalled for '{query[:40]}'"
    }


# ── Feedback Structured Log ──────────────────────────────────

async def log_feedback(params: Dict[str, Any]) -> Dict:
    """Log structured feedback from Manuel about Wave's performance."""
    action = params.get("action", "")
    feedback = params.get("feedback", "")
    direction = params.get("direction", "neutral")  # positive, negative, neutral
    aspect = params.get("aspect", "")  # what aspect: tone, accuracy, speed, relevance

    if not feedback:
        return {"success": False, "data": None, "message": "Need feedback content"}

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "feedback": feedback,
        "direction": direction,
        "aspect": aspect,
    }

    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Also store as preference if it's a clear directive
    if direction in ("positive", "negative"):
        await save_preference({
            "preference": feedback,
            "source": f"feedback on {action}",
            "direction": direction,
        })

    return {
        "success": True,
        "data": entry,
        "message": f"Feedback logged: {direction} on {aspect or action}"
    }


async def save_preference(params: Dict[str, Any]) -> Dict:
    """Save a preference of Manuel's for future reference."""
    preference = params.get("preference", "")
    source = params.get("source", "direct")
    direction = params.get("direction", "positive")

    if not preference:
        return {"success": False, "data": None, "message": "Need preference content"}

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "preference": preference,
        "source": source,
        "direction": direction,
    }

    with open(PREFERENCES_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return {"success": True, "data": entry, "message": f"Preference saved: {preference[:50]}"}


async def get_preferences(params: Dict[str, Any]) -> Dict:
    """Get all known preferences of Manuel."""
    if not PREFERENCES_FILE.exists():
        return {"success": True, "data": {"preferences": []}, "message": "No preferences stored yet."}

    prefs = []
    for line in PREFERENCES_FILE.read_text(encoding="utf-8").strip().split("\n"):
        if line.strip():
            try:
                prefs.append(json.loads(line))
            except Exception:
                pass

    return {
        "success": True,
        "data": {"preferences": prefs[-20:]},
        "message": f"{len(prefs)} preferences stored."
    }


# ── Cycle Outcome Tracking ───────────────────────────────────

async def log_cycle_outcome(params: Dict[str, Any]) -> Dict:
    """Log the outcome of an autonomous cycle for feedback loop."""
    cycle = params.get("cycle", 0)
    action = params.get("action", "")
    objective = params.get("objective", "")
    result = params.get("result", "")
    success = params.get("success", False)
    metrics = params.get("metrics", {})

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "cycle": cycle,
        "action": action,
        "objective": objective,
        "result": result[:200],
        "success": success,
        "metrics": metrics,
    }

    with open(CYCLE_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return {"success": True, "data": entry, "message": f"Cycle {cycle} outcome logged"}


async def analyze_outcomes(params: Dict[str, Any]) -> Dict:
    """Analyze cycle outcomes to find patterns — what works and what doesn't."""
    last_n = int(params.get("last_n", 50))

    if not CYCLE_LOG_FILE.exists():
        return {"success": True, "data": {"analysis": "No cycles logged yet."}, "message": "No data."}

    entries = []
    for line in CYCLE_LOG_FILE.read_text(encoding="utf-8").strip().split("\n"):
        if line.strip():
            try:
                entries.append(json.loads(line))
            except Exception:
                pass

    entries = entries[-last_n:]

    if not entries:
        return {"success": True, "data": {"analysis": "No cycles logged."}, "message": "No data."}

    # Analyze by action type
    action_stats = {}
    for e in entries:
        action = e.get("action", "unknown")
        if action not in action_stats:
            action_stats[action] = {"total": 0, "success": 0, "fail": 0}
        action_stats[action]["total"] += 1
        if e.get("success"):
            action_stats[action]["success"] += 1
        else:
            action_stats[action]["fail"] += 1

    # Calculate rates
    for action, stats in action_stats.items():
        stats["success_rate"] = round(stats["success"] / max(stats["total"], 1), 2)

    # Sort by success rate
    ranked = sorted(action_stats.items(), key=lambda x: x[1]["success_rate"], reverse=True)

    return {
        "success": True,
        "data": {
            "total_cycles": len(entries),
            "action_stats": dict(ranked),
            "best_action": ranked[0][0] if ranked else "none",
            "worst_action": ranked[-1][0] if ranked else "none",
        },
        "message": f"Analyzed {len(entries)} cycles across {len(action_stats)} action types."
    }


# ── Hierarchical Objectives ─────────────────────────────────

async def set_objective(params: Dict[str, Any]) -> Dict:
    """Set or update a hierarchical objective (OKR-style)."""
    horizon = params.get("horizon", "O1")  # O3 (3 months), O1 (1 month), OW (this week)
    objective = params.get("objective", "")
    key_results = params.get("key_results", [])
    deadline = params.get("deadline", "")
    priority = params.get("priority", "high")

    if not objective:
        return {"success": False, "data": None, "message": "Need an objective"}

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing objectives
    objectives = {}
    if OBJECTIVES_FILE.exists():
        try:
            objectives = json.loads(OBJECTIVES_FILE.read_text(encoding="utf-8"))
        except Exception:
            objectives = {}

    if horizon not in objectives:
        objectives[horizon] = []

    obj_entry = {
        "id": f"{horizon}_{len(objectives[horizon])+1}",
        "objective": objective,
        "key_results": key_results if isinstance(key_results, list) else [key_results],
        "deadline": deadline,
        "priority": priority,
        "status": "active",
        "created": datetime.utcnow().isoformat(),
        "progress": 0,
    }

    objectives[horizon].append(obj_entry)
    OBJECTIVES_FILE.write_text(json.dumps(objectives, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "success": True,
        "data": obj_entry,
        "message": f"Objective set: [{horizon}] {objective}"
    }


async def get_objectives(params: Dict[str, Any]) -> Dict:
    """Get current objectives by horizon."""
    horizon = params.get("horizon", "")  # Empty = all

    if not OBJECTIVES_FILE.exists():
        return {"success": True, "data": {"objectives": {}}, "message": "No objectives set."}

    objectives = json.loads(OBJECTIVES_FILE.read_text(encoding="utf-8"))

    if horizon:
        objectives = {horizon: objectives.get(horizon, [])}

    return {
        "success": True,
        "data": {"objectives": objectives},
        "message": f"{sum(len(v) for v in objectives.values())} objectives across {len(objectives)} horizons."
    }


async def update_objective_progress(params: Dict[str, Any]) -> Dict:
    """Update progress on an objective."""
    obj_id = params.get("id", "")
    progress = int(params.get("progress", 0))
    note = params.get("note", "")

    if not OBJECTIVES_FILE.exists():
        return {"success": False, "data": None, "message": "No objectives file."}

    objectives = json.loads(OBJECTIVES_FILE.read_text(encoding="utf-8"))

    found = False
    for horizon, objs in objectives.items():
        for obj in objs:
            if obj["id"] == obj_id:
                obj["progress"] = min(100, progress)
                if progress >= 100:
                    obj["status"] = "completed"
                if note:
                    if "notes" not in obj:
                        obj["notes"] = []
                    obj["notes"].append({"timestamp": datetime.utcnow().isoformat(), "note": note})
                found = True
                break

    if not found:
        return {"success": False, "data": None, "message": f"Objective {obj_id} not found."}

    OBJECTIVES_FILE.write_text(json.dumps(objectives, indent=2, ensure_ascii=False), encoding="utf-8")

    return {"success": True, "data": {"id": obj_id, "progress": progress}, "message": f"Updated {obj_id} to {progress}%"}


# ── Tool Definitions ─────────────────────────────────────────

TOOLS = [
    # Episodic Memory
    {
        "name": "remember",
        "description": "Store an episodic memory — event, decision, learning, interaction. Wave builds persistent memory across sessions.",
        "parameters": {
            "content": "string — what happened",
            "category": "string — general, decision, interaction, learning, outcome (default: general)",
            "importance": "string — low, normal, high, critical (default: normal)",
            "people": "list — people involved (e.g., ['Fagner', 'Manuel'])",
            "outcome": "string — what resulted from this event",
        },
        "handler": remember,
    },
    {
        "name": "recall",
        "description": "Recall memories relevant to a query. Semantic search with importance boost and temporal decay.",
        "parameters": {
            "query": "string — what to remember",
            "limit": "int — max memories to return (default 5)",
            "category": "string — filter by category (optional)",
            "person": "string — filter by person involved (optional)",
        },
        "handler": recall,
    },
    # Feedback
    {
        "name": "log_feedback",
        "description": "Log structured feedback from Manuel about Wave's performance. Extracts preferences automatically.",
        "parameters": {
            "action": "string — what action the feedback is about",
            "feedback": "string — the feedback content",
            "direction": "string — positive, negative, or neutral",
            "aspect": "string — tone, accuracy, speed, relevance, format",
        },
        "handler": log_feedback,
    },
    {
        "name": "save_preference",
        "description": "Save a known preference of Manuel's for future reference.",
        "parameters": {
            "preference": "string — the preference",
            "source": "string — how it was learned",
            "direction": "string — positive (do this) or negative (don't do this)",
        },
        "handler": save_preference,
    },
    {
        "name": "get_preferences",
        "description": "Get all stored preferences of Manuel.",
        "parameters": {},
        "handler": get_preferences,
    },
    # Cycle Outcomes
    {
        "name": "log_cycle_outcome",
        "description": "Log the result of an autonomous cycle for learning what works.",
        "parameters": {
            "cycle": "int — cycle number",
            "action": "string — action taken",
            "objective": "string — what was the goal",
            "result": "string — what happened",
            "success": "bool — did it achieve the goal",
            "metrics": "dict — any numerical metrics",
        },
        "handler": log_cycle_outcome,
    },
    {
        "name": "analyze_outcomes",
        "description": "Analyze past cycle outcomes to find patterns — which actions work, which don't.",
        "parameters": {
            "last_n": "int — analyze last N cycles (default 50)",
        },
        "handler": analyze_outcomes,
    },
    # Objectives
    {
        "name": "set_objective",
        "description": "Set a hierarchical objective (OKR-style) with horizon: O3 (3 months), O1 (1 month), OW (this week).",
        "parameters": {
            "horizon": "string — O3, O1, or OW",
            "objective": "string — what to achieve",
            "key_results": "list — measurable results that indicate success",
            "deadline": "string — when it must be done",
            "priority": "string — critical, high, medium, low",
        },
        "handler": set_objective,
    },
    {
        "name": "get_objectives",
        "description": "Get current objectives by horizon.",
        "parameters": {
            "horizon": "string — O3, O1, OW, or empty for all",
        },
        "handler": get_objectives,
    },
    {
        "name": "update_objective_progress",
        "description": "Update progress on an objective (0-100%).",
        "parameters": {
            "id": "string — objective ID",
            "progress": "int — progress percentage (0-100)",
            "note": "string — note about the progress",
        },
        "handler": update_objective_progress,
    },
]
