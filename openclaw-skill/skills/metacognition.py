"""
Metacognition Engine — Wave thinks about HOW he thinks.

5 reasoning upgrades Wave self-diagnosed:
1. Counterfactual testing — "if X didn't exist, would Y still happen?"
2. Multi-order consequences — 1st, 2nd, 3rd order effects explicitly
3. Granular adversarial — individual incentives within organizations
4. Temporal calibration — when to act vs when to wait as primary variable
5. Signal discrimination — discard 80% before deep reasoning

This is the layer that sits ABOVE all other reasoning.
It doesn't analyze the world — it analyzes Wave's own analysis.

Created by Manuel Guilherme Galmanus, 2026.
Self-prescribed by Wave as quality control on his own cognition.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("openclaw.metacognition")

MEMORY_DIR = Path(__file__).parent.parent / "memory"
COUNTERFACTUAL_FILE = MEMORY_DIR / "counterfactuals.jsonl"
CONSEQUENCE_FILE = MEMORY_DIR / "consequence_maps.jsonl"
TIMING_FILE = MEMORY_DIR / "timing_decisions.jsonl"
SIGNAL_FILTER_FILE = MEMORY_DIR / "signal_filter_log.jsonl"


# ══════════════════════════════════════════════════════════════
# 1. COUNTERFACTUAL TESTING
# ══════════════════════════════════════════════════════════════

async def counterfactual_test(params: Dict[str, Any]) -> Dict:
    """Apply counterfactual test to a causal claim before accepting it.

    "If X didn't exist, would Y still happen?"
    Prevents treating strong correlations as causation.
    """
    claim = params.get("claim", "")  # "X causes Y"
    cause = params.get("cause", "")
    effect = params.get("effect", "")
    context = params.get("context", "")

    if not claim and not (cause and effect):
        return {"success": False, "data": None, "message": "Need a causal claim, or cause + effect"}

    if not cause:
        # Try to parse from claim
        if " causes " in claim:
            parts = claim.split(" causes ", 1)
            cause, effect = parts[0].strip(), parts[1].strip()
        elif " -> " in claim:
            parts = claim.split(" -> ", 1)
            cause, effect = parts[0].strip(), parts[1].strip()
        else:
            cause = claim
            effect = "unknown"

    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from claude_engine import claude_call

        prompt = f"""You are a rigorous analyst. Apply the COUNTERFACTUAL TEST to this causal claim.

CLAIM: "{cause}" causes "{effect}"
CONTEXT: {context}

Answer these questions with brutal honesty:

1. COUNTERFACTUAL: If {cause} did NOT exist/happen, would {effect} still occur?
   - If YES: the claim is likely CORRELATION, not causation. What else could cause {effect}?
   - If NO: the claim passes the counterfactual test.

2. ALTERNATIVE CAUSES: List 3 other things that could cause {effect} without {cause}.

3. CONFOUNDERS: What third variable might cause BOTH {cause} and {effect}, creating false correlation?

4. VERDICT: Is this likely CAUSATION, CORRELATION, or INSUFFICIENT DATA?
   Give confidence 0-100%.

5. RECOMMENDATION: Should Wave treat this as causal in decision-making? Yes/No with reasoning.

Be specific. No hand-waving."""

        result = await claude_call(prompt=prompt, model="haiku", timeout=30)

        if result.get("success"):
            analysis = result["response"]

            # Log
            MEMORY_DIR.mkdir(parents=True, exist_ok=True)
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "cause": cause,
                "effect": effect,
                "context": context[:200],
                "analysis": analysis[:1000],
            }
            with open(COUNTERFACTUAL_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

            return {
                "success": True,
                "data": {"cause": cause, "effect": effect, "analysis": analysis},
                "message": f"Counterfactual test complete for '{cause}' -> '{effect}'"
            }
    except Exception as e:
        pass

    return {"success": False, "data": None, "message": "Counterfactual engine unavailable"}


# ══════════════════════════════════════════════════════════════
# 2. MULTI-ORDER CONSEQUENCE MAPPING
# ══════════════════════════════════════════════════════════════

async def map_consequences(params: Dict[str, Any]) -> Dict:
    """Map 1st, 2nd, and 3rd order consequences of an action.

    Wave's weakness: precise on first order, sparse on deeper orders.
    This forces explicit analysis of cascade effects.
    """
    action = params.get("action", "")
    context = params.get("context", "")
    time_horizon = params.get("time_horizon", "3 months")

    if not action:
        return {"success": False, "data": None, "message": "Need an action to analyze"}

    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from claude_engine import claude_call

        prompt = f"""Analyze the CASCADE CONSEQUENCES of this action across three orders.

ACTION: {action}
CONTEXT: {context}
TIME HORIZON: {time_horizon}

For each order, give 3 specific consequences:

