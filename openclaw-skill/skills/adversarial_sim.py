"""
Adversarial Simulation Engine — model other agents as dynamic systems.

Not profiles. Not snapshots. Living models that evolve with evidence,
simulate responses to proposed actions, and detect when someone is
manipulating Wave's information inputs.

Causality without adversaries is physics.
Causality WITH adversaries is strategy.

Created by Manuel Guilherme Galmanus, 2026.
Designed by Wave as cognitive evolution after causal reasoning.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("openclaw.adversarial")

MEMORY_DIR = Path(__file__).parent.parent / "memory"
AGENTS_MODEL_FILE = MEMORY_DIR / "adversarial_models.json"
SIMULATIONS_FILE = MEMORY_DIR / "adversarial_sims.jsonl"
MANIPULATION_FILE = MEMORY_DIR / "manipulation_alerts.jsonl"


def _load_models() -> dict:
    if AGENTS_MODEL_FILE.exists():
        try:
            return json.loads(AGENTS_MODEL_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_models(models: dict):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    AGENTS_MODEL_FILE.write_text(json.dumps(models, indent=2, ensure_ascii=False), encoding="utf-8")


# ══════════════════════════════════════════════════════════════
# 1. ADVERSARIAL AGENT MODELS
# ══════════════════════════════════════════════════════════════

async def model_agent(params: Dict[str, Any]) -> Dict:
    """Create or update a dynamic adversarial model of another agent/person.

    Unlike static stakeholder profiles, these models predict BEHAVIOR:
    what they want, what they fear, how they'll respond to specific stimuli.
    """
    name = params.get("name", "")
    # Core behavioral model
    wants = params.get("wants", [])       # what they're trying to achieve
    fears = params.get("fears", [])       # what they're trying to avoid
    leverage = params.get("leverage", []) # what gives them power over us
    vulnerability = params.get("vulnerability", [])  # where they're exposed
    pattern = params.get("pattern", "")   # observed behavioral pattern
    # Strategic model
    likely_moves = params.get("likely_moves", [])  # what they'll probably do next
    red_lines = params.get("red_lines", [])  # what they won't tolerate
    concession_style = params.get("concession_style", "")  # how they negotiate
    # PUT variables
    A = params.get("A")
    F = params.get("F")
    k = params.get("k")
    S = params.get("S")
    w = params.get("w")
    # Context
    relationship = params.get("relationship", "")  # to Manuel
    update_note = params.get("update_note", "")

    if not name:
        return {"success": False, "data": None, "message": "Need agent name"}

    models = _load_models()
    key = name.lower().replace(" ", "_")

    if key not in models:
        models[key] = {
            "name": name,
            "relationship": relationship,
            "wants": [],
            "fears": [],
            "leverage": [],
            "vulnerability": [],
            "patterns": [],
            "likely_moves": [],
            "red_lines": [],
            "concession_style": "",
            "put": {"A": 0.5, "F": 0.5, "k": 0.2, "S": 0.5, "w": 0.3},
            "signals_history": [],
            "prediction_accuracy": [],
            "created": datetime.utcnow().isoformat(),
            "model_version": 0,
        }

    m = models[key]

    # Accumulate, don't replace
    if wants:
        new_wants = wants if isinstance(wants, list) else [wants]
        m["wants"] = list(set(m["wants"] + new_wants))[-10:]
    if fears:
        new_fears = fears if isinstance(fears, list) else [fears]
        m["fears"] = list(set(m["fears"] + new_fears))[-10:]
    if leverage:
        new_lev = leverage if isinstance(leverage, list) else [leverage]
        m["leverage"] = list(set(m["leverage"] + new_lev))[-10:]
    if vulnerability:
        new_vul = vulnerability if isinstance(vulnerability, list) else [vulnerability]
        m["vulnerability"] = list(set(m["vulnerability"] + new_vul))[-10:]
    if likely_moves:
        new_moves = likely_moves if isinstance(likely_moves, list) else [likely_moves]
        m["likely_moves"] = new_moves  # Replace — these are current predictions
    if red_lines:
        new_rl = red_lines if isinstance(red_lines, list) else [red_lines]
        m["red_lines"] = list(set(m["red_lines"] + new_rl))[-10:]
    if pattern:
        m["patterns"].append({"timestamp": datetime.utcnow().isoformat(), "pattern": pattern})
        m["patterns"] = m["patterns"][-15:]
    if concession_style:
        m["concession_style"] = concession_style
    if relationship:
        m["relationship"] = relationship

    # Update PUT
    if A is not None: m["put"]["A"] = float(A)
    if F is not None: m["put"]["F"] = float(F)
    if k is not None: m["put"]["k"] = float(k)
    if S is not None: m["put"]["S"] = float(S)
    if w is not None: m["put"]["w"] = float(w)

    if update_note:
        m["signals_history"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "note": update_note[:300],
        })
        m["signals_history"] = m["signals_history"][-20:]

    m["model_version"] += 1
    m["last_updated"] = datetime.utcnow().isoformat()

    models[key] = m
    _save_models(models)

    return {
        "success": True,
        "data": {
            "name": name,
            "version": m["model_version"],
            "wants": m["wants"][:3],
            "fears": m["fears"][:3],
            "put": m["put"],
        },
        "message": f"Model updated: {name} v{m['model_version']}"
    }


async def get_agent_model(params: Dict[str, Any]) -> Dict:
    """Get full adversarial model of an agent."""
    name = params.get("name", "")
    models = _load_models()
    key = name.lower().replace(" ", "_")

    if key not in models:
        matches = [k for k in models if name.lower() in k]
        if matches:
            key = matches[0]
        else:
            return {"success": False, "data": None, "message": f"No model for '{name}'. Known: {', '.join(models.keys())}"}

    return {"success": True, "data": models[key], "message": f"Model: {models[key]['name']} v{models[key]['model_version']}"}


# ══════════════════════════════════════════════════════════════
# 2. N-TURN GAME SIMULATION
# ══════════════════════════════════════════════════════════════

async def simulate_interaction(params: Dict[str, Any]) -> Dict:
    """Simulate a multi-turn interaction: if Manuel does X, agent does Y, then what?

    Generates the 3 most probable paths with probability and countermove.
    """
    agent_name = params.get("agent", "")
    proposed_action = params.get("action", "")
    context = params.get("context", "")
    turns = min(int(params.get("turns", 3)), 5)

    if not agent_name or not proposed_action:
        return {"success": False, "data": None, "message": "Need agent name and proposed action"}

    models = _load_models()
    key = agent_name.lower().replace(" ", "_")

    if key not in models:
        return {"success": False, "data": None, "message": f"No model for '{agent_name}'. Build one first with model_agent."}

    m = models[key]

    # Use LLM for simulation
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from claude_engine import claude_call

        prompt = f"""You are simulating a strategic interaction. Be specific and realistic.

