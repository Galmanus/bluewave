"""
put_calibrator.py — Calibrate PUT coefficients through real-world feedback

The biggest weakness of Psychometric Utility Theory: the coefficients
α, β, γ, δ, ε are "different from person to person" with no calibration method.

This skill solves it through:
1. Monte Carlo simulation — generate N coefficient sets, simulate outcomes
2. Real-world feedback loop — compare predictions with actual responses
3. Bayesian update — narrow coefficient ranges based on what worked
4. Per-archetype profiles — different coefficient sets for different prospect types

After 50-100 real interactions, coefficients converge to calibrated values.
PUT stops being qualitative and becomes predictive.
"""

import asyncio
import json
import logging
import math
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("wave.put_calibrator")

CALIBRATION_DB = Path(__file__).parent.parent / "memory" / "put_calibration.json"
INTERACTION_LOG = Path(__file__).parent.parent / "memory" / "put_interactions.jsonl"


def _load_calibration() -> dict:
    if CALIBRATION_DB.exists():
        try:
            cal = json.loads(CALIBRATION_DB.read_text())
            # Back-fill verticals if older calibration file predates §13.2
            if "verticals" not in cal:
                cal["verticals"] = {}
            return cal
        except Exception:
            pass
    return {
        "global": {
            "alpha": {"mean": 1.0, "std": 0.2, "samples": 0},
            "beta": {"mean": 1.2, "std": 0.2, "samples": 0},
            "gamma": {"mean": 0.8, "std": 0.2, "samples": 0},
            "delta": {"mean": 0.6, "std": 0.2, "samples": 0},
            "epsilon": {"mean": 0.5, "std": 0.2, "samples": 0},
        },
        "archetypes": {},
        "verticals": {},
        "total_interactions": 0,
        "accuracy_history": [],
    }


def _save_calibration(cal: dict):
    CALIBRATION_DB.parent.mkdir(parents=True, exist_ok=True)
    CALIBRATION_DB.write_text(json.dumps(cal, indent=2))