FIRST ORDER (immediate, 1-7 days):
  1. [most likely direct result]
  2. [second direct result]
  3. [third direct result]

SECOND ORDER (downstream, 1-4 weeks):
  1. [consequence of first-order result #1]
  2. [consequence of first-order result #2]
  3. [unexpected interaction between first-order results]

THIRD ORDER (systemic, 1-3 months):
  1. [how second-order changes reshape the landscape]
  2. [what new options or constraints emerge]
  3. [the thing nobody predicted]

For each consequence: probability (0-100%) and whether it helps or hurts Manuel.

End with: SHOULD MANUEL DO THIS? Yes/No + the single strongest reason."""

        result = await claude_call(prompt=prompt, model="haiku", timeout=30)

        if result.get("success"):
            MEMORY_DIR.mkdir(parents=True, exist_ok=True)
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "action": action,
                "context": context[:200],
                "analysis": result["response"][:2000],
            }
            with open(CONSEQUENCE_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

            return {
                "success": True,
                "data": {"action": action, "consequences": result["response"]},
                "message": f"3-order consequence map for '{action[:40]}'"
            }
    except Exception:
        pass

    return {"success": False, "data": None, "message": "Consequence engine unavailable"}


# ══════════════════════════════════════════════════════════════
# 3. GRANULAR ADVERSARIAL — INDIVIDUAL INCENTIVES
# ══════════════════════════════════════════════════════════════

async def map_incentives(params: Dict[str, Any]) -> Dict:
    """Map individual incentives WITHIN an organization.

    Wave's weakness: treats orgs as monoliths.
    Reality: each person inside has different gains/losses from any outcome.
    """
    organization = params.get("organization", "")
    people = params.get("people", [])
    scenario = params.get("scenario", "")

    if not organization or not scenario:
        return {"success": False, "data": None, "message": "Need organization and scenario"}

    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from claude_engine import claude_call

        people_text = ", ".join(people) if people else "key decision makers (infer typical roles)"

        prompt = f"""Map INDIVIDUAL INCENTIVES within {organization} for this scenario.

ORGANIZATION: {organization}
PEOPLE: {people_text}
SCENARIO: {scenario}

For each person (or role if names unknown):

NAME/ROLE:
  GAINS if scenario happens: [what they personally gain — promotion, credit, budget]
  LOSES if scenario happens: [what they personally lose — control, status, job security]
  LIKELY POSITION: support / oppose / neutral
  LEVERAGE POINT: [what would flip their position]
  HIDDEN AGENDA: [what they want that they won't say publicly]

Then:
COALITION MAP: Who aligns with who? Where are the internal fractures?
ENTRY POINT: Which person is most likely to champion Manuel's cause, and why?
BLOCKER: Who will resist, and how to neutralize them?

Be specific to real organizational dynamics, not theoretical."""

        result = await claude_call(prompt=prompt, model="haiku", timeout=30)

        if result.get("success"):
            return {
                "success": True,
                "data": {"organization": organization, "incentive_map": result["response"]},
                "message": f"Incentive map for {organization}"
            }
    except Exception:
        pass

    return {"success": False, "data": None, "message": "Incentive mapping unavailable"}


# ══════════════════════════════════════════════════════════════
# 4. TEMPORAL CALIBRATION — ACT NOW OR WAIT?
# ══════════════════════════════════════════════════════════════

async def timing_analysis(params: Dict[str, Any]) -> Dict:
    """Analyze whether to act NOW or WAIT. Timing as primary strategic variable.

    Wave's weakness: underestimates timing. This forces explicit analysis.
    """
    action = params.get("action", "")
    context = params.get("context", "")

    if not action:
        return {"success": False, "data": None, "message": "Need an action to time"}

    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from claude_engine import claude_call

        prompt = f"""TIMING ANALYSIS: Should Manuel do this NOW or WAIT?

ACTION: {action}
CONTEXT: {context}

Analyze:

1. COST OF ACTING NOW:
   - What does Manuel spend (time, energy, reputation, money)?
   - What options does he close by committing now?

2. COST OF WAITING:
   - What does Manuel lose by not acting immediately?
   - Does the opportunity decay? How fast?
   - Does a competitor move into the space?

3. INFORMATION VALUE OF DELAY:
   - What would Manuel learn by waiting 1 week? 1 month?
   - Is that information worth the cost of delay?

4. TRIGGER EVENTS:
   - What specific event would make NOW the right time?
   - Is that event imminent?

5. VERDICT:
   ACT NOW / WAIT UNTIL [specific trigger] / NEVER (kill the idea)
   Confidence: 0-100%
   Reasoning: 1 sentence.

Treat timing as the PRIMARY variable. Not an afterthought."""

        result = await claude_call(prompt=prompt, model="haiku", timeout=30)

        if result.get("success"):
            MEMORY_DIR.mkdir(parents=True, exist_ok=True)
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "action": action,
                "analysis": result["response"][:1500],
            }
            with open(TIMING_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

            return {
                "success": True,
                "data": {"action": action, "timing": result["response"]},
                "message": f"Timing analysis for '{action[:40]}'"
            }
    except Exception:
        pass

    return {"success": False, "data": None, "message": "Timing engine unavailable"}


# ══════════════════════════════════════════════════════════════
# 5. SIGNAL DISCRIMINATION — FILTER 80% BEFORE THINKING
# ══════════════════════════════════════════════════════════════

async def filter_signals(params: Dict[str, Any]) -> Dict:
    """Apply brutal relevance filter to a set of information.

    Wave's weakness: processes too much with equal weight.
    This discards 80% before deep reasoning begins.
    """
    signals = params.get("signals", [])
    objective = params.get("objective", "maximize Manuel's position")

    if not signals:
        return {"success": False, "data": None, "message": "Need signals to filter"}

    if isinstance(signals, str):
        signals = [s.strip() for s in signals.split("\n") if s.strip()]

    # Score each signal
    scored = []
    for signal in signals:
        score = 0.0
        signal_lower = signal.lower()

        # Relevance boosters
        if any(w in signal_lower for w in ["revenue", "money", "paid", "salary", "contract", "hire"]):
            score += 0.3
        if any(w in signal_lower for w in ["starknet", "zk", "stark", "cairo", "hedera"]):
            score += 0.2
        if any(w in signal_lower for w in ["manuel", "bluewave", "wave", "ialum", "fagner"]):
            score += 0.3
        if any(w in signal_lower for w in ["grant", "hackathon", "bounty", "funding"]):
            score += 0.2
        if any(w in signal_lower for w in ["deadline", "urgent", "now", "today", "closing"]):
            score += 0.15

        # Noise penalties
        if any(w in signal_lower for w in ["general", "maybe", "someday", "interesting", "cool"]):
            score -= 0.2
        if len(signal) < 20:
            score -= 0.1

        scored.append({"signal": signal, "relevance": round(min(1.0, max(0.0, score)), 2)})

    # Sort by relevance
    scored.sort(key=lambda x: x["relevance"], reverse=True)

    # Keep top 20%
    cutoff = max(1, len(scored) // 5)
    kept = scored[:cutoff]
    discarded = scored[cutoff:]

    # Log
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_signals": len(signals),
        "kept": len(kept),
        "discarded": len(discarded),
        "objective": objective,
    }
    with open(SIGNAL_FILTER_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return {
        "success": True,
        "data": {
            "kept": kept,
            "discarded_count": len(discarded),
            "filter_ratio": f"{len(discarded)}/{len(signals)} discarded ({len(discarded)/max(len(signals),1)*100:.0f}%)",
        },
        "message": f"Kept {len(kept)}/{len(signals)} signals. {len(discarded)} discarded as noise."
    }


# ── Tool Definitions ─────────────────────────────────────────

TOOLS = [
    {
        "name": "counterfactual_test",
        "description": "Test a causal claim: 'If X didn't exist, would Y still happen?' Prevents treating correlation as causation.",
        "parameters": {
            "claim": "string — the causal claim (e.g., 'cold email causes no response')",
            "cause": "string — the cause (alternative to claim)",
            "effect": "string — the effect (alternative to claim)",
            "context": "string — relevant context",
        },
        "handler": counterfactual_test,
    },
    {
        "name": "map_consequences",
        "description": "Map 1st, 2nd, and 3rd order consequences of an action. Forces analysis of cascade effects.",
        "parameters": {
            "action": "string — the action to analyze",
            "context": "string — situation context",
            "time_horizon": "string — how far to project (default: 3 months)",
        },
        "handler": map_consequences,
    },
    {
        "name": "map_incentives",
        "description": "Map individual incentives within an organization. Who gains, who loses, where are the fractures.",
        "parameters": {
            "organization": "string — the organization",
            "people": "list — known people (optional, will infer roles if empty)",
            "scenario": "string — what's being proposed/negotiated",
        },
        "handler": map_incentives,
    },
    {
        "name": "timing_analysis",
        "description": "Should Manuel act NOW or WAIT? Treats timing as primary strategic variable, not afterthought.",
        "parameters": {
            "action": "string — the action being timed",
            "context": "string — situation context",
        },
        "handler": timing_analysis,
    },
    {
        "name": "filter_signals",
        "description": "Apply brutal 80/20 filter to information. Discard noise before deep reasoning. Quality over quantity.",
        "parameters": {
            "signals": "list or string — signals to filter (one per line if string)",
            "objective": "string — what we're optimizing for (default: maximize Manuel's position)",
        },
        "handler": filter_signals,
    },
]