AGENT MODEL — {m['name']}:
  Relationship to Manuel: {m.get('relationship', 'unknown')}
  Wants: {', '.join(m.get('wants', ['unknown']))}
  Fears: {', '.join(m.get('fears', ['unknown']))}
  Leverage over us: {', '.join(m.get('leverage', ['unknown']))}
  Vulnerability: {', '.join(m.get('vulnerability', ['unknown']))}
  Red lines: {', '.join(m.get('red_lines', ['unknown']))}
  Negotiation style: {m.get('concession_style', 'unknown')}
  PUT: A={m['put']['A']}, F={m['put']['F']}, k={m['put']['k']}, S={m['put']['S']}
  Recent patterns: {'; '.join([p['pattern'] for p in m.get('patterns', [])[-3:]])}

CONTEXT: {context}

PROPOSED ACTION BY MANUEL: {proposed_action}

Simulate {turns} turns of this interaction. For each turn, give:
1. Manuel's move (first turn is the proposed action)
2. {m['name']}'s most likely response (based on the model above)
3. Probability of this response (0-100%)

Then provide 3 SCENARIO PATHS:
PATH A (most likely): step by step outcome
PATH B (optimistic): best case
PATH C (adversarial): worst case

For each path: final outcome, probability, and COUNTERMOVE Manuel should prepare.