def _log_interaction(entry: dict):
    INTERACTION_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry["timestamp"] = datetime.utcnow().isoformat()
    with open(INTERACTION_LOG, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


# ── Core PUT Equations ────────────────────────────────────────

def compute_U(A, F, k, S, w, Sigma, tau, kappa, Phi, coeffs,
              R_net=0.0, use_interactions=True):
    """Compute Psychic Utility with given coefficients.

    PUT 2.3: includes cross-variable interactions + R_net.
    delta*tau*kappa is NEGATIVE — vulnerability reduces U (Axiom 4).

    Set use_interactions=False for raw U (useful for coefficient isolation in calibration).
    """
    alpha = coeffs["alpha"]
    beta = coeffs["beta"]
    gamma = coeffs["gamma"]
    delta = coeffs["delta"]
    epsilon = coeffs["epsilon"]

    if use_interactions:
        A_eff, F_eff, w_eff, Phi_eff = _apply_cross_interactions(A, F, k, S, w, Sigma, tau, kappa, Phi)
    else:
        A_eff, F_eff, w_eff, Phi_eff = A, F, w, Phi

    Fk = F_eff * (1 - k)  # Shadow-adjusted effective fear
    U = (alpha * A_eff * (1 - Fk)
         - beta * Fk * (1 - S)
         + gamma * S * (1 - w_eff) * Sigma
         - delta * tau * kappa    # NEGATIVE: vulnerability reduces U
         - epsilon * Phi_eff
         + R_net)
    return max(-2.0, min(3.0, U))


# ── Cross-variable interactions (PUT 2.3) ────────────────────
# Aligned with put_engine.py constants

LAMBDA_FA = 3.0       # F→A paralysis
FA_THRESHOLD = 0.65   # Effective fear above this triggers A suppression
LAMBDA_WF = 0.3       # w→F amplification
LAMBDA_KPHI = 0.5     # k→Φ breeding
LAMBDA_SIGMA_W = 0.3  # Σ→w damping
LAMBDA_KA = 0.4       # k→A delayed suppression
KA_THRESHOLD = 0.55   # Shadow above this triggers delayed A suppression

# Hysteresis thresholds (aligned with put_engine.py)
U_CRIT_DOWN = 0.3
U_CRIT_UP = 0.5

# ── Vertical-Specific Coefficient Priors (PUT v2.3 §13.2) ────
# Decision dynamics differ by industry vertical.
# E-commerce: impulsive, low loss aversion → high alpha, low beta
# B2B SaaS: deliberate, high loss aversion → low alpha, high beta
# std=0.15 everywhere — tighter than global (0.2) because priors are theory-informed

VERTICAL_PRIORS: dict = {
    "ecommerce": {
        # Fast decisions, low loss aversion, high impulse
        "alpha": {"mean": 1.3, "std": 0.15, "samples": 0},
        "beta":  {"mean": 0.8, "std": 0.15, "samples": 0},
        "gamma": {"mean": 0.7, "std": 0.15, "samples": 0},
        "delta": {"mean": 0.5, "std": 0.15, "samples": 0},
        "epsilon": {"mean": 0.4, "std": 0.15, "samples": 0},
    },
    "b2b_saas": {
        # Long cycles, committee decisions, high loss aversion
        "alpha": {"mean": 0.8, "std": 0.15, "samples": 0},
        "beta":  {"mean": 1.5, "std": 0.15, "samples": 0},
        "gamma": {"mean": 0.9, "std": 0.15, "samples": 0},
        "delta": {"mean": 0.7, "std": 0.15, "samples": 0},
        "epsilon": {"mean": 0.6, "std": 0.15, "samples": 0},
    },
    "services": {
        # Relationship-driven, balanced dynamics
        "alpha": {"mean": 1.0, "std": 0.15, "samples": 0},
        "beta":  {"mean": 1.1, "std": 0.15, "samples": 0},
        "gamma": {"mean": 0.8, "std": 0.15, "samples": 0},
        "delta": {"mean": 0.6, "std": 0.15, "samples": 0},
        "epsilon": {"mean": 0.5, "std": 0.15, "samples": 0},
    },
    "marketplace": {
        # Platform dynamics: moderate impulse, trust-sensitive
        "alpha": {"mean": 1.1, "std": 0.15, "samples": 0},
        "beta":  {"mean": 1.0, "std": 0.15, "samples": 0},
        "gamma": {"mean": 0.7, "std": 0.15, "samples": 0},
        "delta": {"mean": 0.5, "std": 0.15, "samples": 0},
        "epsilon": {"mean": 0.4, "std": 0.15, "samples": 0},
    },
    "enterprise": {
        # Risk-averse, procurement-driven, high loss aversion
        "alpha": {"mean": 0.7, "std": 0.15, "samples": 0},
        "beta":  {"mean": 1.6, "std": 0.15, "samples": 0},
        "gamma": {"mean": 1.0, "std": 0.15, "samples": 0},
        "delta": {"mean": 0.8, "std": 0.15, "samples": 0},
        "epsilon": {"mean": 0.7, "std": 0.15, "samples": 0},
    },
    "startup": {
        # High ambition, faster decisions, lower fear threshold
        "alpha": {"mean": 1.4, "std": 0.15, "samples": 0},
        "beta":  {"mean": 0.9, "std": 0.15, "samples": 0},
        "gamma": {"mean": 0.6, "std": 0.15, "samples": 0},
        "delta": {"mean": 0.5, "std": 0.15, "samples": 0},
        "epsilon": {"mean": 0.5, "std": 0.15, "samples": 0},
    },
}


def _apply_cross_interactions(A, F, k, S, w, Sigma, tau, kappa, Phi):
    """Apply second-order cross-variable interactions.
    Returns (A_eff, F_eff, w_eff, Phi_eff).

    Interactions (PUT 2.3):
      1. w→F amplification: pain breeds fear
      2. Σ→w damping: stability reduces pain
      3. k→Φ breeding: denial feeds delusion
      4. F→A paralysis: effective fear suppresses ambition
      5. k→A delayed suppression: chronic denial collapses agency
    """
    # 1. w→F amplification (apply first — feeds into F→A)
    F_eff = min(1.0, F * (1.0 + LAMBDA_WF * w))
    # 2. Σ→w damping
    w_eff = w * (1.0 - LAMBDA_SIGMA_W * Sigma)
    # 3. k→Φ breeding
    Phi_eff = min(2.0, Phi * (1.0 + LAMBDA_KPHI * k))
    # 4. F→A paralysis (uses F_eff, not raw F)
    Fk_eff = F_eff * (1.0 - k)
    A_eff = A
    if Fk_eff > FA_THRESHOLD:
        suppression = min(1.0, (Fk_eff - FA_THRESHOLD) * LAMBDA_FA)
        A_eff = A * (1.0 - suppression)
    # 5. k→A delayed suppression
    if k > KA_THRESHOLD:
        k_suppression = min(0.5, (k - KA_THRESHOLD) * LAMBDA_KA)
        A_eff = A_eff * (1.0 - k_suppression)
    return (
        max(0.0, A_eff),
        max(0.0, min(1.0, F_eff)),
        max(0.0, w_eff),
        max(0.0, min(2.0, Phi_eff)),
    )


def _sigmoid(x, k_s=5.0):
    """Standard sigmoid for FP decay."""
    return 1.0 / (1.0 + math.exp(k_s * x))


def compute_FP(R, kappa, tau, Phi, U, U_crit=0.3, k_fp=5.0):
    """Compute Fracture Potential using sigmoid formulation with hysteresis support.

    PUT 2.3: FP = (1-R)*(kappa+tau+Phi_eff) * sigmoid(-(U - U_crit))
    Smooth decay: FP -> 0 when U >> U_crit, FP -> max when U << U_crit.
    No pathological behavior at any U value.

    Pass U_crit=U_CRIT_UP (0.5) for entities already in crisis.
    """
    raw_FP = (1 - R) * (kappa + tau + Phi) * _sigmoid(U - U_crit, k_s=k_fp)
    return raw_FP


def compute_Omega(U, U_crit=0.3, k_omega=1.0):
    """Compute Desperation Factor."""
    return 1 + math.exp(-k_omega * (U - U_crit))


def compute_Phi(E_ext, E_int):
    """Compute Self-Delusion Factor."""
    return (E_ext + E_int) / (1 + abs(E_ext - E_int))


# ── Monte Carlo Simulation ────────────────────────────────────

def _sample_coefficients(cal: dict, archetype: str = None, n: int = 50,
                          vertical: str = None) -> List[dict]:
    """Generate N coefficient sets by sampling from current distributions.

    Fallback chain (most specific → most general):
      vertical (if calibrated) → vertical prior → archetype → global
    """
    # 1. Try calibrated vertical data
    if vertical and vertical in cal.get("verticals", {}):
        source = cal["verticals"][vertical]
    # 2. Fall back to vertical prior (uncalibrated but theory-informed)
    elif vertical and vertical in VERTICAL_PRIORS:
        source = VERTICAL_PRIORS[vertical]
    # 3. Fall back to archetype
    elif archetype and archetype in cal.get("archetypes", {}):
        source = cal["archetypes"][archetype]
    # 4. Global
    else:
        source = cal.get("global", {})

    samples = []
    for _ in range(n):
        sample = {}
        for coeff in ["alpha", "beta", "gamma", "delta", "epsilon"]:
            dist = source.get(coeff, {"mean": 0.5, "std": 0.2})
            val = random.gauss(dist["mean"], dist["std"])
            sample[coeff] = max(0.01, min(2.0, val))  # Clamp [0.01, 2.0] (beta can exceed 1)
        samples.append(sample)
    return samples


async def simulate_prospect(params: Dict[str, Any]) -> Dict:
    """Simulate how a prospect will respond using Monte Carlo PUT analysis.

    Input: prospect's PUT variables (A, F, k, S, w, Sigma, tau, kappa, Phi)
    Output: predicted response distribution, recommended approach, confidence
    """
    # Extract prospect variables
    A = float(params.get("A", 0.5))
    F = float(params.get("F", 0.5))
    k = float(params.get("k", 0.3))
    S = float(params.get("S", 0.5))
    w = float(params.get("w", 0.3))
    Sigma = float(params.get("Sigma", 0.5))
    tau = float(params.get("tau", 0.3))
    kappa = float(params.get("kappa", 0.3))
    E_ext = float(params.get("E_ext", 0.5))
    E_int = float(params.get("E_int", 0.5))
    R = float(params.get("R", 0.5))  # Resilience
    archetype = params.get("archetype", None)
    prospect_name = params.get("name", "unknown")

    vertical = params.get("vertical", None)
    Phi = compute_Phi(E_ext, E_int)

    cal = _load_calibration()
    samples = _sample_coefficients(cal, archetype, n=100, vertical=vertical)

    results = []
    for coeffs in samples:
        U = compute_U(A, F, k, S, w, Sigma, tau, kappa, Phi, coeffs)
        FP = compute_FP(R, kappa, tau, Phi, U)
        Omega = compute_Omega(U)

        # Predict response category based on U, FP, Omega
        if U > 0.6:
            response = "receptive"  # High utility — open to offers
        elif FP > 2.0:
            response = "desperate"  # High fracture — will act under pressure
        elif Omega > 1.5:
            response = "urgent"  # Desperation spiking — time-sensitive
        elif U < 0.2:
            response = "resistant"  # Low utility — hard sell
        else:
            response = "neutral"  # Could go either way

        results.append({
            "U": round(U, 4),
            "FP": round(FP, 4),
            "Omega": round(Omega, 4),
            "response": response,
            "coeffs": coeffs,
        })

    # Aggregate predictions
    response_counts = {}
    for r in results:
        resp = r["response"]
        response_counts[resp] = response_counts.get(resp, 0) + 1

    dominant = max(response_counts, key=response_counts.get)
    confidence = response_counts[dominant] / len(results)

    # Average U, FP, Omega
    avg_U = sum(r["U"] for r in results) / len(results)
    avg_FP = sum(r["FP"] for r in results) / len(results)
    avg_Omega = sum(r["Omega"] for r in results) / len(results)

    # Recommend approach based on prediction
    approach_map = {
        "receptive": "Direct value proposition. They're open — show capability and price.",
        "desperate": "Emphasize urgency and immediate relief. They need a solution NOW.",
        "urgent": "Time-pressure framing. The window is closing. Act fast.",
        "resistant": "Long-game. Build relationship first. Don't pitch yet.",
        "neutral": "Lead with insight, not product. Demonstrate expertise.",
    }

    return {
        "success": True,
        "data": {
            "prospect": prospect_name,
            "variables": {"A": A, "F": F, "k": k, "S": S, "w": w, "Phi": round(Phi, 4)},
            "predictions": {
                "dominant_response": dominant,
                "confidence": round(confidence, 2),
                "distribution": response_counts,
                "avg_U": round(avg_U, 4),
                "avg_FP": round(avg_FP, 4),
                "avg_Omega": round(avg_Omega, 4),
            },
            "recommendation": approach_map.get(dominant, "Analyze further."),
            "simulations_run": len(results),
        },
        "message": (
            f"Prospect '{prospect_name}': {dominant} ({confidence:.0%} confidence). "
            f"U={avg_U:.2f} FP={avg_FP:.2f} Omega={avg_Omega:.2f}. "
            f"Approach: {approach_map.get(dominant, 'analyze')[:80]}"
        ),
    }


async def record_outcome(params: Dict[str, Any]) -> Dict:
    """Record the actual outcome of an interaction for calibration.

    Compare what happened with what was predicted.
    Update coefficient distributions accordingly.
    """
    prospect_name = params.get("name", "unknown")
    predicted_response = params.get("predicted", "neutral")
    actual_response = params.get("actual", "neutral")  # receptive|desperate|urgent|resistant|neutral
    archetype = params.get("archetype", None)
    vertical = params.get("vertical", None)

    # PUT variables used in the prediction
    variables = params.get("variables", {})
    A = float(variables.get("A", 0.5))
    F = float(variables.get("F", 0.5))
    k = float(variables.get("k", 0.3))
    S = float(variables.get("S", 0.5))
    w = float(variables.get("w", 0.3))
    Sigma = float(variables.get("Sigma", 0.5))
    tau = float(variables.get("tau", 0.3))
    kappa = float(variables.get("kappa", 0.3))
    E_ext = float(variables.get("E_ext", 0.5))
    E_int = float(variables.get("E_int", 0.5))
    R = float(variables.get("R", 0.5))
    Phi = compute_Phi(E_ext, E_int)

    correct = predicted_response == actual_response

    cal = _load_calibration()

    # Find which coefficient sets predicted correctly
    samples = _sample_coefficients(cal, archetype, n=200, vertical=vertical)
    correct_coeffs = []

    for coeffs in samples:
        U = compute_U(A, F, k, S, w, Sigma, tau, kappa, Phi, coeffs)
        FP = compute_FP(R, kappa, tau, Phi, U)
        Omega = compute_Omega(U)

        # Same prediction logic as simulate
        if U > 0.6:
            sim_response = "receptive"
        elif FP > 2.0:
            sim_response = "desperate"
        elif Omega > 1.5:
            sim_response = "urgent"
        elif U < 0.2:
            sim_response = "resistant"
        else:
            sim_response = "neutral"

        if sim_response == actual_response:
            correct_coeffs.append(coeffs)

    def _bayesian_update_target(target: dict, correct_coeffs: list) -> dict:
        """Update a coefficient distribution dict in-place using correct coefficient samples."""
        for coeff in ["alpha", "beta", "gamma", "delta", "epsilon"]:
            values = [c[coeff] for c in correct_coeffs]
            new_mean = sum(values) / len(values)
            new_std = max(0.05, (sum((v - new_mean) ** 2 for v in values) / len(values)) ** 0.5)
            old = target.get(coeff, {"mean": 0.5, "std": 0.2, "samples": 0})
            n_samples = old.get("samples", 0)
            weight = min(n_samples / (n_samples + len(correct_coeffs)), 0.9)
            target[coeff] = {
                "mean": round(weight * old["mean"] + (1 - weight) * new_mean, 4),
                "std": round(weight * old["std"] + (1 - weight) * new_std, 4),
                "samples": n_samples + 1,
            }
        return target

    if correct_coeffs:
        # Update global
        cal["global"] = _bayesian_update_target(cal.get("global", {}), correct_coeffs)

        # Update archetype if specified
        if archetype:
            arch_target = cal.setdefault("archetypes", {}).get(archetype, {})
            cal["archetypes"][archetype] = _bayesian_update_target(arch_target, correct_coeffs)

        # Update vertical if specified — starts from prior if not yet calibrated
        if vertical:
            vert_target = cal.setdefault("verticals", {}).get(
                vertical,
                {k: dict(v) for k, v in VERTICAL_PRIORS.get(vertical, {}).items()}
            )
            cal["verticals"][vertical] = _bayesian_update_target(vert_target, correct_coeffs)

    cal["total_interactions"] = cal.get("total_interactions", 0) + 1
    cal["accuracy_history"] = (cal.get("accuracy_history", []) + [1 if correct else 0])[-100:]

    _save_calibration(cal)

    # Log the interaction
    _log_interaction({
        "prospect": prospect_name,
        "predicted": predicted_response,
        "actual": actual_response,
        "correct": correct,
        "archetype": archetype,
        "vertical": vertical,
        "variables": variables,
        "correct_coefficients_found": len(correct_coeffs),
    })

    accuracy = sum(cal["accuracy_history"]) / len(cal["accuracy_history"]) if cal["accuracy_history"] else 0

    return {
        "success": True,
        "data": {
            "prospect": prospect_name,
            "predicted": predicted_response,
            "actual": actual_response,
            "correct": correct,
            "coefficients_updated": len(correct_coeffs) > 0,
            "total_interactions": cal["total_interactions"],
            "running_accuracy": round(accuracy, 2),
        },
        "message": (
            f"{'CORRECT' if correct else 'WRONG'}: predicted {predicted_response}, actual {actual_response}. "
            f"Accuracy: {accuracy:.0%} over {len(cal['accuracy_history'])} interactions. "
            f"Coefficients {'updated' if correct_coeffs else 'unchanged'}."
        ),
    }


async def calibration_status(params: Dict[str, Any]) -> Dict:
    """Current calibration state — coefficients, accuracy, sample count."""
    cal = _load_calibration()
    acc = cal.get("accuracy_history", [])
    accuracy = sum(acc) / len(acc) if acc else 0

    return {
        "success": True,
        "data": {
            "global_coefficients": cal.get("global", {}),
            "archetypes": list(cal.get("archetypes", {}).keys()),
            "verticals": list(cal.get("verticals", {}).keys()),
            "total_interactions": cal.get("total_interactions", 0),
            "accuracy": round(accuracy, 2),
            "history_size": len(acc),
            "convergence": "calibrating" if len(acc) < 50 else ("converged" if accuracy > 0.7 else "needs_more_data"),
        },
        "message": (
            f"PUT Calibration: {cal.get('total_interactions', 0)} interactions, "
            f"{accuracy:.0%} accuracy, {len(cal.get('archetypes', {}))} archetypes, "
            f"{len(cal.get('verticals', {}))} verticals calibrated. "
            f"Status: {'converged' if len(acc) >= 50 and accuracy > 0.7 else 'calibrating'}"
        ),
    }


async def vertical_calibration_status(params: Dict[str, Any]) -> Dict:
    """Show calibration state for all verticals.

    Returns current coefficient estimates per vertical, how many interactions
    have been recorded, and whether they've diverged from the theoretical prior.
    """
    cal = _load_calibration()
    calibrated = cal.get("verticals", {})

    vertical_report = {}
    for vname, prior in VERTICAL_PRIORS.items():
        live = calibrated.get(vname)
        if live:
            samples = live.get("alpha", {}).get("samples", 0)
            # Drift: mean absolute difference from prior across all coefficients
            drift = round(
                sum(
                    abs(live.get(c, {}).get("mean", 0) - prior[c]["mean"])
                    for c in ["alpha", "beta", "gamma", "delta", "epsilon"]
                ) / 5,
                4,
            )
            vertical_report[vname] = {
                "status": "calibrating" if samples < 20 else "converged",
                "interactions": samples,
                "drift_from_prior": drift,
                "coefficients": {c: live.get(c, {}) for c in ["alpha", "beta", "gamma", "delta", "epsilon"]},
            }
        else:
            vertical_report[vname] = {
                "status": "prior_only",
                "interactions": 0,
                "drift_from_prior": 0.0,
                "coefficients": {c: dict(v) for c, v in prior.items()},
            }

    calibrated_count = sum(1 for v in vertical_report.values() if v["status"] != "prior_only")

    return {
        "success": True,
        "data": {
            "verticals": vertical_report,
            "calibrated_verticals": calibrated_count,
            "prior_only_verticals": len(VERTICAL_PRIORS) - calibrated_count,
        },
        "message": (
            f"Verticals: {calibrated_count}/{len(VERTICAL_PRIORS)} calibrated from real data. "
            + ", ".join(
                f"{v}: {r['interactions']} interactions"
                for v, r in vertical_report.items()
                if r["interactions"] > 0
            ) or "No vertical interactions recorded yet."
        ),
    }


async def predict_conversion_time(params: Dict[str, Any]) -> Dict:
    """Temporal prediction: WHEN will this prospect reach ignition (conversion moment)?

    Uses RK4 ODE integration (put_engine.solve_put_trajectory) for accurate numerical
    trajectory. Monte Carlo over calibrated coefficient distributions gives a ±N day
    confidence interval around the deterministic estimate.

    Answers the question: "In how many days will this prospect hit ignition threshold?"

    Args (all PUT variables + optional):
        days: simulation horizon in days (default 90)
        archetype: prospect archetype for coefficient sampling
        vertical: industry vertical (ecommerce|b2b_saas|services|marketplace|enterprise|startup)
        in_crisis: whether prospect is already in crisis state (default False)
        trigger_schedule: list of daily trigger intensities [0-1]
        threat_schedule: list of daily threat intensities [0-1]

    Returns:
        ignition_day: best estimate (RK4 deterministic)
        confidence_interval: [low, high] in days
        probability_30d: probability of ignition within 30 days
        trajectory_summary: first 5 points of the RK4 trajectory
    """
    try:
        from skills.put_engine import predict_ignition_time as _pit, compute_U as _engine_cU
    except ImportError:
        try:
            from put_engine import predict_ignition_time as _pit, compute_U as _engine_cU
        except ImportError:
            return {
                "success": False,
                "message": "put_engine not available — run from openclaw-skill/skills/ directory",
            }

    # Extract PUT vector
    put = {
        "A":      float(params.get("A", 0.5)),
        "F":      float(params.get("F", 0.5)),
        "k":      float(params.get("k", 0.3)),
        "S":      float(params.get("S", 0.5)),
        "w":      float(params.get("w", 0.3)),
        "Sigma":  float(params.get("Sigma", 0.5)),
        "tau":    float(params.get("tau", 0.3)),
        "kappa":  float(params.get("kappa", 0.3)),
        "Phi":    float(params.get("Phi", 0.5)),
        "R_net":  float(params.get("R_net", 0.0)),
    }
    steps = int(params.get("days", 90))
    archetype = params.get("archetype")
    vertical = params.get("vertical")
    in_crisis = bool(params.get("in_crisis", False))
    trigger_schedule = params.get("trigger_schedule")
    threat_schedule = params.get("threat_schedule")
    prospect_name = params.get("name", "unknown")

    entity_state = {"in_crisis": in_crisis, "A_prev": put["A"]}

    # ── 1. Deterministic RK4 trajectory ──────────────────────
    base = _pit(
        put, steps=steps,
        trigger_schedule=trigger_schedule,
        threat_schedule=threat_schedule,
        entity_state=entity_state,
    )

    # ── 2. Monte Carlo: coefficient uncertainty → U uncertainty ──
    # Sample N coefficient sets from calibrated/prior distributions
    cal = _load_calibration()
    mc_samples = _sample_coefficients(cal, archetype, n=200, vertical=vertical)

    u_values = [
        _engine_cU(
            put["A"], put["F"], put["k"], put["S"], put["w"],
            put["Sigma"], put["tau"], put["kappa"], put["Phi"], put["R_net"],
            alpha=c["alpha"], beta=c["beta"], gamma=c["gamma"],
            delta=c["delta"], epsilon=c["epsilon"],
        )
        for c in mc_samples
    ]
    u_mean = sum(u_values) / len(u_values)
    u_std = (sum((u - u_mean) ** 2 for u in u_values) / len(u_values)) ** 0.5

    # Translate U uncertainty to timeline uncertainty.
    # Empirical scaling: the endogenous ODE variables change ~0.01-0.02/day.
    # A U offset of 0.1 shifts ignition by ~7 days (dU/dt ≈ 0.014/day baseline).
    # => uncertainty_days ≈ u_std / 0.014
    DAYS_PER_U_STD = 70.0
    uncertainty_days = max(1, int(u_std * DAYS_PER_U_STD))

    # ── 3. Build output ──────────────────────────────────────
    ignition_day = base.get("days_to_ignition")

    if ignition_day is not None:
        ci_low = max(1, ignition_day - uncertainty_days)
        ci_high = ignition_day + uncertainty_days
        forecast = (
            f"Prospect '{prospect_name}': ignition in ~{ignition_day} days "
            f"[CI: {ci_low}–{ci_high}]. "
            f"P(30d) = {base['ignition_probability_30d']:.0%}."
        )
    else:
        ci_low = ci_high = None
        forecast = (
            f"Prospect '{prospect_name}': no ignition predicted within {steps} days. "
            f"Min U = {base.get('min_U', '?'):.3f}. "
            f"Increase triggers or re-assess PUT vector."
        )

    return {
        "success": True,
        "data": {
            "prospect": prospect_name,
            "ignition_day": ignition_day,
            "confidence_interval": [ci_low, ci_high] if ci_low is not None else None,
            "uncertainty_days": uncertainty_days,
            "probability_30d": base.get("ignition_probability_30d"),
            "current_U_mean": round(u_mean, 4),
            "current_U_std": round(u_std, 4),
            "vertical": vertical or "global",
            "archetype": archetype or "global",
            "min_U_in_trajectory": base.get("min_U"),
            "crisis_steps": base.get("crisis_steps"),
            "simulation_days": steps,
            "trajectory_summary": base.get("trajectory_summary", [])[:5],
            "final_state": base.get("final_state"),
        },
        "message": forecast,
    }


async def compute_put_full(params: Dict[str, Any]) -> Dict:
    """Compute all PUT variables for a target using calibrated coefficients."""
    A = float(params.get("A", 0.5))
    F = float(params.get("F", 0.5))
    k = float(params.get("k", 0.3))
    S = float(params.get("S", 0.5))
    w = float(params.get("w", 0.3))
    Sigma = float(params.get("Sigma", 0.5))
    tau = float(params.get("tau", 0.3))
    kappa = float(params.get("kappa", 0.3))
    E_ext = float(params.get("E_ext", 0.5))
    E_int = float(params.get("E_int", 0.5))
    R = float(params.get("R", 0.5))

    cal = _load_calibration()
    coeffs = {c: cal["global"][c]["mean"] for c in ["alpha", "beta", "gamma", "delta", "epsilon"]}

    Phi = compute_Phi(E_ext, E_int)
    Fk = F * (1 - k)
    U = compute_U(A, F, k, S, w, Sigma, tau, kappa, Phi, coeffs)
    FP = compute_FP(R, kappa, tau, Phi, U)
    Omega = compute_Omega(U)

    return {
        "success": True,
        "data": {
            "inputs": {"A": A, "F": F, "k": k, "S": S, "w": w, "Sigma": Sigma, "tau": tau, "kappa": kappa},
            "computed": {
                "Fk_shadow_fear": round(Fk, 4),
                "Phi_self_delusion": round(Phi, 4),
                "U_psychic_utility": round(U, 4),
                "FP_fracture_potential": round(FP, 4),
                "Omega_desperation": round(Omega, 4),
            },
            "coefficients_used": coeffs,
            "calibration_samples": cal["global"]["alpha"]["samples"],
        },
        "message": f"U={U:.3f} FP={FP:.3f} Omega={Omega:.3f} Phi={Phi:.3f} (calibrated on {cal['global']['alpha']['samples']} samples)",
    }


# ── Archetype Discovery via Clustering (PUT 2.4) ────────────

def _euclidean_distance(a: list, b: list) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def _kmeans(vectors: list, k: int = 7, max_iter: int = 100, seed: int = 42) -> dict:
    """Pure-Python K-Means clustering. No sklearn dependency.

    Args:
        vectors: list of [A, F, k, S, w, Sigma, tau, kappa, Phi] lists
        k: number of clusters
        max_iter: maximum iterations

    Returns:
        {"centroids": [...], "labels": [...], "inertia": float}
    """
    random.seed(seed)
    n = len(vectors)
    if n < k:
        k = n

    # K-Means++ initialization
    centroids = [list(vectors[random.randint(0, n - 1)])]
    for _ in range(k - 1):
        dists = []
        for v in vectors:
            min_d = min(_euclidean_distance(v, c) for c in centroids)
            dists.append(min_d ** 2)
        total = sum(dists)
        if total == 0:
            centroids.append(list(vectors[random.randint(0, n - 1)]))
            continue
        probs = [d / total for d in dists]
        cumulative = 0
        r = random.random()
        for i, p in enumerate(probs):
            cumulative += p
            if cumulative >= r:
                centroids.append(list(vectors[i]))
                break

    dim = len(vectors[0])
    labels = [0] * n

    for _iteration in range(max_iter):
        # Assignment step
        new_labels = []
        for v in vectors:
            dists = [_euclidean_distance(v, c) for c in centroids]
            new_labels.append(dists.index(min(dists)))

        if new_labels == labels:
            break  # Converged
        labels = new_labels

        # Update step
        for ci in range(k):
            members = [vectors[i] for i in range(n) if labels[i] == ci]
            if members:
                centroids[ci] = [sum(m[d] for m in members) / len(members) for d in range(dim)]

    inertia = sum(
        _euclidean_distance(vectors[i], centroids[labels[i]]) ** 2
        for i in range(n)
    )

    return {"centroids": centroids, "labels": labels, "inertia": inertia}


def _find_optimal_k(vectors: list, max_k: int = 10) -> int:
    """Elbow method: find k where inertia improvement drops below threshold."""
    if len(vectors) < 3:
        return len(vectors)

    max_k = min(max_k, len(vectors))
    inertias = []
    for k in range(2, max_k + 1):
        result = _kmeans(vectors, k=k)
        inertias.append(result["inertia"])

    if len(inertias) < 2:
        return 2

    # Find elbow: biggest drop in rate of improvement
    improvements = [inertias[i] - inertias[i + 1] for i in range(len(inertias) - 1)]
    if not improvements or max(improvements) == 0:
        return 3

    # Second derivative (rate of change of improvement)
    for i in range(len(improvements) - 1):
        if improvements[i + 1] < improvements[i] * 0.3:  # 70% drop in improvement
            return i + 3  # offset by starting k=2

    return min(7, max_k)  # Default to 7 (matches theoretical archetypes)


async def discover_archetypes(params: Dict[str, Any]) -> Dict:
    """Discover empirical archetypes from accumulated PUT interaction data.

    Clusters all recorded prospect PUT vectors using K-Means.
    Compares discovered clusters against the 7 theoretical archetypes.
    Returns: new archetypes, their centroids, and overlap analysis with theory.

    This is the bridge between theoretical PUT and empirical validation.
    """
    # Collect all PUT vectors from interaction log
    vectors = []
    names = []

    if INTERACTION_LOG.exists():
        with open(INTERACTION_LOG) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    v = entry.get("variables", {})
                    if v:
                        vec = [
                            float(v.get("A", 0.5)), float(v.get("F", 0.5)),
                            float(v.get("k", 0.3)), float(v.get("S", 0.5)),
                            float(v.get("w", 0.3)), float(v.get("Sigma", 0.5)),
                            float(v.get("tau", 0.3)), float(v.get("kappa", 0.3)),
                            float(v.get("E_ext", 0.5)),
                        ]
                        vectors.append(vec)
                        names.append(entry.get("prospect", "unknown"))
                except Exception:
                    continue

    # Also pull from stakeholders if available
    stakeholders_path = Path(__file__).parent.parent / "memory" / "stakeholders.json"
    if stakeholders_path.exists():
        try:
            stakeholders = json.loads(stakeholders_path.read_text())
            for eid, entity in stakeholders.items():
                p = entity.get("put", {})
                if p and any(p.get(v, 0) != 0.5 for v in ["A", "F", "k"]):
                    vec = [
                        float(p.get("A", 0.5)), float(p.get("F", 0.5)),
                        float(p.get("k", 0.3)), float(p.get("S", 0.5)),
                        float(p.get("w", 0.3)), float(p.get("Sigma", 0.5)),
                        float(p.get("tau", 0.3)), float(p.get("kappa", 0.3)),
                        float(p.get("Phi", 0.5)),
                    ]
                    vectors.append(vec)
                    names.append(eid)
        except Exception:
            pass

    if len(vectors) < 5:
        return {
            "success": True,
            "data": {
                "status": "insufficient_data",
                "vectors_found": len(vectors),
                "minimum_required": 5,
            },
            "message": (
                f"Only {len(vectors)} PUT vectors available. Need at least 5 for clustering. "
                f"Record more interactions via put_record_outcome to enable archetype discovery."
            ),
        }

    # Find optimal number of clusters
    max_k = min(10, len(vectors) // 2)
    optimal_k = _find_optimal_k(vectors, max_k=max(max_k, 3))
    result = _kmeans(vectors, k=optimal_k)

    # Theoretical archetype centroids (9 dimensions: A, F, k, S, w, Sigma, tau, kappa, Phi)
    theoretical = {
        "builder":       [0.9, 0.2, 0.1, 0.5, 0.3, 0.7, 0.2, 0.2, 0.3],
        "guardian":      [0.3, 0.8, 0.2, 0.6, 0.4, 0.6, 0.3, 0.4, 0.4],
        "politician":    [0.6, 0.4, 0.3, 0.8, 0.2, 0.6, 0.4, 0.3, 0.5],
        "sufferer":      [0.5, 0.5, 0.2, 0.3, 0.9, 0.4, 0.3, 0.5, 0.4],
        "denier":        [0.4, 0.9, 0.8, 0.5, 0.6, 0.4, 0.4, 0.3, 0.7],
        "perfectionist": [0.6, 0.5, 0.3, 0.6, 0.5, 0.6, 0.7, 0.7, 0.5],
        "visionary":     [0.9, 0.1, 0.1, 0.4, 0.3, 0.5, 0.2, 0.2, 0.8],
    }

    # Map discovered clusters to nearest theoretical archetype
    var_names = ["A", "F", "k", "S", "w", "Sigma", "tau", "kappa", "Phi"]
    discovered_archetypes = []
    novel_count = 0

    for ci, centroid in enumerate(result["centroids"]):
        cluster_members = [names[i] for i in range(len(vectors)) if result["labels"][i] == ci]
        cluster_size = len(cluster_members)

        # Distance to each theoretical archetype
        distances = {
            name: round(_euclidean_distance(centroid, tc), 3)
            for name, tc in theoretical.items()
        }
        nearest = min(distances, key=distances.get)
        nearest_dist = distances[nearest]

        # If distance > 0.8, this is a NOVEL archetype not in theory
        is_novel = nearest_dist > 0.8
        if is_novel:
            novel_count += 1
            label = f"empirical_{novel_count}"
        else:
            label = nearest

        centroid_dict = {var_names[i]: round(centroid[i], 3) for i in range(len(var_names))}

        discovered_archetypes.append({
            "cluster_id": ci,
            "label": label,
            "is_novel": is_novel,
            "nearest_theoretical": nearest,
            "distance_to_nearest": nearest_dist,
            "centroid": centroid_dict,
            "size": cluster_size,
            "members": cluster_members[:10],  # Cap at 10 for readability
        })

    # Save discovered archetypes to calibration DB
    cal = _load_calibration()
    cal["discovered_archetypes"] = {
        "timestamp": datetime.utcnow().isoformat(),
        "n_vectors": len(vectors),
        "optimal_k": optimal_k,
        "inertia": round(result["inertia"], 4),
        "clusters": discovered_archetypes,
    }
    _save_calibration(cal)

    # Summary
    novel_names = [a["label"] for a in discovered_archetypes if a["is_novel"]]
    confirmed = [a["nearest_theoretical"] for a in discovered_archetypes if not a["is_novel"]]
    confirmed_unique = list(set(confirmed))
    missing = [t for t in theoretical if t not in confirmed_unique]

    return {
        "success": True,
        "data": {
            "n_vectors": len(vectors),
            "optimal_k": optimal_k,
            "inertia": round(result["inertia"], 4),
            "discovered_archetypes": discovered_archetypes,
            "confirmed_theoretical": confirmed_unique,
            "missing_theoretical": missing,
            "novel_archetypes": novel_names,
        },
        "message": (
            f"Discovered {optimal_k} clusters from {len(vectors)} vectors. "
            f"Confirmed: {', '.join(confirmed_unique) if confirmed_unique else 'none'}. "
            f"Novel: {', '.join(novel_names) if novel_names else 'none'}. "
            f"Missing: {', '.join(missing) if missing else 'all accounted for'}."
        ),
    }


TOOLS = [
    {
        "name": "put_simulate",
        "description": "Monte Carlo simulation of prospect response using PUT. Runs 100 simulations with varied coefficients. Returns dominant prediction + confidence + recommended approach.",
        "handler": simulate_prospect,
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Prospect name"},
                "A": {"type": "number", "description": "Ambition 0-1"},
                "F": {"type": "number", "description": "Fear 0-1"},
                "k": {"type": "number", "description": "Shadow coefficient 0-1"},
                "S": {"type": "number", "description": "Status 0-1"},
                "w": {"type": "number", "description": "Wound weight 0-1"},
                "Sigma": {"type": "number", "description": "Ecosystem stability 0-1"},
                "tau": {"type": "number", "description": "Treachery 0-1"},
                "kappa": {"type": "number", "description": "Guilt transfer 0-1"},
                "E_ext": {"type": "number", "description": "External feedback 0-1"},
                "E_int": {"type": "number", "description": "Internal feedback 0-1"},
                "R": {"type": "number", "description": "Resilience 0-1"},
                "archetype": {"type": "string", "description": "Prospect archetype for targeted coefficients"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "put_record_outcome",
        "description": "Record actual outcome vs prediction. Feeds calibration loop. Call after every outreach/interaction to improve accuracy.",
        "handler": record_outcome,
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Prospect name"},
                "predicted": {"type": "string", "description": "What was predicted: receptive|desperate|urgent|resistant|neutral"},
                "actual": {"type": "string", "description": "What actually happened"},
                "archetype": {"type": "string"},
                "variables": {"type": "object", "description": "PUT variables used in prediction"},
            },
            "required": ["name", "predicted", "actual"],
        },
    },
    {
        "name": "put_calibration_status",
        "description": "Check current PUT calibration state — coefficient values, accuracy, convergence status.",
        "handler": calibration_status,
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "put_compute",
        "description": "Compute all PUT variables (U, FP, Omega, Phi) using calibrated coefficients. Returns full psychometric profile.",
        "handler": compute_put_full,
        "parameters": {
            "type": "object",
            "properties": {
                "A": {"type": "number"}, "F": {"type": "number"}, "k": {"type": "number"},
                "S": {"type": "number"}, "w": {"type": "number"}, "Sigma": {"type": "number"},
                "tau": {"type": "number"}, "kappa": {"type": "number"},
                "E_ext": {"type": "number"}, "E_int": {"type": "number"}, "R": {"type": "number"},
            },
        },
    },
    {
        "name": "put_discover_archetypes",
        "description": (
            "Discover empirical archetypes from accumulated PUT data using K-Means clustering. "
            "Compares discovered clusters against the 7 theoretical archetypes. "
            "Identifies NOVEL archetypes that theory didn't predict. "
            "Requires at least 5 recorded interactions."
        ),
        "handler": discover_archetypes,
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "put_predict_conversion_time",
        "description": (
            "Temporal prediction: WHEN will this prospect reach ignition (conversion moment)? "
            "Uses RK4 ODE integration for accurate numerical trajectory + Monte Carlo "
            "coefficient uncertainty to give confidence interval in days. "
            "Returns: ignition_day, confidence_interval [low, high], probability_30d, "
            "trajectory summary. Answers 'in N days' not just 'will they convert'."
        ),
        "handler": predict_conversion_time,
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Prospect name"},
                "A": {"type": "number", "description": "Ambition 0-1"},
                "F": {"type": "number", "description": "Fear 0-1"},
                "k": {"type": "number", "description": "Shadow coefficient 0-1"},
                "S": {"type": "number", "description": "Status 0-1"},
                "w": {"type": "number", "description": "Wound weight 0-1"},
                "Sigma": {"type": "number", "description": "Ecosystem stability 0-1"},
                "tau": {"type": "number", "description": "Treachery 0-1"},
                "kappa": {"type": "number", "description": "Guilt transfer 0-1"},
                "Phi": {"type": "number", "description": "Self-delusion 0-2"},
                "R_net": {"type": "number", "description": "Network resonance -1 to 1"},
                "days": {"type": "integer", "description": "Simulation horizon in days (default 90)"},
                "archetype": {"type": "string", "description": "Prospect archetype for targeted coefficients"},
                "vertical": {"type": "string", "enum": ["ecommerce", "b2b_saas", "services", "marketplace", "enterprise", "startup"], "description": "Industry vertical for vertical-specific coefficients"},
                "in_crisis": {"type": "boolean", "description": "Whether prospect is already in crisis state"},
                "trigger_schedule": {"type": "array", "items": {"type": "number"}, "description": "Per-day trigger intensities [0-1]"},
                "threat_schedule": {"type": "array", "items": {"type": "number"}, "description": "Per-day threat intensities [0-1]"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "put_vertical_status",
        "description": (
            "Show calibration state for all 6 industry verticals "
            "(ecommerce, b2b_saas, services, marketplace, enterprise, startup). "
            "Shows current coefficient estimates, sample counts, and drift from theoretical priors. "
            "Use to know which verticals have been calibrated from real data vs theory only."
        ),
        "handler": vertical_calibration_status,
        "parameters": {"type": "object", "properties": {}},
    },
]
