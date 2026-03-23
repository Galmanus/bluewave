"""
Strategic Sensor — Weak Signal Detection + Autonomous Hypothesis Generation.

Wave stops waiting to be asked. He scans, detects, hypothesizes, and alerts.

The difference between tactical and strategic intelligence:
- Tactical: you ask, I answer
- Strategic: I see what you haven't noticed yet and tell you before it matters

Created by Manuel Guilherme Galmanus, 2026.
Designed by Wave as his evolution from reactive advisor to active sensor.
"""

import json
import logging
import math
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("openclaw.sensor")

MEMORY_DIR = Path(__file__).parent.parent / "memory"
SIGNALS_FILE = MEMORY_DIR / "weak_signals.jsonl"
STRATEGIC_HYPOTHESES_FILE = MEMORY_DIR / "strategic_hypotheses.jsonl"
ALERTS_FILE = MEMORY_DIR / "proactive_alerts.jsonl"
BASELINE_FILE = MEMORY_DIR / "signal_baseline.json"


# ══════════════════════════════════════════════════════════════
# 1. WEAK SIGNAL INGESTION & ANOMALY DETECTION
# ══════════════════════════════════════════════════════════════

async def ingest_signal(params: Dict[str, Any]) -> Dict:
    """Ingest a signal from any source — market, tech, people, competition.

    Signals are raw observations. The system detects anomalies by comparing
    against the baseline of normal signals.
    """
    source = params.get("source", "")  # market, tech, competitor, person, news
    content = params.get("content", "")
    category = params.get("category", "general")
    intensity = float(params.get("intensity", 0.5))  # 0-1, how strong the signal is
    related_to = params.get("related_to", [])  # people, companies, topics

    if not content:
        return {"success": False, "data": None, "message": "Need signal content"}

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    signal = {
        "timestamp": datetime.utcnow().isoformat(),
        "source": source,
        "content": content[:500],
        "category": category,
        "intensity": intensity,
        "related_to": related_to if isinstance(related_to, list) else [related_to],
        "processed": False,
        "anomaly_score": 0,
    }

    # Check against baseline for anomaly
    baseline = _load_baseline()
    if baseline:
        cat_baseline = baseline.get(category, {})
        avg_intensity = cat_baseline.get("avg_intensity", 0.5)
        if intensity > avg_intensity * 1.5:
            signal["anomaly_score"] = min(1.0, (intensity - avg_intensity) / avg_intensity)
            signal["anomaly_type"] = "intensity_spike"
        elif category not in baseline:
            signal["anomaly_score"] = 0.7
            signal["anomaly_type"] = "new_category"

    with open(SIGNALS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(signal, ensure_ascii=False) + "\n")

    # Update baseline
    _update_baseline(category, intensity)

    result = {
        "success": True,
        "data": {"anomaly_score": signal["anomaly_score"]},
        "message": f"Signal ingested: {source}/{category} (intensity: {intensity:.1f})"
    }

    # Auto-alert if anomaly is high
    if signal["anomaly_score"] > 0.6:
        result["data"]["alert"] = f"ANOMALY DETECTED: {signal.get('anomaly_type', 'unknown')} in {category} — intensity {intensity:.1f} vs baseline {avg_intensity:.1f}"

    return result


def _load_baseline() -> dict:
    if BASELINE_FILE.exists():
        try:
            return json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _update_baseline(category: str, intensity: float):
    baseline = _load_baseline()
    if category not in baseline:
        baseline[category] = {"count": 0, "total_intensity": 0, "avg_intensity": 0.5}

    b = baseline[category]
    b["count"] += 1
    b["total_intensity"] += intensity
    b["avg_intensity"] = b["total_intensity"] / b["count"]

    BASELINE_FILE.write_text(json.dumps(baseline, indent=2, ensure_ascii=False), encoding="utf-8")