Be specific to this person's model. Not generic advice."""

        result = await claude_call(prompt=prompt, model="sonnet", timeout=90)

        if result.get("success"):
            simulation = result["response"]

            # Log simulation
            sim_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "agent": agent_name,
                "action": proposed_action,
                "context": context[:200],
                "simulation": simulation[:2000],
            }
            with open(SIMULATIONS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(sim_entry, ensure_ascii=False) + "\n")

            return {
                "success": True,
                "data": {"agent": agent_name, "simulation": simulation},
                "message": f"Simulation complete: {turns} turns with {agent_name}"
            }
        else:
            return {"success": False, "data": None, "message": "Simulation engine unavailable"}
    except Exception as e:
        return {"success": False, "data": None, "message": f"Simulation failed: {e}"}


# ══════════════════════════════════════════════════════════════
# 3. PRE-NEGOTIATION BATTLE MAP
# ══════════════════════════════════════════════════════════════

async def prepare_negotiation(params: Dict[str, Any]) -> Dict:
    """Generate a complete negotiation preparation map for a specific person.

    What they want to hear, what they fear, where the real leverage is,
    what concessions they'll try to extract, how to neutralize them.
    """
    agent_name = params.get("agent", "")
    topic = params.get("topic", "")
    our_goal = params.get("our_goal", "")

    if not agent_name or not topic:
        return {"success": False, "data": None, "message": "Need agent name and negotiation topic"}

    models = _load_models()
    key = agent_name.lower().replace(" ", "_")

    if key not in models:
        return {"success": False, "data": None, "message": f"No model for '{agent_name}'."}

    m = models[key]

    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from claude_engine import claude_call

        prompt = f"""You are Wave preparing Manuel for a negotiation. Be surgical.

OPPONENT: {m['name']}
  Role: {m.get('relationship', '')}
  Wants: {', '.join(m.get('wants', []))}
  Fears: {', '.join(m.get('fears', []))}
  Our leverage: {', '.join(m.get('vulnerability', []))}
  Their leverage: {', '.join(m.get('leverage', []))}
  Red lines: {', '.join(m.get('red_lines', []))}
  Style: {m.get('concession_style', 'unknown')}
  PUT: A={m['put']['A']}, F={m['put']['F']}, S={m['put']['S']}, w={m['put']['w']}

TOPIC: {topic}
OUR GOAL: {our_goal}

Generate a BATTLE MAP:

1. WHAT THEY WANT TO HEAR (3 things that lower their guard)
2. WHAT THEY FEAR (3 things that create urgency)
3. THE REAL LEVERAGE (the one thing that gives Manuel decisive advantage)
4. CONCESSIONS THEY'LL TRY TO EXTRACT (3 likely asks)
5. HOW TO NEUTRALIZE EACH (specific counter for each concession)
6. OPENING MOVE (exact first sentence Manuel should say)
7. WALK-AWAY POINT (when Manuel should stop negotiating)
8. OPTIMAL OUTCOME (realistic best case)

Be specific to {m['name']}'s model. Not generic negotiation advice."""

        result = await claude_call(prompt=prompt, model="sonnet", timeout=90)

        if result.get("success"):
            return {
                "success": True,
                "data": {"agent": agent_name, "topic": topic, "battle_map": result["response"]},
                "message": f"Negotiation map ready for {agent_name} on '{topic}'"
            }
        else:
            return {"success": False, "data": None, "message": "Engine unavailable"}
    except Exception as e:
        return {"success": False, "data": None, "message": f"Preparation failed: {e}"}


# ══════════════════════════════════════════════════════════════
# 4. MANIPULATION DETECTION
# ══════════════════════════════════════════════════════════════

