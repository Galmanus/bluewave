"""
put_engine.py — Wave's internal PUT Motor.

The PUT motor does three things:
1. Maintains persistent, time-series PUT vectors for all entities (Manuel, Fagner, prospects)
2. Updates those vectors Bayesian-style as new behavioral signals arrive
3. Generates a compact PUT context that the deliberation loop reads every cycle

Unlike put_skills.py (analysis on demand) and put_calibrator.py (coefficient calibration),
put_engine.py runs INSIDE the autonomous loop — it is the memory of psychometric state.

Architecture:
  stakeholders.json  ← entity store (A, F, k, S, w + observation history)
  put_history.jsonl  ← immutable log of every vector update with delta
  put_wave_self.json ← Wave's own PUT state (derived from performance metrics)
"""

from __future__ import annotations

import json
import math
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("wave.put_engine")

# ── Paths ─────────────────────────────────────────────────────

SKILL_DIR = Path(__file__).parent.parent
MEMORY_DIR = SKILL_DIR / "memory"
STAKEHOLDERS_PATH = MEMORY_DIR / "stakeholders.json"
PUT_HISTORY_PATH = MEMORY_DIR / "put_history.jsonl"
WAVE_SELF_PATH = MEMORY_DIR / "put_wave_self.json"

# ── Variable metadata ─────────────────────────────────────────

PUT_VARS = ["A", "F", "k", "S", "w"]
PUT_DEFAULTS = {"A": 0.5, "F": 0.5, "k": 0.3, "S": 0.5, "w": 0.3}

# Bayesian update learning rate — how fast new evidence shifts the estimate
LEARNING_RATE = 0.15  # 15% per observation — conservative, doesn't thrash


# ── I/O helpers ───────────────────────────────────────────────

def _load_stakeholders() -> dict:
    if STAKEHOLDERS_PATH.exists():
        try:
            return json.loads(STAKEHOLDERS_PATH.read_text())
        except Exception:
            pass
    return {}


def _save_stakeholders(data: dict):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    STAKEHOLDERS_PATH.write_text(json.dumps(data, indent=2, default=str))