async def get_anomalies(params: Dict[str, Any]) -> Dict:
    """Get all detected anomalies — signals that deviate from baseline."""
    min_score = float(params.get("min_score", 0.5))
    last_hours = int(params.get("last_hours", 24))

    if not SIGNALS_FILE.exists():
        return {"success": True, "data": {"anomalies": []}, "message": "No signals yet."}

    cutoff = datetime.utcnow() - timedelta(hours=last_hours)
    anomalies = []

    for line in SIGNALS_FILE.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            s = json.loads(line)
            if s.get("anomaly_score", 0) < min_score:
                continue
            try:
                ts = datetime.fromisoformat(s["timestamp"])
                if ts < cutoff:
                    continue
            except Exception:
                pass
            anomalies.append({
                "content": s["content"][:200],
                "source": s["source"],
                "category": s["category"],
                "intensity": s["intensity"],
                "anomaly_score": s["anomaly_score"],
                "anomaly_type": s.get("anomaly_type", ""),
                "timestamp": s["timestamp"],
            })
        except Exception:
            continue

    anomalies.sort(key=lambda x: x["anomaly_score"], reverse=True)

    return {
        "success": True,
        "data": {"anomalies": anomalies[:20]},
        "message": f"{len(anomalies)} anomalies in last {last_hours}h."
    }


# ══════════════════════════════════════════════════════════════
# 2. AUTONOMOUS HYPOTHESIS GENERATION
# ══════════════════════════════════════════════════════════════

