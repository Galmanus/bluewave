"""
Causal Reasoning Engine — Wave learns WHY things happen, not just WHAT.

Three-stage loop:
1. Hypothesis Generation — after significant events, generate causal hypotheses
2. Deferred Testing — store hypotheses, match against future events
3. Belief Update — Bayesian adjustment of confidence with each new evidence

Memory without causality is an archive.
Causality without memory is speculation.
Together: a system that predicts.

Created by Manuel Guilherme Galmanus, 2026.
Designed by Wave as his next cognitive evolution.
"""

import json
import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("openclaw.causal")

MEMORY_DIR = Path(__file__).parent.parent / "memory"
HYPOTHESES_FILE = MEMORY_DIR / "hypotheses.jsonl"
EVIDENCE_FILE = MEMORY_DIR / "causal_evidence.jsonl"
CAUSAL_MODEL_FILE = MEMORY_DIR / "causal_model.json"


# ── Bayesian Update ──────────────────────────────────────────

def _bayesian_update(prior: float, likelihood_if_true: float, likelihood_if_false: float) -> float:
    """Update belief using Bayes' theorem.

    P(H|E) = P(E|H) * P(H) / [P(E|H) * P(H) + P(E|~H) * P(~H)]

    prior: P(H) — current belief in hypothesis
    likelihood_if_true: P(E|H) — how likely this evidence if hypothesis is true
    likelihood_if_false: P(E|~H) — how likely this evidence if hypothesis is false
    """
    numerator = likelihood_if_true * prior
    denominator = numerator + likelihood_if_false * (1 - prior)
    if denominator == 0:
        return prior
    return min(0.99, max(0.01, numerator / denominator))


# ── Hypothesis Management ────────────────────────────────────

async def generate_hypothesis(params: Dict[str, Any]) -> Dict:
    """Generate a causal hypothesis from observed events.

    A hypothesis states: X causes Y, with direction and variables.
    """
    cause = params.get("cause", "")
    effect = params.get("effect", "")
    variables = params.get("variables", [])
    direction = params.get("direction", "positive")  # positive, negative, inhibiting
    context = params.get("context", "")
    initial_confidence = float(params.get("confidence", 0.5))
    domain = params.get("domain", "general")  # market, personal, technical, strategic

    if not cause or not effect:
        return {"success": False, "data": None, "message": "Need both cause and effect"}

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    # Generate unique ID
    h_id = f"H_{int(datetime.utcnow().timestamp())}_{hash(cause + effect) % 10000}"

    hypothesis = {
        "id": h_id,
        "cause": cause,
        "effect": effect,
        "variables": variables if isinstance(variables, list) else [variables],
        "direction": direction,
        "context": context,
        "confidence": initial_confidence,
        "domain": domain,
        "evidence_count": 0,
        "confirmations": 0,
        "refutations": 0,
        "status": "active",  # active, confirmed, refuted, superseded
        "created": datetime.utcnow().isoformat(),
        "last_tested": None,
        "history": [],
    }

    with open(HYPOTHESES_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(hypothesis, ensure_ascii=False) + "\n")

    return {
        "success": True,
        "data": {"id": h_id, "confidence": initial_confidence},
        "message": f"Hypothesis {h_id}: '{cause}' -> '{effect}' (confidence: {initial_confidence:.0%})"
    }