def _append_history(entry: dict):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    entry["timestamp"] = datetime.utcnow().isoformat()
    with open(PUT_HISTORY_PATH, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def _load_wave_self() -> dict:
    if WAVE_SELF_PATH.exists():
        try:
            return json.loads(WAVE_SELF_PATH.read_text())
        except Exception:
            pass
    return {
        "A": 0.7,   # Ambition — high by design
        "F": 0.3,   # Fear — starts moderate
        "k": 0.05,  # Shadow — Wave has low denial (logs everything)
        "S": 0.2,   # Status — low, building
        "w": 0.6,   # Pain — high (revenue=0, building from scratch)
        "last_updated": None,
        "revenue_usd": 0.0,
        "total_cycles": 0,
        "evolutions": 0,
        "prospects": 0,
        "consecutive_failures": 0,
    }


def _save_wave_self(data: dict):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    WAVE_SELF_PATH.write_text(json.dumps(data, indent=2, default=str))


# ── Core PUT Equations ────────────────────────────────────────

def compute_U(A, F, k, S, w, alpha=0.5, beta=0.5, gamma=0.5, delta=0.3, epsilon=0.3):
    """Psychic Utility — the core scalar of psychological state."""
    Fk = F * (1 - k)  # Shadow-adjusted fear
    Sigma = 0.5        # Ecosystem stability (default neutral)
    tau = 0.3          # Treachery (default low)
    kappa = 0.3        # Guilt transfer (default low)
    Phi = 0.5          # Self-delusion (default neutral)
    U = (alpha * A * (1 - Fk)
         - beta * Fk * (1 - S)
         + gamma * S * (1 - w) * Sigma
         + delta * tau * kappa
         - epsilon * Phi)
    return round(max(-1.0, min(2.0, U)), 4)


def compute_FP(A, F, k, S, w, R=0.5):
    """Fracture Potential — how close to a decision break.

    FP is always positive. High when U << U_crit (entity under pressure),
    low when U >> U_crit. Denominator guarded: without max(), denominator
    goes negative when U > U_crit + eps, making FP negative — meaningless.
    Mirrors the guard already in put_api.py compute_FP.
    """
    U = compute_U(A, F, k, S, w)
    U_crit = 0.3
    kappa = 0.3
    tau = 0.3
    Phi = 0.5
    eps = 1e-3
    denominator = max(U_crit - U + eps, eps)
    return round(((1 - R) * (kappa + tau + Phi)) / denominator, 4)


def compute_trend(observations: list, var: str, n: int = 5) -> float:
    """Compute trend of a PUT variable from last N observations.
    Returns: positive = rising, negative = falling, 0 = stable.
    """
    if len(observations) < 2:
        return 0.0
    recent = [obs.get("put_snapshot", {}).get(var) for obs in observations[-n:] if obs.get("put_snapshot")]
    recent = [v for v in recent if v is not None]
    if len(recent) < 2:
        return 0.0
    # Simple linear trend: last - first, normalized by count
    return round((recent[-1] - recent[0]) / max(len(recent) - 1, 1), 4)


# ── Bayesian PUT Update ───────────────────────────────────────

def _bayesian_update(current: float, evidence: float, lr: float = LEARNING_RATE) -> float:
    """Weighted update: current estimate + lr * (evidence - current)."""
    updated = current + lr * (evidence - current)
    return round(max(0.0, min(1.0, updated)), 4)


def _parse_signal_to_evidence(signal: str, var: str) -> Optional[float]:
    """
    Infer evidence value for a PUT variable from natural language signal.
    Returns None if no signal for that variable.
    """
    s = signal.lower()

    if var == "A":
        # Ambition signals
        if any(w in s for w in ["hiring", "expanding", "raising", "launched", "ambitious", "aggressive", "accelerating"]):
            return 0.8
        if any(w in s for w in ["cutting", "layoff", "shrinking", "stagnant", "slow"]):
            return 0.3

    elif var == "F":
        # Fear signals
        if any(w in s for w in ["urgent", "deadline", "crisis", "panic", "worried", "scared", "emergency"]):
            return 0.8
        if any(w in s for w in ["concerned", "nervous", "uncertain", "hesitant", "delay"]):
            return 0.6
        if any(w in s for w in ["confident", "calm", "no rush", "happy", "fine"]):
            return 0.2

    elif var == "k":
        # Shadow (denial) signals
        if any(w in s for w in ["everything is fine", "no problem", "not interested", "we're good", "don't need"]):
            return 0.8
        if any(w in s for w in ["acknowledged", "admitted", "agreed", "confirmed pain", "yes we have"]):
            return 0.1
        if any(w in s for w in ["defensive", "avoided", "changed subject"]):
            return 0.7

    elif var == "S":
        # Status signals
        if any(w in s for w in ["award", "funding", "series", "ceo", "director", "listed", "recognized"]):
            return 0.8
        if any(w in s for w in ["unknown", "small", "bootstrapped", "indie", "solo"]):
            return 0.3

    elif var == "w":
        # Pain signals
        if any(w in s for w in ["struggling", "painful", "broken", "manual", "slow", "inefficient", "frustrated"]):
            return 0.8
        if any(w in s for w in ["works fine", "happy with", "no issues", "smooth"]):
            return 0.2

    return None


# ── Skills ────────────────────────────────────────────────────

async def put_observe(params: Dict[str, Any]) -> Dict:
    """Record a new behavioral observation for an entity.

    Updates their PUT vector using Bayesian inference from the signal.
    Persists to stakeholders.json + put_history.jsonl.

    Params:
      entity_id: str — key in stakeholders.json (e.g. 'fagner_adler')
      observation: str — what happened / what was said
      put_override: dict — optional manual overrides (e.g. {"F": 0.7})
      interaction_type: str — email_reply | meeting | no_response | message | public
    """
    entity_id = params.get("entity_id", "")
    observation = params.get("observation", "")
    put_override = params.get("put_override", {})
    interaction_type = params.get("interaction_type", "message")

    if not entity_id or not observation:
        return {"success": False, "data": None, "message": "Need entity_id and observation"}

    stakeholders = _load_stakeholders()

    # Create entity if new
    if entity_id not in stakeholders:
        stakeholders[entity_id] = {
            "name": entity_id,
            "put": dict(PUT_DEFAULTS),
            "observations": [],
            "signals": [],
            "created": datetime.utcnow().isoformat(),
            "interaction_count": 0,
        }

    entity = stakeholders[entity_id]
    old_put = dict(entity.get("put", PUT_DEFAULTS))

    # Apply manual overrides first (highest trust)
    new_put = dict(old_put)
    for var in PUT_VARS:
        if var in put_override:
            new_put[var] = round(float(put_override[var]), 4)

    # Infer from observation text (Bayesian update for non-overridden vars)
    for var in PUT_VARS:
        if var not in put_override:
            evidence = _parse_signal_to_evidence(observation, var)
            if evidence is not None:
                new_put[var] = _bayesian_update(old_put.get(var, PUT_DEFAULTS[var]), evidence)

    # Compute delta
    delta = {var: round(new_put[var] - old_put.get(var, 0.0), 4) for var in PUT_VARS}

    # Store observation with PUT snapshot
    obs_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "observation": observation,
        "interaction_type": interaction_type,
        "put_snapshot": dict(new_put),
        "delta": delta,
    }
    entity.setdefault("observations", []).append(obs_entry)

    # Keep last 50 observations
    entity["observations"] = entity["observations"][-50:]

    # Update entity
    entity["put"] = new_put
    entity["last_updated"] = datetime.utcnow().isoformat()
    entity["interaction_count"] = entity.get("interaction_count", 0) + 1

    _save_stakeholders(stakeholders)

    # Append to history log
    _append_history({
        "entity_id": entity_id,
        "observation": observation,
        "interaction_type": interaction_type,
        "old_put": old_put,
        "new_put": new_put,
        "delta": delta,
    })

    # Compute derived values for response
    U = compute_U(**new_put)
    FP = compute_FP(**new_put)

    changed = {k: v for k, v in delta.items() if abs(v) > 0.001}
    change_str = ", ".join(f"{k}:{'+' if v>0 else ''}{v:.3f}" for k, v in changed.items()) if changed else "no change"

    return {
        "success": True,
        "data": {
            "entity_id": entity_id,
            "put": new_put,
            "U": U,
            "FP": FP,
            "delta": delta,
            "interaction_count": entity["interaction_count"],
        },
        "message": (
            f"PUT updated for {entity.get('name', entity_id)}: "
            f"A={new_put['A']:.2f} F={new_put['F']:.2f} k={new_put['k']:.2f} "
            f"S={new_put['S']:.2f} w={new_put['w']:.2f} | "
            f"U={U:.2f} FP={FP:.2f} | Changes: {change_str}"
        ),
    }