async def generate_strategic_hypotheses(params: Dict[str, Any]) -> Dict:
    """Generate strategic hypotheses based on recent signals — WITHOUT being asked.

    This is the proactive intelligence function. Wave looks at recent signals,
    cross-references with causal model and stakeholder data, and generates
    hypotheses about what's coming.
    """
    focus = params.get("focus", "")  # optional focus area

    # Gather recent signals
    recent_signals = []
    if SIGNALS_FILE.exists():
        for line in SIGNALS_FILE.read_text(encoding="utf-8").strip().split("\n"):
            if line.strip():
                try:
                    s = json.loads(line)
                    # Last 48 hours
                    ts = datetime.fromisoformat(s["timestamp"])
                    if (datetime.utcnow() - ts).total_seconds() < 48 * 3600:
                        recent_signals.append(s)
                except Exception:
                    pass

    # Gather recent memories
    recent_memories = []
    episodes_file = MEMORY_DIR / "episodes.jsonl"
    if episodes_file.exists():
        for line in episodes_file.read_text(encoding="utf-8").strip().split("\n"):
            if line.strip():
                try:
                    ep = json.loads(line)
                    recent_memories.append(ep.get("content", "")[:100])
                except Exception:
                    pass
        recent_memories = recent_memories[-10:]

    # Gather stakeholder state
    stakeholders_summary = ""
    stakeholders_file = MEMORY_DIR / "stakeholders.json"
    if stakeholders_file.exists():
        try:
            sh = json.loads(stakeholders_file.read_text(encoding="utf-8"))
            for key, val in sh.items():
                put = val.get("put", {})
                stakeholders_summary += f"  {val.get('name', key)}: A={put.get('A','?')} F={put.get('F','?')} S={put.get('S','?')}\n"
        except Exception:
            pass

    # Use LLM to generate hypotheses
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from claude_engine import claude_call

        signals_text = "\n".join([f"  [{s.get('source', '?')}/{s.get('category', '?')}] {s.get('content', '')[:100]}" for s in recent_signals[-15:]])
        memories_text = "\n".join([f"  - {m}" for m in recent_memories])

        prompt = f"""You are Wave's strategic sensor. Your job is to detect what hasn't been noticed yet.

RECENT SIGNALS (last 48h):
{signals_text if signals_text else '  No signals ingested yet.'}

RECENT MEMORIES:
{memories_text if memories_text else '  No recent memories.'}

STAKEHOLDER STATE:
{stakeholders_summary if stakeholders_summary else '  No stakeholder data.'}

CONTEXT:
Manuel is AI Engineer at Ialum (R$10K/month PJ). Building Wave (221 tools autonomous agent) and MIDAS (privacy DeFi on Starknet). Goal: $1M in 9 months. 26 emails sent to companies, 0 replies. Fagner is CEO of Ialum.
{f'FOCUS AREA: {focus}' if focus else ''}

Generate exactly 3 STRATEGIC HYPOTHESES about things that are likely to happen in the next 2-4 weeks that Manuel hasn't noticed yet. Each must be:
1. SPECIFIC (not "the market will change" — but "Starknet Foundation will open grant round for privacy tools because X")
2. ACTIONABLE (what should Manuel do about it)
3. TIME-BOUND (when this becomes relevant)
4. CONFIDENCE-SCORED (0-100%)

Format each as:
HYPOTHESIS: [statement]
EVIDENCE: [what signals support this]
ACTION: [what Manuel should do]
TIMELINE: [when]
CONFIDENCE: [0-100%]"""

        result = await claude_call(prompt=prompt, model="sonnet", timeout=90)

        if result.get("success"):
            hypotheses_text = result["response"]

            # Log
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "focus": focus,
                "signals_count": len(recent_signals),
                "hypotheses": hypotheses_text[:2000],
            }
            with open(STRATEGIC_HYPOTHESES_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

            return {
                "success": True,
                "data": {"hypotheses": hypotheses_text, "signals_analyzed": len(recent_signals)},
                "message": f"3 strategic hypotheses generated from {len(recent_signals)} signals."
            }
        else:
            return {"success": False, "data": None, "message": "Hypothesis engine unavailable"}
    except Exception as e:
        return {"success": False, "data": None, "message": f"Generation failed: {e}"}


# ══════════════════════════════════════════════════════════════
# 3. PROACTIVE ALERTS
# ══════════════════════════════════════════════════════════════

async def create_alert(params: Dict[str, Any]) -> Dict:
    """Create a proactive alert — Wave notifies Manuel without being asked."""
    title = params.get("title", "")
    content = params.get("content", "")
    urgency = params.get("urgency", "medium")  # low, medium, high, critical
    category = params.get("category", "strategic")
    action_required = params.get("action_required", "")
    deadline = params.get("deadline", "")

    if not title or not content:
        return {"success": False, "data": None, "message": "Need title and content"}

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    alert = {
        "timestamp": datetime.utcnow().isoformat(),
        "title": title,
        "content": content[:500],
        "urgency": urgency,
        "category": category,
        "action_required": action_required,
        "deadline": deadline,
        "status": "pending",  # pending, acknowledged, acted_on, dismissed
    }

    with open(ALERTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(alert, ensure_ascii=False) + "\n")

    # If critical, try to notify Manuel via Telegram
    if urgency in ("critical", "high"):
        try:
            import httpx
            token = os.environ.get("TELEGRAM_BOT_TOKEN", "8555774668:AAFvgQNB0FAYwCuZYqr6tFrALb8lLjfBCPw")
            chat_id = os.environ.get("TELEGRAM_NOTIFY_CHAT_ID", "7461066889")
            msg = f"[WAVE ALERT — {urgency.upper()}]\n\n{title}\n\n{content[:300]}\n\nAction: {action_required}"
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": msg[:4000]},
                )
            alert["notified"] = True
        except Exception:
            alert["notified"] = False

    return {
        "success": True,
        "data": alert,
        "message": f"Alert created: [{urgency.upper()}] {title}"
    }


async def get_alerts(params: Dict[str, Any]) -> Dict:
    """Get pending proactive alerts."""
    status = params.get("status", "pending")

    if not ALERTS_FILE.exists():
        return {"success": True, "data": {"alerts": []}, "message": "No alerts."}

    alerts = []
    for line in ALERTS_FILE.read_text(encoding="utf-8").strip().split("\n"):
        if line.strip():
            try:
                a = json.loads(line)
                if status and a.get("status") != status:
                    continue
                alerts.append(a)
            except Exception:
                pass

    alerts.sort(key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x.get("urgency", "medium"), 2))

    return {
        "success": True,
        "data": {"alerts": alerts[-20:]},
        "message": f"{len(alerts)} {status} alerts."
    }


