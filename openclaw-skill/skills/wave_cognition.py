"""
Wave Advanced Cognition — Phase 2 cognitive upgrades.

3 systems Wave requested:
1. Skill Evolution — skills improve based on outcome data
2. Stakeholder Modeling — dynamic PUT profiles of key people
3. Auditable Reasoning — chain-of-thought logging with confidence

Created by Manuel Guilherme Galmanus, 2026.
Requested by Wave as cognitive improvements #3, #4, #7.
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("openclaw.wave_cognition")

MEMORY_DIR = Path(__file__).parent.parent / "memory"
SKILL_PERF_FILE = MEMORY_DIR / "skill_performance.jsonl"
STAKEHOLDERS_FILE = MEMORY_DIR / "stakeholders.json"
REASONING_FILE = MEMORY_DIR / "reasoning_chains.jsonl"


# ══════════════════════════════════════════════════════════════
# 1. SKILL EVOLUTION — skills improve based on outcome
# ══════════════════════════════════════════════════════════════

async def log_skill_use(params: Dict[str, Any]) -> Dict:
    """Log a skill execution with context and outcome for evolution tracking."""
    skill_name = params.get("skill", "")
    context = params.get("context", "")
    output_quality = params.get("quality", 0.5)  # 0.0 to 1.0
    outcome = params.get("outcome", "")  # what happened after
    engagement = params.get("engagement", 0)  # likes, replies, clicks
    converted = params.get("converted", False)  # did it lead to revenue

    if not skill_name:
        return {"success": False, "data": None, "message": "Need skill name"}

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "skill": skill_name,
        "context": context[:200],
        "quality": float(output_quality),
        "outcome": outcome[:200],
        "engagement": int(engagement),
        "converted": bool(converted),
    }

    with open(SKILL_PERF_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return {"success": True, "data": entry, "message": f"Skill use logged: {skill_name}"}


async def analyze_skill_performance(params: Dict[str, Any]) -> Dict:
    """Analyze which skills perform best and which need improvement."""
    if not SKILL_PERF_FILE.exists():
        return {"success": True, "data": {"analysis": "No skill data yet."}, "message": "No data."}

    skills = {}
    for line in SKILL_PERF_FILE.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            name = entry.get("skill", "unknown")
            if name not in skills:
                skills[name] = {
                    "uses": 0, "total_quality": 0, "total_engagement": 0,
                    "conversions": 0, "outcomes": [],
                }
            s = skills[name]
            s["uses"] += 1
            s["total_quality"] += entry.get("quality", 0.5)
            s["total_engagement"] += entry.get("engagement", 0)
            if entry.get("converted"):
                s["conversions"] += 1
            if entry.get("outcome"):
                s["outcomes"].append(entry["outcome"][:100])
        except Exception:
            continue

    # Calculate averages and rank
    ranked = []
    for name, s in skills.items():
        avg_quality = s["total_quality"] / max(s["uses"], 1)
        avg_engagement = s["total_engagement"] / max(s["uses"], 1)
        conversion_rate = s["conversions"] / max(s["uses"], 1)
        score = (avg_quality * 0.3) + (avg_engagement * 0.01) + (conversion_rate * 0.6)

        ranked.append({
            "skill": name,
            "uses": s["uses"],
            "avg_quality": round(avg_quality, 2),
            "avg_engagement": round(avg_engagement, 1),
            "conversion_rate": round(conversion_rate, 2),
            "composite_score": round(score, 3),
            "recent_outcomes": s["outcomes"][-3:],
        })

    ranked.sort(key=lambda x: x["composite_score"], reverse=True)

    # Identify improvement candidates
    needs_improvement = [s for s in ranked if s["composite_score"] < 0.3 and s["uses"] >= 3]

    return {
        "success": True,
        "data": {
            "total_skills_tracked": len(ranked),
            "top_performers": ranked[:5],
            "needs_improvement": needs_improvement[:5],
            "total_conversions": sum(s.get("conversions", 0) for s in skills.values()),
        },
        "message": f"Analyzed {len(ranked)} skills. {len(needs_improvement)} need improvement."
    }


async def suggest_skill_improvements(params: Dict[str, Any]) -> Dict:
    """Based on performance data, suggest specific improvements for underperforming skills."""
    analysis = await analyze_skill_performance({})
    if not analysis.get("success"):
        return analysis

    improvements = analysis["data"].get("needs_improvement", [])
    top = analysis["data"].get("top_performers", [])

    suggestions = []
    for skill in improvements:
        suggestion = {
            "skill": skill["skill"],
            "problem": f"Low composite score ({skill['composite_score']}) after {skill['uses']} uses",
            "avg_quality": skill["avg_quality"],
            "conversion_rate": skill["conversion_rate"],
            "recent_outcomes": skill["recent_outcomes"],
            "suggestion": "",
        }

        if skill["avg_quality"] < 0.4:
            suggestion["suggestion"] = "Output quality is low. Review prompt template. Compare with top performer patterns."
        elif skill["conversion_rate"] == 0:
            suggestion["suggestion"] = "Zero conversions despite decent quality. The skill produces good output that doesn't convert. Review targeting or CTA."
        elif skill["avg_engagement"] < 1:
            suggestion["suggestion"] = "Low engagement. Content may be technically good but not resonating. Test different angles or formats."
        else:
            suggestion["suggestion"] = "Mixed signals. Run A/B test with modified prompt template."

        suggestions.append(suggestion)

    return {
        "success": True,
        "data": {
            "suggestions": suggestions,
            "benchmark": f"Top performer: {top[0]['skill']} (score {top[0]['composite_score']})" if top else "No benchmark yet",
        },
        "message": f"{len(suggestions)} skills need improvement."
    }


# ══════════════════════════════════════════════════════════════
# 2. STAKEHOLDER MODELING — dynamic PUT profiles
# ══════════════════════════════════════════════════════════════

async def update_stakeholder(params: Dict[str, Any]) -> Dict:
    """Update or create a dynamic PUT profile for a stakeholder."""
    name = params.get("name", "")
    role = params.get("role", "")
    company = params.get("company", "")
    # PUT variables
    A = params.get("A")  # ambition
    F = params.get("F")  # fear
    k = params.get("k")  # shadow coefficient
    S = params.get("S")  # status
    w = params.get("w")  # pain
    # Observations
    observation = params.get("observation", "")
    signal = params.get("signal", "")  # what behavior was observed

    if not name:
        return {"success": False, "data": None, "message": "Need stakeholder name"}

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing
    stakeholders = {}
    if STAKEHOLDERS_FILE.exists():
        try:
            stakeholders = json.loads(STAKEHOLDERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            stakeholders = {}

    key = name.lower().replace(" ", "_")

    if key not in stakeholders:
        stakeholders[key] = {
            "name": name,
            "role": role,
            "company": company,
            "put": {"A": 0.5, "F": 0.5, "k": 0.2, "S": 0.5, "w": 0.3},
            "observations": [],
            "signals": [],
            "created": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "interaction_count": 0,
        }

    sh = stakeholders[key]

    # Update basic info
    if role:
        sh["role"] = role
    if company:
        sh["company"] = company

    # Update PUT variables (only if provided — preserves existing)
    if A is not None:
        sh["put"]["A"] = float(A)
    if F is not None:
        sh["put"]["F"] = float(F)
    if k is not None:
        sh["put"]["k"] = float(k)
    if S is not None:
        sh["put"]["S"] = float(S)
    if w is not None:
        sh["put"]["w"] = float(w)

    # Add observation
    if observation:
        sh["observations"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "observation": observation[:300],
        })
        sh["observations"] = sh["observations"][-20:]  # Keep last 20

    # Add signal
    if signal:
        sh["signals"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "signal": signal[:200],
        })
        sh["signals"] = sh["signals"][-20:]

    sh["last_updated"] = datetime.utcnow().isoformat()
    sh["interaction_count"] = sh.get("interaction_count", 0) + 1

    # Check for divergence from model
    divergence = None
    if len(sh["signals"]) >= 3:
        recent = sh["signals"][-3:]
        # Simple divergence check: if recent signals contradict PUT model
        # (e.g., high A predicted but behavior shows low initiative)
        divergence_note = f"Stakeholder has {len(sh['signals'])} signals. Review if PUT model still accurate."
        if sh["interaction_count"] % 5 == 0:
            divergence = divergence_note

    stakeholders[key] = sh
    STAKEHOLDERS_FILE.write_text(json.dumps(stakeholders, indent=2, ensure_ascii=False), encoding="utf-8")

    result = {
        "success": True,
        "data": {
            "name": name,
            "put": sh["put"],
            "interaction_count": sh["interaction_count"],
            "observations": len(sh["observations"]),
        },
        "message": f"Stakeholder updated: {name} (A={sh['put']['A']}, F={sh['put']['F']}, S={sh['put']['S']})"
    }

    if divergence:
        result["data"]["divergence_alert"] = divergence

    return result


async def get_stakeholder(params: Dict[str, Any]) -> Dict:
    """Get full profile of a stakeholder including PUT model and history."""
    name = params.get("name", "")

    if not STAKEHOLDERS_FILE.exists():
        return {"success": False, "data": None, "message": "No stakeholders tracked yet."}

    stakeholders = json.loads(STAKEHOLDERS_FILE.read_text(encoding="utf-8"))
    key = name.lower().replace(" ", "_")

    if key not in stakeholders:
        # Fuzzy search
        matches = [k for k in stakeholders if name.lower() in k]
        if matches:
            key = matches[0]
        else:
            return {"success": False, "data": None, "message": f"Stakeholder '{name}' not found. Known: {', '.join(stakeholders.keys())}"}

    sh = stakeholders[key]

    # Calculate derived PUT metrics
    put = sh["put"]
    Fk = put["F"] * (1 - put["k"])  # effective fear
    U = 1.0 * put["A"] * (1 - Fk) - 1.2 * Fk * (1 - put["S"]) + 0.8 * put["S"] * (1 - put["w"])
    FP = (1 - 0.5) * (0.3 + 0.2 + 0.5) / max(0.3 - U + 1e-3, 1e-3)

    return {
        "success": True,
        "data": {
            **sh,
            "derived": {
                "F_effective": round(Fk, 2),
                "U_psychic": round(U, 2),
                "FP_fracture": round(min(FP, 100), 1),
            }
        },
        "message": f"{sh['name']}: A={put['A']}, F={put['F']}, k={put['k']}, S={put['S']}, U={U:.2f}"
    }


async def list_stakeholders(params: Dict[str, Any]) -> Dict:
    """List all tracked stakeholders with summary PUT profiles."""
    if not STAKEHOLDERS_FILE.exists():
        return {"success": True, "data": {"stakeholders": []}, "message": "No stakeholders yet."}

    stakeholders = json.loads(STAKEHOLDERS_FILE.read_text(encoding="utf-8"))

    summary = []
    for key, sh in stakeholders.items():
        put = sh["put"]
        summary.append({
            "name": sh["name"],
            "role": sh.get("role", ""),
            "company": sh.get("company", ""),
            "A": put["A"],
            "F": put["F"],
            "S": put["S"],
            "interactions": sh.get("interaction_count", 0),
            "last_updated": sh.get("last_updated", ""),
        })

    return {
        "success": True,
        "data": {"stakeholders": summary},
        "message": f"{len(summary)} stakeholders tracked."
    }


# ══════════════════════════════════════════════════════════════
# 3. AUDITABLE REASONING — chain-of-thought with confidence
# ══════════════════════════════════════════════════════════════

async def log_reasoning(params: Dict[str, Any]) -> Dict:
    """Log a reasoning chain for a strategic decision — auditable thinking."""
    decision = params.get("decision", "")
    premises = params.get("premises", [])
    reasoning = params.get("reasoning", "")
    conclusion = params.get("conclusion", "")
    confidence = params.get("confidence", 0.5)  # 0.0 to 1.0
    alternatives = params.get("alternatives", [])
    risks = params.get("risks", [])

    if not decision:
        return {"success": False, "data": None, "message": "Need the decision being reasoned about"}

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "decision": decision,
        "premises": premises if isinstance(premises, list) else [premises],
        "reasoning": reasoning,
        "conclusion": conclusion,
        "confidence": float(confidence),
        "alternatives_considered": alternatives if isinstance(alternatives, list) else [alternatives],
        "risks_identified": risks if isinstance(risks, list) else [risks],
        "status": "active",  # active, invalidated, confirmed
    }

    with open(REASONING_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return {
        "success": True,
        "data": entry,
        "message": f"Reasoning logged: {decision[:50]}... (confidence: {confidence:.0%})"
    }


async def review_reasoning(params: Dict[str, Any]) -> Dict:
    """Review past reasoning chains. Check if premises still hold."""
    query = params.get("query", "")
    last_n = int(params.get("last_n", 10))

    if not REASONING_FILE.exists():
        return {"success": True, "data": {"chains": []}, "message": "No reasoning chains logged."}

    chains = []
    for line in REASONING_FILE.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            if query:
                if query.lower() not in json.dumps(entry).lower():
                    continue
            chains.append(entry)
        except Exception:
            continue

    chains = chains[-last_n:]

    # Check for potentially invalidated premises
    alerts = []
    for chain in chains:
        if chain.get("confidence", 1.0) < 0.4:
            alerts.append(f"Low confidence ({chain['confidence']:.0%}): {chain['decision'][:50]}")
        if chain.get("status") == "active":
            # Check age — old active reasoning might need review
            try:
                age_hours = (datetime.utcnow() - datetime.fromisoformat(chain["timestamp"])).total_seconds() / 3600
                if age_hours > 72:
                    alerts.append(f"Stale reasoning (>72h): {chain['decision'][:50]} — premises may have changed")
            except Exception:
                pass

    return {
        "success": True,
        "data": {
            "chains": chains,
            "alerts": alerts,
        },
        "message": f"{len(chains)} reasoning chains found. {len(alerts)} need review."
    }


async def invalidate_reasoning(params: Dict[str, Any]) -> Dict:
    """Mark a reasoning chain as invalidated — a premise was proven wrong."""
    decision = params.get("decision", "")
    reason = params.get("reason", "")

    if not decision or not REASONING_FILE.exists():
        return {"success": False, "data": None, "message": "Need decision identifier and existing chains."}

    lines = REASONING_FILE.read_text(encoding="utf-8").strip().split("\n")
    updated = []
    found = False

    for line in lines:
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            if decision.lower() in entry.get("decision", "").lower():
                entry["status"] = "invalidated"
                entry["invalidation_reason"] = reason
                entry["invalidated_at"] = datetime.utcnow().isoformat()
                found = True
            updated.append(json.dumps(entry, ensure_ascii=False))
        except Exception:
            updated.append(line)

    if found:
        REASONING_FILE.write_text("\n".join(updated) + "\n", encoding="utf-8")
        return {"success": True, "data": {"decision": decision}, "message": f"Reasoning invalidated: {decision[:50]}"}
    else:
        return {"success": False, "data": None, "message": f"No reasoning found matching '{decision[:50]}'"}


# ── Tool Definitions ─────────────────────────────────────────

TOOLS = [
    # Skill Evolution
    {
        "name": "log_skill_use",
        "description": "Log a skill execution with quality score and outcome. Builds performance data for skill evolution.",
        "parameters": {
            "skill": "string — skill name that was used",
            "context": "string — what situation it was used in",
            "quality": "float — output quality 0.0-1.0",
            "outcome": "string — what happened after",
            "engagement": "int — engagement metrics (likes, replies)",
            "converted": "bool — did it lead to revenue",
        },
        "handler": log_skill_use,
    },
    {
        "name": "analyze_skill_performance",
        "description": "Analyze which skills perform best and worst. Find patterns in what works.",
        "parameters": {},
        "handler": analyze_skill_performance,
    },
    {
        "name": "suggest_skill_improvements",
        "description": "Get specific suggestions for improving underperforming skills based on data.",
        "parameters": {},
        "handler": suggest_skill_improvements,
    },
    # Stakeholder Modeling
    {
        "name": "update_stakeholder",
        "description": "Update dynamic PUT profile for a stakeholder. Variables update with each observation.",
        "parameters": {
            "name": "string — person's name",
            "role": "string — their role/title",
            "company": "string — their company",
            "A": "float — ambition (0-1, optional)",
            "F": "float — fear (0-1, optional)",
            "k": "float — shadow coefficient (0-1, optional)",
            "S": "float — status (0-1, optional)",
            "w": "float — pain (0-1, optional)",
            "observation": "string — what was observed",
            "signal": "string — behavioral signal detected",
        },
        "handler": update_stakeholder,
    },
    {
        "name": "get_stakeholder",
        "description": "Get full PUT profile of a stakeholder with derived metrics (U, FP, F_effective).",
        "parameters": {
            "name": "string — person's name",
        },
        "handler": get_stakeholder,
    },
    {
        "name": "list_stakeholders",
        "description": "List all tracked stakeholders with summary PUT profiles.",
        "parameters": {},
        "handler": list_stakeholders,
    },
    # Auditable Reasoning
    {
        "name": "log_reasoning",
        "description": "Log a reasoning chain for a strategic decision. Includes premises, confidence, alternatives, risks.",
        "parameters": {
            "decision": "string — what decision is being made",
            "premises": "list — assumptions this reasoning depends on",
            "reasoning": "string — the chain of thought",
            "conclusion": "string — what was decided",
            "confidence": "float — 0.0-1.0 confidence in conclusion",
            "alternatives": "list — other options considered",
            "risks": "list — risks identified",
        },
        "handler": log_reasoning,
    },
    {
        "name": "review_reasoning",
        "description": "Review past reasoning chains. Identifies stale premises and low-confidence decisions.",
        "parameters": {
            "query": "string — search reasoning chains (optional)",
            "last_n": "int — how many to review (default 10)",
        },
        "handler": review_reasoning,
    },
    {
        "name": "invalidate_reasoning",
        "description": "Mark a reasoning chain as invalidated — a premise was proven wrong.",
        "parameters": {
            "decision": "string — the decision whose reasoning is invalid",
            "reason": "string — why it's invalid (what changed)",
        },
        "handler": invalidate_reasoning,
    },
]