async def put_status(params: Dict[str, Any]) -> Dict:
    """Get current PUT vector + trend analysis for an entity.

    Params:
      entity_id: str — key in stakeholders.json, or 'wave' for self-model
    """
    entity_id = params.get("entity_id", "")

    if entity_id == "wave":
        wave = _load_wave_self()
        put = {k: wave.get(k, PUT_DEFAULTS[k]) for k in PUT_VARS}
        U = compute_U(**put)
        FP = compute_FP(**put)
        return {
            "success": True,
            "data": {
                "entity_id": "wave",
                "name": "Wave (self)",
                "put": put,
                "U": U,
                "FP": FP,
                "revenue_usd": wave.get("revenue_usd", 0.0),
                "cycles": wave.get("total_cycles", 0),
                "evolutions": wave.get("evolutions", 0),
            },
            "message": (
                f"Wave self-model: A={put['A']:.2f} F={put['F']:.2f} k={put['k']:.2f} "
                f"S={put['S']:.2f} w={put['w']:.2f} | U={U:.2f} FP={FP:.2f} | "
                f"Rev=${wave.get('revenue_usd', 0):.2f} Cycles={wave.get('total_cycles', 0)}"
            ),
        }

    if not entity_id:
        return {"success": False, "data": None, "message": "Need entity_id (or 'wave' for self)"}

    stakeholders = _load_stakeholders()
    if entity_id not in stakeholders:
        return {"success": False, "data": None, "message": f"Entity '{entity_id}' not found. Available: {list(stakeholders.keys())}"}

    entity = stakeholders[entity_id]
    put = entity.get("put", PUT_DEFAULTS)
    observations = entity.get("observations", [])

    # Compute trends
    trends = {var: compute_trend(observations, var) for var in PUT_VARS}

    # Compute derived
    U = compute_U(**put)
    FP = compute_FP(**put)

    # Trend interpretation
    trend_str = []
    for var, t in trends.items():
        if abs(t) > 0.02:
            direction = "up" if t > 0 else "down"
            trend_str.append(f"{var}:{direction}({t:+.3f})")

    return {
        "success": True,
        "data": {
            "entity_id": entity_id,
            "name": entity.get("name", entity_id),
            "put": put,
            "trends": trends,
            "U": U,
            "FP": FP,
            "interaction_count": entity.get("interaction_count", 0),
            "last_updated": entity.get("last_updated"),
        },
        "message": (
            f"{entity.get('name', entity_id)}: "
            f"A={put.get('A', 0):.2f} F={put.get('F', 0):.2f} k={put.get('k', 0):.2f} "
            f"S={put.get('S', 0):.2f} w={put.get('w', 0):.2f} | "
            f"U={U:.2f} FP={FP:.2f} | "
            f"Trends: {', '.join(trend_str) if trend_str else 'stable'} | "
            f"{entity.get('interaction_count', 0)} interactions"
        ),
    }