# ══════════════════════════════════════════════════════════════
# 4. STRATEGIC SCAN — ALL-IN-ONE
# ══════════════════════════════════════════════════════════════

async def strategic_scan(params: Dict[str, Any]) -> Dict:
    """Run a complete strategic scan: ingest signals, detect anomalies,
    generate hypotheses, and create alerts. The full sensor loop in one call."""
    focus = params.get("focus", "")

    results = {
        "anomalies": [],
        "hypotheses": "",
        "alerts_created": 0,
    }

    # 1. Get anomalies
    anomalies = await get_anomalies({"min_score": 0.5, "last_hours": 48})
    results["anomalies"] = anomalies.get("data", {}).get("anomalies", [])

    # 2. Generate hypotheses
    hyp = await generate_strategic_hypotheses({"focus": focus})
    if hyp.get("success"):
        results["hypotheses"] = hyp.get("data", {}).get("hypotheses", "")

    # 3. Create alerts for high-anomaly signals
    for anomaly in results["anomalies"]:
        if anomaly.get("anomaly_score", 0) > 0.7:
            await create_alert({
                "title": f"Anomaly: {anomaly.get('category', '')} signal spike",
                "content": anomaly.get("content", "")[:300],
                "urgency": "high" if anomaly["anomaly_score"] > 0.8 else "medium",
                "category": anomaly.get("category", ""),
                "action_required": "Review signal and determine if action needed",
            })
            results["alerts_created"] += 1

    return {
        "success": True,
        "data": results,
        "message": f"Scan complete: {len(results['anomalies'])} anomalies, {results['alerts_created']} alerts, hypotheses generated."
    }


# ── Tool Definitions ─────────────────────────────────────────

TOOLS = [
    {
        "name": "ingest_signal",
        "description": "Ingest a signal from any source. Auto-detects anomalies against baseline. Wave's sensory input.",
        "parameters": {
            "source": "string — market, tech, competitor, person, news",
            "content": "string — what was observed",
            "category": "string — general, market_move, hiring, funding, product_launch, regulatory",
            "intensity": "float — signal strength 0-1 (default 0.5)",
            "related_to": "list — people/companies/topics related",
        },
        "handler": ingest_signal,
    },
    {
        "name": "get_anomalies",
        "description": "Get detected anomalies — signals that deviate from normal baseline.",
        "parameters": {
            "min_score": "float — minimum anomaly score (default 0.5)",
            "last_hours": "int — look back this many hours (default 24)",
        },
        "handler": get_anomalies,
    },
    {
        "name": "generate_strategic_hypotheses",
        "description": "Generate 3 strategic hypotheses about what's coming — WITHOUT being asked. Proactive intelligence.",
        "parameters": {
            "focus": "string — optional focus area (e.g., 'Starknet ecosystem', 'Fagner negotiation')",
        },
        "handler": generate_strategic_hypotheses,
    },
    {
        "name": "create_alert",
        "description": "Create a proactive alert — Wave notifies Manuel via Telegram without being asked.",
        "parameters": {
            "title": "string — alert title",
            "content": "string — what's happening",
            "urgency": "string — low, medium, high, critical",
            "category": "string — strategic, market, technical, personal",
            "action_required": "string — what Manuel should do",
            "deadline": "string — when action is needed by",
        },
        "handler": create_alert,
    },
    {
        "name": "get_alerts",
        "description": "Get pending proactive alerts sorted by urgency.",
        "parameters": {
            "status": "string — pending, acknowledged, acted_on, dismissed (default: pending)",
        },
        "handler": get_alerts,
    },
    {
        "name": "strategic_scan",
        "description": "Run full strategic scan: detect anomalies, generate hypotheses, create alerts. The complete sensor loop.",
        "parameters": {
            "focus": "string — optional focus area",
        },
        "handler": strategic_scan,
    },
]