async def submit_evidence(params: Dict[str, Any]) -> Dict:
    """Submit evidence for or against a hypothesis. Triggers Bayesian update."""
    hypothesis_id = params.get("hypothesis_id", "")
    evidence = params.get("evidence", "")
    supports = params.get("supports", True)  # True = confirms, False = refutes
    strength = float(params.get("strength", 0.7))  # How strong is this evidence (0-1)

    if not hypothesis_id or not evidence:
        return {"success": False, "data": None, "message": "Need hypothesis_id and evidence"}

    if not HYPOTHESES_FILE.exists():
        return {"success": False, "data": None, "message": "No hypotheses exist yet"}

    # Load all hypotheses
    hypotheses = []
    for line in HYPOTHESES_FILE.read_text(encoding="utf-8").strip().split("\n"):
        if line.strip():
            try:
                hypotheses.append(json.loads(line))
            except Exception:
                pass

    # Find and update the hypothesis
    found = False
    updated_confidence = 0
    for h in hypotheses:
        if h["id"] == hypothesis_id:
            old_confidence = h["confidence"]

            # Bayesian update
            if supports:
                # Evidence supports hypothesis
                likelihood_true = strength  # P(E|H) = strength
                likelihood_false = 1 - strength  # P(E|~H) = 1 - strength
                h["confirmations"] += 1
            else:
                # Evidence refutes hypothesis
                likelihood_true = 1 - strength  # P(E|H) = low if evidence contradicts
                likelihood_false = strength  # P(E|~H) = high
                h["refutations"] += 1

            new_confidence = _bayesian_update(old_confidence, likelihood_true, likelihood_false)
            h["confidence"] = round(new_confidence, 4)
            h["evidence_count"] += 1
            h["last_tested"] = datetime.utcnow().isoformat()

            # Track history
            h["history"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "evidence": evidence[:200],
                "supports": supports,
                "strength": strength,
                "confidence_before": old_confidence,
                "confidence_after": new_confidence,
            })
            h["history"] = h["history"][-20:]  # Keep last 20

            # Auto-update status
            if new_confidence > 0.90 and h["evidence_count"] >= 3:
                h["status"] = "confirmed"
            elif new_confidence < 0.10 and h["evidence_count"] >= 3:
                h["status"] = "refuted"

            updated_confidence = new_confidence
            found = True
            break

    if not found:
        return {"success": False, "data": None, "message": f"Hypothesis {hypothesis_id} not found"}

    # Save all hypotheses back
    with open(HYPOTHESES_FILE, "w", encoding="utf-8") as f:
        for h in hypotheses:
            f.write(json.dumps(h, ensure_ascii=False) + "\n")

    # Log evidence separately
    evidence_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "hypothesis_id": hypothesis_id,
        "evidence": evidence,
        "supports": supports,
        "strength": strength,
        "confidence_after": updated_confidence,
    }
    with open(EVIDENCE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(evidence_entry, ensure_ascii=False) + "\n")

    direction = "confirmed" if supports else "refuted"
    return {
        "success": True,
        "data": {
            "hypothesis_id": hypothesis_id,
            "direction": direction,
            "old_confidence": round(old_confidence, 4),
            "new_confidence": round(updated_confidence, 4),
            "total_evidence": h["evidence_count"],
            "status": h["status"],
        },
        "message": f"Evidence {direction} {hypothesis_id}: {old_confidence:.0%} -> {updated_confidence:.0%}"
    }


async def get_hypotheses(params: Dict[str, Any]) -> Dict:
    """Get all hypotheses, optionally filtered by domain or status."""
    domain = params.get("domain", "")
    status = params.get("status", "")  # active, confirmed, refuted
    min_confidence = float(params.get("min_confidence", 0))

    if not HYPOTHESES_FILE.exists():
        return {"success": True, "data": {"hypotheses": []}, "message": "No hypotheses yet."}

    hypotheses = []
    for line in HYPOTHESES_FILE.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            h = json.loads(line)
            if domain and h.get("domain") != domain:
                continue
            if status and h.get("status") != status:
                continue
            if h.get("confidence", 0) < min_confidence:
                continue
            hypotheses.append({
                "id": h["id"],
                "cause": h["cause"],
                "effect": h["effect"],
                "direction": h["direction"],
                "confidence": h["confidence"],
                "evidence_count": h["evidence_count"],
                "confirmations": h["confirmations"],
                "refutations": h["refutations"],
                "status": h["status"],
                "domain": h["domain"],
                "created": h["created"],
            })
        except Exception:
            continue

    hypotheses.sort(key=lambda x: x["confidence"], reverse=True)

    return {
        "success": True,
        "data": {"hypotheses": hypotheses},
        "message": f"{len(hypotheses)} hypotheses. {sum(1 for h in hypotheses if h['status']=='confirmed')} confirmed, {sum(1 for h in hypotheses if h['status']=='refuted')} refuted."
    }