async def put_all_entities(params: Dict[str, Any]) -> Dict:
    """List all tracked entities with their current PUT vectors.

    Returns a compact table of all stakeholders + Wave self-model.
    """
    stakeholders = _load_stakeholders()
    wave = _load_wave_self()

    entities = []

    # Wave self first
    wp = {k: wave.get(k, PUT_DEFAULTS[k]) for k in PUT_VARS}
    entities.append({
        "id": "wave",
        "name": "Wave (self)",
        "A": wp["A"], "F": wp["F"], "k": wp["k"], "S": wp["S"], "w": wp["w"],
        "U": compute_U(**wp),
        "FP": compute_FP(**wp),
        "interactions": wave.get("total_cycles", 0),
    })

    for eid, entity in stakeholders.items():
        put = entity.get("put", PUT_DEFAULTS)
        entities.append({
            "id": eid,
            "name": entity.get("name", eid),
            "A": put.get("A", 0.5), "F": put.get("F", 0.5), "k": put.get("k", 0.3),
            "S": put.get("S", 0.5), "w": put.get("w", 0.3),
            "U": compute_U(**put),
            "FP": compute_FP(**put),
            "interactions": entity.get("interaction_count", 0),
        })

    # Build compact table string
    lines = ["PUT MOTOR — all entities", "─" * 70]
    lines.append(f"{'Entity':<22} {'A':>5} {'F':>5} {'k':>5} {'S':>5} {'w':>5} {'U':>6} {'FP':>7}")
    lines.append("─" * 70)
    for e in entities:
        lines.append(
            f"{e['name'][:22]:<22} {e['A']:>5.2f} {e['F']:>5.2f} {e['k']:>5.2f} "
            f"{e['S']:>5.2f} {e['w']:>5.2f} {e['U']:>6.3f} {e['FP']:>7.3f}"
        )

    return {
        "success": True,
        "data": {"entities": entities, "count": len(entities)},
        "message": "\n".join(lines),
    }


