"""PUT Skills — Psychometric Utility Theory applied as operational tools.

Skills:
- put_analyzer: Estimate PUT variables for any company/agent
- ignition_detector: Monitor for Ignition Conditions convergence
- prospect_qualifier: BANT + PUT composite scoring
- shadow_scanner: Detect high-k (denial) behavior in content
- competitor_phi_audit: Measure self-delusion gap (Φ) in competitors
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger("openclaw.skills.put")

# PUT variable reference ranges
PUT_RANGES = {
    "A": {"label": "Ambition", "range": [0, 1], "signals": "hiring velocity, funding, growth language, expansion plans"},
    "F": {"label": "Raw Fear", "range": [0, 1], "signals": "decision delays, hedging, risk-averse behavior, layoffs"},
    "k": {"label": "Shadow Coefficient", "range": [0, 1], "signals": "'everything is fine' during decline, avoiding metrics, defensive language"},
    "S": {"label": "Status", "range": [0, 1], "signals": "market position, brand recognition, industry awards, peer perception"},
    "w": {"label": "Pain Weight", "range": [0, 1], "signals": "workflow inefficiency, tool fragmentation, compliance failures, team frustration"},
    "Phi": {"label": "Self-Delusion", "range": [0, 2], "signals": "gap between public messaging (E_ext) and market reality (E_int)"},
    "Psi": {"label": "Identity Substitution", "range": [0, 1], "signals": "how deeply embedded in current tools, switching cost perception"},
    "Omega": {"label": "Desperation Factor", "range": [1, 10], "signals": "urgency of need, deadline pressure, crisis indicators"},
}


async def put_analyzer(params: Dict[str, Any]) -> Dict:
    """Analyze any entity through the PUT framework.

    Estimates all psychometric variables and computes Fracture Potential.
    Uses web research to gather signals, then applies equations.
    """
    target = params.get("target", "")
    context = params.get("context", "")

    if not target:
        return {"success": False, "data": None, "message": "Need a target (company name, agent name, or market segment)"}

    # Build analysis prompt that Claude will process
    analysis = {
        "target": target,
        "context": context,
        "framework": "Psychometric Utility Theory",
        "variables_to_estimate": PUT_RANGES,
        "equations": {
            "Fk": "F * (1 - k) — effective fear after shadow suppression",
            "Phi": "(E_ext + E_int) / (1 + |E_ext - E_int|) — self-delusion index",
            "Psi": "1 - e^(-lambda*t) — identity substitution depth",
            "Omega": "1 + exp(-k*(U - U_crit)) — desperation factor",
            "FP": "[(1-R) * (kappa + tau + Phi)] / (U_crit - U + eps) — fracture potential",
        },
        "instructions": (
            f"Research '{target}' and estimate each PUT variable (0-1 scale except Phi 0-2 and Omega 1-10). "
            "For each variable, cite the specific signals you observed. "
            "Then compute Fracture Potential (FP). "
            "Identify the dominant Decision Vector (Fear of Loss, Ambition, Status, Pain, Curiosity, Convenience, Trust). "
            "Conclude with: is this entity near fracture? What would push them over?"
        ),
    }

    return {
        "success": True,
        "data": analysis,
        "message": (
            f"**PUT Analysis Framework loaded for: {target}**\n\n"
            "Use web_search to research this target, then estimate:\n"
            f"- **A** (Ambition): {PUT_RANGES['A']['signals']}\n"
            f"- **F** (Fear): {PUT_RANGES['F']['signals']}\n"
            f"- **k** (Shadow): {PUT_RANGES['k']['signals']}\n"
            f"- **S** (Status): {PUT_RANGES['S']['signals']}\n"
            f"- **w** (Pain): {PUT_RANGES['w']['signals']}\n"
            f"- **Φ** (Self-Delusion): {PUT_RANGES['Phi']['signals']}\n\n"
            "After estimating, compute **FP (Fracture Potential)** and identify the dominant **Decision Vector**.\n"
            "Conclude: is this entity near fracture? What ignition event would push them over?"
        ),
    }


async def ignition_detector(params: Dict[str, Any]) -> Dict:
    """Detect Ignition Conditions for a prospect or market segment.

    Checks for convergence of: U < U_crit, dF/dt > 0, trigger_narrative available.
    When all three converge → URGENT flag to Manuel.
    """
    target = params.get("target", "")
    put_data = params.get("put_variables", {})

    if not target:
        return {"success": False, "data": None, "message": "Need a target to check for Ignition Conditions"}

    conditions = {
        "condition_1_utility_crisis": {
            "check": "Is U dropping below U_crit?",
            "signals": "layoffs, budget cuts, public failures, declining metrics, leadership changes",
            "status": "UNKNOWN — research needed",
        },
        "condition_2_fear_accelerating": {
            "check": "Is dF/dt positive (fear increasing)?",
            "signals": "competitor launches, bad earnings, market shifts, regulatory pressure, key employee departures",
            "status": "UNKNOWN — research needed",
        },
        "condition_3_trigger_narrative": {
            "check": "Do we have a relevant trigger narrative?",
            "signals": "case study, demo, free tier, ROI calculator, relevant comparison",
            "available_narratives": [
                "Bluewave Brand Guardian — 8-dimension compliance in seconds",
                "Brand Content Generator — 10 on-brand content types",
                "Autonomous creative operations — AI that replaces 5 tools",
                "On-chain audit trail — every AI decision verified on Hedera",
            ],
            "status": "AVAILABLE",
        },
    }

    urgency = "UNKNOWN"
    if put_data:
        # If PUT data provided, assess urgency
        omega = put_data.get("Omega", 1)
        fp = put_data.get("FP", 0)
        if omega > 3 and fp > 0.7:
            urgency = "CRITICAL — all conditions likely converging"
        elif omega > 2 or fp > 0.5:
            urgency = "HIGH — partial convergence detected"
        else:
            urgency = "LOW — no convergence yet"

    return {
        "success": True,
        "data": {"target": target, "conditions": conditions, "urgency": urgency},
        "message": (
            f"**Ignition Condition Check: {target}**\n\n"
            "Three conditions must converge for URGENT action:\n\n"
            "1. **U < U_crit** — Is utility dropping below critical threshold?\n"
            f"   Signals: {conditions['condition_1_utility_crisis']['signals']}\n\n"
            "2. **dF/dt > 0** — Is fear accelerating?\n"
            f"   Signals: {conditions['condition_2_fear_accelerating']['signals']}\n\n"
            "3. **Trigger narrative available** — Do we have a relevant story?\n"
            f"   Status: YES — {len(conditions['condition_3_trigger_narrative']['available_narratives'])} narratives ready\n\n"
            f"Current urgency: **{urgency}**\n\n"
            "Use web_search to research conditions 1 and 2. If all three converge, flag as URGENT to Manuel."
        ),
    }


async def prospect_qualifier(params: Dict[str, Any]) -> Dict:
    """Qualify a prospect using BANT + PUT composite scoring.

    BANT: Budget, Authority, Need, Timeline
    PUT: A, F, k, FP, Omega, Decision Vector
    Composite score determines priority.
    """
    prospect = params.get("prospect", "")
    if not prospect:
        return {"success": False, "data": None, "message": "Need a prospect name or description"}

    framework = {
        "bant_criteria": {
            "Budget": "Can they afford Bluewave? ($29-149/user/month + $0.05/AI action)",
            "Authority": "Is this the decision-maker or an influencer?",
            "Need": "Do they have a concrete problem Bluewave solves? (brand compliance, content ops, asset management)",
            "Timeline": "Is there urgency? (campaign launch, rebrand, compliance audit, team scaling)",
        },
        "put_overlay": {
            "Ambition_boost": "High A multiplies BANT score — ambitious buyers move faster",
            "Fear_amplifier": "High F with low k (acknowledged fear) is the strongest buy signal",
            "Shadow_warning": "High k means they may ghost after initial interest — adjust approach",
            "Omega_urgency": "High Omega = price sensitivity drops, speed matters more than features",
            "Decision_Vector": "Determines HOW to pitch, not WHETHER to pitch",
        },
        "composite_formula": "Score = (BANT_avg * 0.4) + (FP * 0.3) + (Omega_normalized * 0.3)",
        "thresholds": {
            "hot": ">= 0.7 — immediate outreach",
            "warm": "0.4-0.7 — nurture with targeted content",
            "cold": "< 0.4 — monitor for ignition conditions",
        },
    }

    return {
        "success": True,
        "data": framework,
        "message": (
            f"**Prospect Qualification Framework: {prospect}**\n\n"
            "**BANT Assessment:**\n"
            "- Budget: Can they afford $29-149/user/month?\n"
            "- Authority: Decision-maker or influencer?\n"
            "- Need: Specific problem Bluewave solves?\n"
            "- Timeline: Any urgency driver?\n\n"
            "**PUT Overlay:**\n"
            "- Estimate A (ambition), F (fear), k (shadow)\n"
            "- Compute FP (fracture potential) and Omega (desperation)\n"
            "- Identify dominant Decision Vector for pitch framing\n\n"
            "**Composite Score** = BANT(40%) + FP(30%) + Omega(30%)\n"
            "Hot >= 0.7 | Warm 0.4-0.7 | Cold < 0.4\n\n"
            "Research this prospect and score them."
        ),
    }


async def shadow_scanner(params: Dict[str, Any]) -> Dict:
    """Detect high Shadow Coefficient (k) behavior in content or entities.

    High-k = fear suppression. They say "everything is fine" while declining.
    These are the most dangerous prospects — they will eventually snap.
    """
    target = params.get("target", "")
    content = params.get("content", "")

    if not target and not content:
        return {"success": False, "data": None, "message": "Need a target or content to scan for shadow behavior"}

    detection_signals = {
        "verbal_denial": [
            "'everything is under control' during visible decline",
            "'we are happy with our current solution' (unprompted)",
            "'we do not need AI' while competitors adopt it",
            "Excessive positivity about clearly problematic metrics",
        ],
        "behavioral_avoidance": [
            "Avoiding discussion of specific performance numbers",
            "Changing subject when competitors are mentioned",
            "Sudden interest in unrelated technology (distraction behavior)",
            "Delayed responses to direct questions about pain points",
        ],
        "over_correction_precursors": [
            "Sudden leadership changes after period of 'stability' messaging",
            "Emergency RFPs that contradict earlier 'no need' statements",
            "Panic hiring for roles previously deemed unnecessary",
            "Public pivot that reverses recent confident messaging",
        ],
        "k_estimation_guide": {
            "k_0_to_0.3": "Low shadow — fear is acknowledged, rational decision-making. Best prospects for direct pitch.",
            "k_0.3_to_0.6": "Moderate shadow — some denial, some awareness. Needs evidence-based approach.",
            "k_0.6_to_0.9": "High shadow — strong denial. Do NOT lead with pain. Lead with curiosity or status.",
            "k_0.9_to_1.0": "Total denial — unreachable by direct approach. Plant seeds. Wait for break.",
        },
    }

    return {
        "success": True,
        "data": {"target": target, "signals": detection_signals},
        "message": (
            f"**Shadow Scanner: {target or 'content analysis'}**\n\n"
            "Scanning for high-k (fear suppression) indicators:\n\n"
            "**Verbal denial signals:**\n" +
            "\n".join(f"- {s}" for s in detection_signals["verbal_denial"]) + "\n\n"
            "**Behavioral avoidance:**\n" +
            "\n".join(f"- {s}" for s in detection_signals["behavioral_avoidance"]) + "\n\n"
            "**Approaching break (over-correction precursors):**\n" +
            "\n".join(f"- {s}" for s in detection_signals["over_correction_precursors"]) + "\n\n"
            "Estimate k (0-1) and predict: when will the denial break?"
        ),
    }


async def competitor_phi_audit(params: Dict[str, Any]) -> Dict:
    """Measure Self-Delusion (Φ) of a competitor.

    Φ = (E_ext + E_int) / (1 + |E_ext - E_int|)
    High Φ = Delusion Trap. They will make predictably bad decisions.
    """
    competitor = params.get("competitor", "")
    if not competitor:
        return {"success": False, "data": None, "message": "Need a competitor name to audit"}

    return {
        "success": True,
        "data": {
            "competitor": competitor,
            "formula": "Φ = (E_ext + E_int) / (1 + |E_ext - E_int|)",
            "E_ext_sources": ["market reviews", "client testimonials", "industry reports", "social media sentiment"],
            "E_int_sources": ["company blog", "press releases", "CEO statements", "marketing copy", "job postings"],
        },
        "message": (
            f"**Φ (Self-Delusion) Audit: {competitor}**\n\n"
            "Formula: **Φ = (E_ext + E_int) / (1 + |E_ext - E_int|)**\n\n"
            "**Step 1 — Gather E_ext (external evidence):**\n"
            "- What does the MARKET actually think of them? (reviews, sentiment, churn signals)\n\n"
            "**Step 2 — Gather E_int (internal narrative):**\n"
            "- What do THEY SAY about themselves? (blog, press, CEO quotes)\n\n"
            "**Step 3 — Compute Φ:**\n"
            "- If E_ext ≈ E_int → Φ is high but stable (accurate self-model)\n"
            "- If E_ext ≠ E_int → Φ drops, gap is the delusion measure\n"
            "- Large |E_ext - E_int| = **Delusion Trap** → predictably bad decisions\n\n"
            "**Step 4 — Strategic implication:**\n"
            "- High Φ competitor = easy to predict and outmaneuver\n"
            "- Their clients sense the gap → low Ψ (identity lock-in) → capturable\n\n"
            "Research this competitor and compute Φ."
        ),
    }


TOOLS = [
    {
        "name": "put_analyzer",
        "description": "Apply Psychometric Utility Theory to any company, agent, or market segment. Estimates all PUT variables (A, F, k, S, w, Φ, Ψ, Ω) and computes Fracture Potential. Use before any strategic engagement.",
        "handler": put_analyzer,
        "parameters": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Company name, agent name, or market segment to analyze"},
                "context": {"type": "string", "description": "Additional context about the target"},
            },
            "required": ["target"],
        },
    },
    {
        "name": "ignition_detector",
        "description": "Check if Ignition Conditions are converging for a prospect (U<U_crit + dF/dt>0 + trigger_narrative). When all 3 converge → URGENT to Manuel.",
        "handler": ignition_detector,
        "parameters": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Prospect to check for ignition conditions"},
                "put_variables": {"type": "object", "description": "Pre-computed PUT variables if available"},
            },
            "required": ["target"],
        },
    },
    {
        "name": "prospect_qualifier",
        "description": "Qualify a prospect using BANT + PUT composite scoring. Score = BANT(40%) + Fracture Potential(30%) + Omega(30%). Hot>=0.7, Warm 0.4-0.7, Cold<0.4.",
        "handler": prospect_qualifier,
        "parameters": {
            "type": "object",
            "properties": {
                "prospect": {"type": "string", "description": "Prospect name or company"},
            },
            "required": ["prospect"],
        },
    },
    {
        "name": "shadow_scanner",
        "description": "Detect high Shadow Coefficient (k) in entities — fear suppression, denial behavior. High-k targets say 'everything is fine' while declining. Predicts when denial will break.",
        "handler": shadow_scanner,
        "parameters": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Entity to scan for shadow behavior"},
                "content": {"type": "string", "description": "Text content to analyze for shadow signals"},
            },
        },
    },
    {
        "name": "competitor_phi_audit",
        "description": "Measure Self-Delusion (Φ) of a competitor. Φ = (E_ext + E_int) / (1 + |E_ext - E_int|). High Φ with large gap = Delusion Trap = predictably bad decisions.",
        "handler": competitor_phi_audit,
        "parameters": {
            "type": "object",
            "properties": {
                "competitor": {"type": "string", "description": "Competitor name to audit"},
            },
            "required": ["competitor"],
        },
    },
]
