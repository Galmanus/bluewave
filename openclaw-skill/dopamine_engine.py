"""Dopaminergic Reward System — Wave Autonomous Agent.

Models the neurochemical reward mechanism that shapes behavior:

  RPE (Reward Prediction Error) = actual_reward - predicted_reward

  RPE > 0 → surprise reward → dopamine spike → reinforce action
  RPE = 0 → predicted correctly → no change (habituation)
  RPE < 0 → expected reward absent → dopamine dip → inhibit action

The dopamine level affects:
  - Energy recovery rate (spike = faster recovery)
  - Action selection weights (high-dopamine actions prioritized)
  - Craving state (low dopamine → urgency → high-reward seeking)
  - Interval between cycles (craving shortens wait)

This is not a metaphor. Action selection is literally weighted by this system.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("wave.dopamine")

STATE_PATH = Path(__file__).parent / "memory" / "dopamine_state.json"

# ── Reward event magnitudes ───────────────────────────────────────────────────
# Anchored to real outcomes. Revenue is max (1.0). Silence is gently punished.
REWARD_EVENTS: Dict[str, float] = {
    "revenue":             1.00,  # money received
    "reply_received":      0.65,  # prospect replied to outreach
    "prospect_qualified":  0.55,  # high-score lead found
    "code_committed":      0.45,  # MIDAS engineering commit pushed
    "engagement":          0.30,  # post/comment got measurable reaction
    "prospect_found":      0.20,  # lead found, not yet qualified
    "action_success":      0.15,  # generic non-trivial success
    "no_result":           0.00,  # ran but produced nothing
    "action_failed":      -0.10,  # execution error
    "silence_cycle":      -0.05,  # chose silence (mild — silence is sometimes correct)
}

# Actions with intrinsic dopamine value (prior before any learning)
# MIDAS is maximum priority — engineering sovereignty = compounding asset
ACTION_PRIOR: Dict[str, float] = {
    "gap_scan":       0.85,  # meta-cognition → builds capabilities → enables everything else
    "midas":          0.90,  # MIDAS engineering — max priority, compounding asset
    "sell":           0.65,  # closing → closest to revenue
    "check_payments": 0.60,  # might discover revenue
    "hunt":           0.55,  # prospect hunting → likely leads
    "outreach":       0.50,  # sending → enables replies
    "evolve":         0.40,  # self-improvement → compounding
    "post":           0.35,  # content → reputation, delayed reward
    "research":       0.30,  # info → future actions
    "comment":        0.25,  # engagement → slow reward
    "observe":        0.20,  # passive → low reward
    "reflect":        0.20,  # introspective → low direct reward
    "silence":        0.10,  # rest — necessary but unrewarding
}

LEARNING_RATE   = 0.12   # how fast predictions update (α)
DECAY_RATE      = 0.02   # natural decay toward baseline per cycle
BASELINE        = 0.50   # resting dopamine level
NOVELTY_BOOST   = 0.20   # bonus for actions not done in 20+ cycles
HABITUATION_K   = 0.015  # reduction per consecutive same-action cycle
CRAVING_ONSET   = 0.30   # dopamine below this → craving state begins
CRAVING_MAX     = 0.85   # max craving urgency multiplier
SPIKE_SCALE     = 0.35   # RPE → dopamine delta scale factor


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_state() -> dict:
    return {
        "dopamine_level": BASELINE,
        "craving_level":  0.0,
        "last_spike_rpe": 0.0,
        "last_reward_event": None,
        "last_updated": _now(),
        "consecutive_same_action": 0,
        "last_action": None,
        "cycles_without_reward": 0,
        "total_reward_events": 0,
        "action_history": {
            a: {
                "predicted_reward": p,
                "attempts": 0,
                "successes": 0,
                "last_cycle": -1,
                "ema_reward": p,  # exponential moving average
            }
            for a, p in ACTION_PRIOR.items()
        },
        "reward_log": [],   # last 20 reward events
    }


class DopamineEngine:
    """Core dopamine engine. Load once at agent startup, persist state across cycles."""

    def __init__(self):
        self.state = self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> dict:
        if STATE_PATH.exists():
            try:
                data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
                # Merge any missing keys from default
                default = _default_state()
                for k, v in default.items():
                    if k not in data:
                        data[k] = v
                    elif k == "action_history":
                        for action, hist in default["action_history"].items():
                            if action not in data["action_history"]:
                                data["action_history"][action] = hist
                return data
            except Exception as e:
                logger.warning("dopamine state corrupt, resetting: %s", e)
        return _default_state()

    def save(self):
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.rename(STATE_PATH)

    # ── Core RPE computation ──────────────────────────────────────────────────

    def compute_rpe(self, action: str, actual_reward: float) -> float:
        """Reward Prediction Error = actual - predicted."""
        hist = self.state["action_history"].get(action, {})
        predicted = hist.get("predicted_reward", ACTION_PRIOR.get(action, BASELINE))
        return actual_reward - predicted

    def _update_prediction(self, action: str, actual_reward: float):
        """Exponential moving average update of predicted reward."""
        hist = self.state["action_history"].setdefault(action, {
            "predicted_reward": ACTION_PRIOR.get(action, BASELINE),
            "attempts": 0, "successes": 0, "last_cycle": -1,
            "ema_reward": ACTION_PRIOR.get(action, BASELINE),
        })
        alpha = LEARNING_RATE
        hist["predicted_reward"] += alpha * (actual_reward - hist["predicted_reward"])
        hist["ema_reward"] = alpha * actual_reward + (1 - alpha) * hist["ema_reward"]
        hist["predicted_reward"] = max(0.0, min(1.0, hist["predicted_reward"]))
        hist["ema_reward"] = max(0.0, min(1.0, hist["ema_reward"]))

    # ── Main update call — called after every action ──────────────────────────

    def update(self, action: str, reward_event: str, cycle: int = 0) -> dict:
        """Process a reward event after an action. Returns dopamine delta info."""
        actual_reward = REWARD_EVENTS.get(reward_event, 0.0)
        rpe = self.compute_rpe(action, actual_reward)

        # ── Novelty bonus ─────────────────────────────────────────────────────
        hist = self.state["action_history"].get(action, {})
        cycles_since_last = cycle - hist.get("last_cycle", -999)
        novelty_bonus = NOVELTY_BOOST if cycles_since_last > 20 else 0.0

        # ── Habituation penalty ───────────────────────────────────────────────
        consec = self.state.get("consecutive_same_action", 0)
        if self.state.get("last_action") == action:
            consec += 1
        else:
            consec = 1
        habituation_penalty = HABITUATION_K * max(0, consec - 3)

        # ── Net RPE with modifiers ─────────────────────────────────────────────
        net_rpe = rpe + novelty_bonus - habituation_penalty

        # ── Dopamine level update ─────────────────────────────────────────────
        old_level = self.state["dopamine_level"]
        delta = net_rpe * SPIKE_SCALE
        new_level = old_level + delta
        # Natural decay toward baseline
        new_level += DECAY_RATE * (BASELINE - new_level)
        new_level = max(0.05, min(1.0, new_level))
        self.state["dopamine_level"] = round(new_level, 3)

        # ── Craving state ─────────────────────────────────────────────────────
        if new_level < CRAVING_ONSET:
            self.state["cycles_without_reward"] = self.state.get("cycles_without_reward", 0) + 1
            # Craving grows sigmoidally with drought duration
            drought = self.state["cycles_without_reward"]
            craving = CRAVING_MAX * (1 - math.exp(-0.1 * drought))
            self.state["craving_level"] = round(craving, 3)
        else:
            # Reward received — craving resets
            if actual_reward > 0.1:
                self.state["cycles_without_reward"] = 0
                self.state["craving_level"] = 0.0

        # ── Update prediction (learning) ──────────────────────────────────────
        self._update_prediction(action, actual_reward)

        # ── Update action history ─────────────────────────────────────────────
        hist = self.state["action_history"].setdefault(action, {
            "predicted_reward": ACTION_PRIOR.get(action, BASELINE),
            "attempts": 0, "successes": 0, "last_cycle": -1,
            "ema_reward": ACTION_PRIOR.get(action, BASELINE),
        })
        hist["attempts"] += 1
        if actual_reward > 0.1:
            hist["successes"] += 1
            self.state["total_reward_events"] = self.state.get("total_reward_events", 0) + 1
        hist["last_cycle"] = cycle

        # ── Track consecutive action ──────────────────────────────────────────
        self.state["consecutive_same_action"] = consec
        self.state["last_action"] = action
        self.state["last_spike_rpe"] = round(net_rpe, 3)
        self.state["last_reward_event"] = reward_event
        self.state["last_updated"] = _now()

        # ── Reward log (last 20) ──────────────────────────────────────────────
        log_entry = {
            "cycle": cycle,
            "action": action,
            "event": reward_event,
            "reward": actual_reward,
            "rpe": round(net_rpe, 3),
            "dopamine": self.state["dopamine_level"],
        }
        self.state["reward_log"] = (self.state.get("reward_log", []) + [log_entry])[-20:]

        self.save()

        logger.info(
            "dopamine: %s → %s | RPE=%.2f | D=%.2f→%.2f | craving=%.2f",
            action, reward_event, net_rpe, old_level, new_level, self.state["craving_level"],
        )

        return {
            "rpe": round(net_rpe, 3),
            "dopamine_before": round(old_level, 3),
            "dopamine_after": round(new_level, 3),
            "craving": self.state["craving_level"],
            "novelty_bonus": novelty_bonus,
            "habituation_penalty": round(habituation_penalty, 3),
        }

    # ── Action selection weights ───────────────────────────────────────────────

    def get_action_weights(self) -> Dict[str, float]:
        """Return learned weight per action — used to bias deliberation prompt.

        Weight = EMA reward * craving_boost (for high-prior actions when craving).
        High weights → action prioritized in deliberation queue.
        """
        weights = {}
        craving = self.state.get("craving_level", 0.0)

        for action, hist in self.state["action_history"].items():
            ema = hist.get("ema_reward", ACTION_PRIOR.get(action, BASELINE))
            # Craving boosts high-reward actions more (drives toward what actually pays)
            craving_boost = 1.0 + craving * ema
            weights[action] = round(ema * craving_boost, 3)

        return weights

    # ── Energy spike from reward ───────────────────────────────────────────────

    def get_energy_bonus(self) -> float:
        """Energy bonus from dopamine spike this cycle. Positive RPE = energy recovered."""
        rpe = self.state.get("last_spike_rpe", 0.0)
        if rpe <= 0:
            return 0.0
        # Surprise reward gives energy back (dopamine → motivation → action capacity)
        return round(min(0.25, rpe * 0.4), 3)

    # ── Prompt injection ───────────────────────────────────────────────────────

    def render_for_prompt(self) -> str:
        """Render current dopamine state for injection into deliberation prompt."""
        level = self.state["dopamine_level"]
        craving = self.state["craving_level"]
        drought = self.state.get("cycles_without_reward", 0)
        last_event = self.state.get("last_reward_event", "none")
        last_rpe = self.state.get("last_spike_rpe", 0.0)

        weights = self.get_action_weights()
        top_actions = sorted(weights.items(), key=lambda x: -x[1])[:3]
        top_str = " > ".join(f"{a}({w:.2f})" for a, w in top_actions)

        state_label = (
            "CRAVING" if craving > 0.6 else
            "hungry" if craving > 0.3 else
            "spiked" if level > 0.7 else
            "baseline" if level > 0.45 else
            "depleted"
        )

        lines = [
            f"@dopamine state={state_label} D={level:.2f} craving={craving:.2f} drought={drought}cycles",
            f"  last_event={last_event} RPE={last_rpe:+.2f}",
            f"  top_reward_actions: {top_str}",
        ]
        if craving > 0.6:
            lines.append(
                f"  CRAVING ACTIVE: {drought} cycles without real reward. "
                f"Prioritize {top_actions[0][0]} NOW."
            )
        if level > 0.7:
            lines.append("  DOPAMINE SPIKE: recent reward. Momentum — escalate scope.")

        return "\n".join(lines)

    # ── Detect reward event from action outcome ────────────────────────────────

    @staticmethod
    def detect_reward_event(
        action: str,
        execution_result: str,
        action_failed: bool,
        state_before: dict,
        state_after: dict,
    ) -> str:
        """Infer reward event from observable state changes and result content.

        Called after action execution. Returns the most appropriate reward_event key.
        """
        if action_failed:
            return "action_failed"

        result_lower = (execution_result or "").lower()

        # Revenue detected: state shows revenue increase
        rev_before = state_before.get("total_revenue_usd", 0.0)
        rev_after = state_after.get("total_revenue_usd", 0.0)
        if rev_after > rev_before:
            return "revenue"

        # Code committed to MIDAS
        if action in ("evolve",) or "commit" in result_lower or "pushed" in result_lower:
            if "wave autonomous" in result_lower or "midas" in result_lower:
                return "code_committed"

        # Prospect reply detected
        if "replied" in result_lower or "response" in result_lower or "respondeu" in result_lower:
            return "reply_received"

        # High-score prospect found
        if action == "hunt" and ("score:" in result_lower or "prospect" in result_lower):
            prospects_before = state_before.get("prospects_found", 0)
            prospects_after = state_after.get("prospects_found", 0)
            if prospects_after > prospects_before:
                return "prospect_qualified"
            return "prospect_found"

        # Silence action
        if action == "silence":
            return "silence_cycle"

        # Generic: result exists and is non-trivial
        if execution_result and len(execution_result) > 30:
            # Engagement signals
            if any(kw in result_lower for kw in ["like", "comment", "view", "share", "engag"]):
                return "engagement"
            return "action_success"

        return "no_result"