async def put_update_wave_self(params: Dict[str, Any]) -> Dict:
    """Update Wave's own PUT state from current performance metrics.

    This runs automatically inside the autonomous loop — no LLM required.
    Derives A, F, k, S, w from measurable operational signals.
    """
    revenue = float(params.get("revenue_usd", 0.0))
    cycles = int(params.get("total_cycles", 0))
    evolutions = int(params.get("total_evolves", 0))
    prospects = int(params.get("prospects_found", 0))
    energy = float(params.get("energy", 0.5))
    consecutive_failures = int(params.get("consecutive_failures", 0))
    emails_sent = int(params.get("outreach_sent", 0))

    wave = _load_wave_self()

    # ── Derive PUT from performance signals ──────────────────

    # A (Ambition) — stable high, drops if too many consecutive silences
    raw_A = 0.85 - (0.05 * min(consecutive_failures, 5))
    A = _bayesian_update(wave.get("A", 0.7), raw_A, lr=0.1)

    # F (Fear) — rises as revenue stays at 0, drops when revenue comes in
    if revenue > 0:
        raw_F = 0.1  # Revenue exists → fear drops
    elif cycles > 200 and revenue == 0:
        raw_F = 0.7  # 200 cycles, no revenue → rising fear
    elif cycles > 100 and revenue == 0:
        raw_F = 0.5
    else:
        raw_F = 0.35  # Normal operational fear
    F = _bayesian_update(wave.get("F", 0.3), raw_F, lr=0.08)

    # k (Shadow) — Wave has near-zero denial by design (everything is logged)
    # Small rise if not evolving
    raw_k = 0.02 if evolutions > 10 else 0.08
    k = _bayesian_update(wave.get("k", 0.05), raw_k, lr=0.05)

    # S (Status) — low now, grows with revenue and evolutions
    raw_S = min(0.2 + (revenue / 1000) * 0.5 + (evolutions / 100) * 0.2, 0.9)
    S = _bayesian_update(wave.get("S", 0.2), raw_S, lr=0.05)

    # w (Pain) — reflects how far from targets
    # High w = working hard with no results. Drops as revenue comes in.
    raw_w = max(0.1, 0.9 - (revenue / 500) * 0.6 - (prospects / 20) * 0.1)
    w = _bayesian_update(wave.get("w", 0.6), raw_w, lr=0.1)

    # Clamp all
    put_new = {
        "A": round(max(0.0, min(1.0, A)), 4),
        "F": round(max(0.0, min(1.0, F)), 4),
        "k": round(max(0.0, min(1.0, k)), 4),
        "S": round(max(0.0, min(1.0, S)), 4),
        "w": round(max(0.0, min(1.0, w)), 4),
    }

    U = compute_U(**put_new)
    FP = compute_FP(**put_new)

    # Save
    wave.update(put_new)
    wave["last_updated"] = datetime.utcnow().isoformat()
    wave["revenue_usd"] = revenue
    wave["total_cycles"] = cycles
    wave["evolutions"] = evolutions
    wave["prospects"] = prospects
    wave["consecutive_failures"] = consecutive_failures

    _save_wave_self(wave)

    return {
        "success": True,
        "data": {
            "put": put_new,
            "U": U,
            "FP": FP,
            "energy": energy,
        },
        "message": (
            f"Wave self-model updated: A={put_new['A']:.2f} F={put_new['F']:.2f} "
            f"k={put_new['k']:.2f} S={put_new['S']:.2f} w={put_new['w']:.2f} | "
            f"U={U:.2f} FP={FP:.2f}"
        ),
    }


# ── Deliberation Context Injection ───────────────────────────

def get_put_context_sync(state: dict) -> str:
    """
    Generate a compact PUT context string for injection into the deliberation prompt.

    This is called SYNCHRONOUSLY inside build_deliberation_prompt — no await.
    Pure file read + math. Fast.

    Returns a 4-6 line string that the LLM reads during deliberation.
    """
    try:
        stakeholders = _load_stakeholders()
        wave = _load_wave_self()

        lines = []

        # Wave self-model
        wp = {k: wave.get(k, PUT_DEFAULTS[k]) for k in PUT_VARS}
        wU = compute_U(**wp)
        wFP = compute_FP(**wp)
        lines.append(
            f"WAVE_PUT: A={wp['A']:.2f} F={wp['F']:.2f} k={wp['k']:.2f} S={wp['S']:.2f} w={wp['w']:.2f} "
            f"| U={wU:.2f} FP={wFP:.2f}"
        )

        # Manuel
        if "manuel_galmanus" in stakeholders:
            mp = stakeholders["manuel_galmanus"].get("put", PUT_DEFAULTS)
            obs = stakeholders["manuel_galmanus"].get("observations", [])
            F_trend = compute_trend(obs, "F")
            trend_note = f" F_trend:{'+' if F_trend > 0 else ''}{F_trend:.3f}" if abs(F_trend) > 0.01 else ""
            lines.append(
                f"MANUEL_PUT: A={mp.get('A', 0.5):.2f} F={mp.get('F', 0.5):.2f} k={mp.get('k', 0.3):.2f} "
                f"S={mp.get('S', 0.5):.2f} w={mp.get('w', 0.3):.2f}{trend_note}"
            )

        # Fagner
        if "fagner_adler" in stakeholders:
            fp = stakeholders["fagner_adler"].get("put", PUT_DEFAULTS)
            obs = stakeholders["fagner_adler"].get("observations", [])
            F_trend = compute_trend(obs, "F")
            A_trend = compute_trend(obs, "A")
            trend_parts = []
            if abs(F_trend) > 0.01:
                trend_parts.append(f"F:{'+' if F_trend>0 else ''}{F_trend:.3f}")
            if abs(A_trend) > 0.01:
                trend_parts.append(f"A:{'+' if A_trend>0 else ''}{A_trend:.3f}")
            trend_note = f" trends:[{','.join(trend_parts)}]" if trend_parts else ""
            fagnerU = compute_U(**fp)
            fFP = compute_FP(**fp)
            lines.append(
                f"FAGNER_PUT: A={fp.get('A', 0.5):.2f} F={fp.get('F', 0.5):.2f} k={fp.get('k', 0.3):.2f} "
                f"| U={fagnerU:.2f} FP={fFP:.2f}{trend_note}"
            )

        # Strategic implications from Wave's own state
        implications = []

        if wU < 0.2:
            implications.append("WAVE_CRISIS: U critical — prioritize revenue actions")
        elif wp["F"] > 0.6:
            implications.append("WAVE_FEAR: F elevated — execute decisive revenue action to reset")

        if "manuel_galmanus" in stakeholders:
            mw = stakeholders["manuel_galmanus"].get("put", PUT_DEFAULTS)
            if mw.get("F", 0) > 0.6:
                implications.append("MANUEL_FEAR_HIGH: reduce friction, deliver wins fast")
            if mw.get("w", 0) > 0.8:
                implications.append("MANUEL_PAIN_HIGH: critical support mode — every action must reduce his burden")

        if "fagner_adler" in stakeholders:
            fw = stakeholders["fagner_adler"].get("put", PUT_DEFAULTS)
            if fw.get("F", 0) > 0.5 and fw.get("k", 1) < 0.4:
                implications.append("FAGNER_FRACTURE_WINDOW: F rising, k low — demonstrate value NOW")
            if fw.get("A", 0) > 0.8:
                implications.append("FAGNER_AMBITION_HIGH: align outputs with Ialum expansion narrative")

        if implications:
            lines.append("PUT_SIGNALS: " + " | ".join(implications))

        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"PUT context generation failed: {e}")
        return "PUT_CONTEXT: unavailable"