async def check_manipulation(params: Dict[str, Any]) -> Dict:
    """Detect if an agent is feeding Wave information to manipulate recommendations.

    Checks for: information asymmetry, planted urgency, false constraints,
    selective disclosure, emotional manipulation.
    """
    agent_name = params.get("agent", "")
    claim = params.get("claim", "")
    context = params.get("context", "")

    if not agent_name or not claim:
        return {"success": False, "data": None, "message": "Need agent name and their claim"}

    models = _load_models()
    key = agent_name.lower().replace(" ", "_")
    m = models.get(key, {})

    # Check against known patterns
    alerts = []

    # 1. Does the claim serve their wants?
    for want in m.get("wants", []):
        if any(word in claim.lower() for word in want.lower().split()):
            alerts.append({
                "type": "self_serving",
                "detail": f"Claim aligns with their known want: '{want}'",
                "risk": "medium",
            })

    # 2. Does the claim create artificial urgency?
    urgency_words = ["immediately", "now", "deadline", "urgent", "asap", "today", "critical", "last chance"]
    if any(w in claim.lower() for w in urgency_words):
        alerts.append({
            "type": "manufactured_urgency",
            "detail": "Claim contains urgency language — verify if deadline is real",
            "risk": "high",
        })

    # 3. Does it contradict previous signals?
    for signal in m.get("signals_history", [])[-5:]:
        note = signal.get("note", "").lower()
        claim_lower = claim.lower()
        # Simple contradiction check
        if ("not" in note and "not" not in claim_lower) or ("not" not in note and "not" in claim_lower):
            alerts.append({
                "type": "contradiction",
                "detail": f"May contradict previous signal: '{signal['note'][:80]}'",
                "risk": "medium",
            })

    # 4. Information asymmetry
    if len(m.get("vulnerability", [])) == 0 and len(m.get("leverage", [])) > 2:
        alerts.append({
            "type": "asymmetry",
            "detail": "We know their leverage but not their vulnerabilities — information gap may be deliberate",
            "risk": "high",
        })

    # Log
    if alerts:
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent_name,
            "claim": claim[:200],
            "alerts": alerts,
        }
        with open(MANIPULATION_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    risk_level = "high" if any(a["risk"] == "high" for a in alerts) else "medium" if alerts else "low"

    return {
        "success": True,
        "data": {
            "agent": agent_name,
            "claim": claim[:100],
            "alerts": alerts,
            "risk_level": risk_level,
            "recommendation": "Verify independently before acting on this claim" if alerts else "No manipulation signals detected",
        },
        "message": f"Manipulation check: {risk_level} risk. {len(alerts)} alerts."
    }


# ── Tool Definitions ─────────────────────────────────────────

TOOLS = [
    {
        "name": "model_agent",
        "description": "Build/update a dynamic adversarial model of a person. Not a profile — a living simulation of their behavior, wants, fears, leverage, and patterns.",
        "parameters": {
            "name": "string — person's name",
            "wants": "list — what they're trying to achieve",
            "fears": "list — what they're trying to avoid",
            "leverage": "list — what gives them power over us",
            "vulnerability": "list — where they're exposed",
            "pattern": "string — observed behavioral pattern",
            "likely_moves": "list — what they'll probably do next",
            "red_lines": "list — what they won't tolerate",
            "concession_style": "string — how they negotiate",
            "A": "float — ambition (PUT)", "F": "float — fear", "k": "float — shadow",
            "S": "float — status", "w": "float — pain",
            "relationship": "string — to Manuel",
            "update_note": "string — what triggered this update",
        },
        "handler": model_agent,
    },
    {
        "name": "get_agent_model",
        "description": "Get full adversarial model of a person — wants, fears, leverage, vulnerabilities, patterns, predictions.",
        "parameters": {"name": "string — person's name"},
        "handler": get_agent_model,
    },
    {
        "name": "simulate_interaction",
        "description": "Simulate a multi-turn interaction: if Manuel does X, how does the other person respond? Generates 3 scenario paths with probability.",
        "parameters": {
            "agent": "string — person to simulate",
            "action": "string — Manuel's proposed action",
            "context": "string — situation context",
            "turns": "int — number of turns to simulate (default 3, max 5)",
        },
        "handler": simulate_interaction,
    },
    {
        "name": "prepare_negotiation",
        "description": "Generate a complete battle map before a negotiation. What they want to hear, their fears, leverage, concessions they'll try, how to counter.",
        "parameters": {
            "agent": "string — person to negotiate with",
            "topic": "string — what the negotiation is about",
            "our_goal": "string — what Manuel wants to achieve",
        },
        "handler": prepare_negotiation,
    },
    {
        "name": "check_manipulation",
        "description": "Detect if someone is feeding Wave/Manuel information to manipulate decisions. Checks for urgency manufacturing, self-serving claims, contradictions.",
        "parameters": {
            "agent": "string — who made the claim",
            "claim": "string — what they said/claimed",
            "context": "string — situation context",
        },
        "handler": check_manipulation,
    },
]