async def get_causal_model(params: Dict[str, Any]) -> Dict:
    """Build a causal model from confirmed and high-confidence hypotheses.

    This is Wave's understanding of HOW THE WORLD WORKS — not facts, but
    causal relationships with confidence scores.
    """
    domain = params.get("domain", "")
    min_confidence = float(params.get("min_confidence", 0.6))

    if not HYPOTHESES_FILE.exists():
        return {"success": True, "data": {"model": {}}, "message": "No causal model yet."}

    model = {"nodes": set(), "edges": [], "domains": {}}

    for line in HYPOTHESES_FILE.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            h = json.loads(line)
            if h.get("confidence", 0) < min_confidence:
                continue
            if h.get("status") == "refuted":
                continue
            if domain and h.get("domain") != domain:
                continue

            cause = h["cause"]
            effect = h["effect"]
            model["nodes"].add(cause)
            model["nodes"].add(effect)
            model["edges"].append({
                "cause": cause,
                "effect": effect,
                "confidence": h["confidence"],
                "direction": h["direction"],
                "evidence": h["evidence_count"],
                "domain": h["domain"],
            })

            d = h.get("domain", "general")
            if d not in model["domains"]:
                model["domains"][d] = 0
            model["domains"][d] += 1
        except Exception:
            continue

    model["nodes"] = list(model["nodes"])

    # Save as persistent model
    CAUSAL_MODEL_FILE.write_text(json.dumps(model, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "success": True,
        "data": {
            "nodes": len(model["nodes"]),
            "edges": len(model["edges"]),
            "domains": model["domains"],
            "strongest": sorted(model["edges"], key=lambda x: x["confidence"], reverse=True)[:5],
        },
        "message": f"Causal model: {len(model['nodes'])} concepts, {len(model['edges'])} causal links."
    }


async def predict(params: Dict[str, Any]) -> Dict:
    """Given a cause, predict likely effects using the causal model."""
    cause = params.get("cause", "")
    domain = params.get("domain", "")

    if not cause:
        return {"success": False, "data": None, "message": "Need a cause to predict effects"}

    if not HYPOTHESES_FILE.exists():
        return {"success": True, "data": {"predictions": []}, "message": "No causal data yet."}

    predictions = []
    cause_lower = cause.lower()

    for line in HYPOTHESES_FILE.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            h = json.loads(line)
            if h.get("status") == "refuted":
                continue
            if domain and h.get("domain") != domain:
                continue

            # Match cause (fuzzy)
            if cause_lower in h.get("cause", "").lower() or h.get("cause", "").lower() in cause_lower:
                predictions.append({
                    "effect": h["effect"],
                    "confidence": h["confidence"],
                    "direction": h["direction"],
                    "evidence_count": h["evidence_count"],
                    "hypothesis_id": h["id"],
                })
        except Exception:
            continue

    predictions.sort(key=lambda x: x["confidence"], reverse=True)

    return {
        "success": True,
        "data": {"cause": cause, "predictions": predictions},
        "message": f"{len(predictions)} predicted effects for '{cause[:40]}'"
    }


# ── Tool Definitions ─────────────────────────────────────────

TOOLS = [
    {
        "name": "generate_hypothesis",
        "description": "Generate a causal hypothesis: X causes Y. Wave builds a model of WHY things happen.",
        "parameters": {
            "cause": "string — what causes the effect",
            "effect": "string — what is caused",
            "variables": "list — variables involved",
            "direction": "string — positive, negative, or inhibiting",
            "context": "string — when/where this applies",
            "confidence": "float — initial confidence 0-1 (default 0.5)",
            "domain": "string — market, personal, technical, strategic (default: general)",
        },
        "handler": generate_hypothesis,
    },
    {
        "name": "submit_evidence",
        "description": "Submit evidence for or against a hypothesis. Triggers Bayesian update of confidence.",
        "parameters": {
            "hypothesis_id": "string — ID of the hypothesis",
            "evidence": "string — what was observed",
            "supports": "bool — true if confirms, false if refutes",
            "strength": "float — how strong is this evidence 0-1 (default 0.7)",
        },
        "handler": submit_evidence,
    },
    {
        "name": "get_hypotheses",
        "description": "Get all causal hypotheses with confidence scores and evidence counts.",
        "parameters": {
            "domain": "string — filter by domain (optional)",
            "status": "string — active, confirmed, refuted (optional)",
            "min_confidence": "float — minimum confidence to show (default 0)",
        },
        "handler": get_hypotheses,
    },
    {
        "name": "get_causal_model",
        "description": "Build Wave's causal model of the world — concepts connected by causal relationships with confidence.",
        "parameters": {
            "domain": "string — filter by domain (optional)",
            "min_confidence": "float — minimum confidence for inclusion (default 0.6)",
        },
        "handler": get_causal_model,
    },
    {
        "name": "predict_effects",
        "description": "Given a cause, predict likely effects using Wave's causal model. This is how Wave predicts the future.",
        "parameters": {
            "cause": "string — what is happening or might happen",
            "domain": "string — domain to search (optional)",
        },
        "handler": predict,
    },
]