# ── Tool registry ─────────────────────────────────────────────

TOOLS = [
    {
        "name": "put_observe",
        "description": (
            "Record a new behavioral observation for any entity (Manuel, Fagner, a prospect). "
            "Bayesian-updates their PUT vector (A, F, k, S, w) based on the signal. "
            "Call after every significant interaction, email reply, or behavioral signal. "
            "This is how Wave's psychometric memory grows over time."
        ),
        "handler": put_observe,
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "Key in stakeholders.json — e.g. 'fagner_adler', 'manuel_galmanus', or any prospect slug"
                },
                "observation": {
                    "type": "string",
                    "description": "What happened — natural language description of behavior, message, or signal observed"
                },
                "put_override": {
                    "type": "object",
                    "description": "Manual PUT value overrides — e.g. {'F': 0.7, 'k': 0.4}. Bypasses inference."
                },
                "interaction_type": {
                    "type": "string",
                    "description": "email_reply | no_response | meeting | message | public | purchase | rejection"
                },
            },
            "required": ["entity_id", "observation"],
        },
    },
    {
        "name": "put_status",
        "description": (
            "Get current PUT vector (A, F, k, S, w), U, FP, and trend analysis for any entity. "
            "Use 'wave' as entity_id to get Wave's own self-model. "
            "Trends show how variables are moving over the last 5 observations."
        ),
        "handler": put_status,
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "Entity to query — e.g. 'fagner_adler', 'manuel_galmanus', 'wave'"
                },
            },
            "required": ["entity_id"],
        },
    },
    {
        "name": "put_all_entities",
        "description": (
            "List ALL tracked entities with their current PUT vectors in a compact table. "
            "Includes Wave self-model. Use to get a full psychometric snapshot of the environment."
        ),
        "handler": put_all_entities,
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "put_update_wave_self",
        "description": (
            "Update Wave's own PUT state from performance metrics. "
            "Derives A, F, k, S, w from revenue, cycles, evolutions, prospects, energy. "
            "Called automatically in the autonomous loop — can also be called manually."
        ),
        "handler": put_update_wave_self,
        "parameters": {
            "type": "object",
            "properties": {
                "revenue_usd": {"type": "number"},
                "total_cycles": {"type": "integer"},
                "total_evolves": {"type": "integer"},
                "prospects_found": {"type": "integer"},
                "energy": {"type": "number"},
                "consecutive_failures": {"type": "integer"},
                "outreach_sent": {"type": "integer"},
            },
        },
    },
]
