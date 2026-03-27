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
            return json.loads(CALIBRATION_DB.read_text())
        except Exception:
            pass
    return {
        "global": {
            "alpha": {"mean": 0.5, "std": 0.2, "samples": 0},
            "beta": {"mean": 0.5, "std": 0.2, "samples": 0},
            "gamma": {"mean": 0.5, "std": 0.2, "samples": 0},
            "delta": {"mean": 0.3, "std": 0.2, "samples": 0},
            "epsilon": {"mean": 0.3, "std": 0.2, "samples": 0},
        },
        "archetypes": {},
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

def compute_U(A, F, k, S, w, Sigma, tau, kappa, Phi, coeffs):
    """Compute Psychic Utility with given coefficients."""
    alpha = coeffs["alpha"]
    beta = coeffs["beta"]
    gamma = coeffs["gamma"]
    delta = coeffs["delta"]
    epsilon = coeffs["epsilon"]

    Fk = F * (1 - k)  # Shadow-adjusted fear
    U = (alpha * A * (1 - Fk)
         - beta * Fk * (1 - S)
         + gamma * S * (1 - w) * Sigma
         + delta * tau * kappa
         - epsilon * Phi)
    return U


def compute_FP(R, kappa, tau, Phi, U, U_crit=0.3, eps=1e-3):
    """Compute Fracture Potential.

    Denominator guarded: without max(), it goes negative when U > U_crit + eps,
    making FP negative — physically meaningless and corrupts avg_FP aggregation.
    Same guard as put_engine.py:127 and put_api.py:166.
    """
    denominator = max(U_crit - U + eps, eps)
    return ((1 - R) * (kappa + tau + Phi)) / denominator


def compute_Omega(U, U_crit=0.3, k_omega=1.0):
    """Compute Desperation Factor."""
    return 1 + math.exp(-k_omega * (U - U_crit))


def compute_Phi(E_ext, E_int):
    """Compute Self-Delusion Factor."""
    return (E_ext + E_int) / (1 + abs(E_ext - E_int))


# ── Monte Carlo Simulation ────────────────────────────────────

def _sample_coefficients(cal: dict, archetype: str = None, n: int = 50) -> List[dict]:
    """Generate N coefficient sets by sampling from current distributions."""
    source = cal.get("archetypes", {}).get(archetype, cal.get("global", {}))

    samples = []
    for _ in range(n):
        sample = {}
        for coeff in ["alpha", "beta", "gamma", "delta", "epsilon"]:
            dist = source.get(coeff, {"mean": 0.5, "std": 0.2})
            val = random.gauss(dist["mean"], dist["std"])
            sample[coeff] = max(0.01, min(1.0, val))  # Clamp to [0.01, 1.0]
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

    Phi = compute_Phi(E_ext, E_int)

    cal = _load_calibration()
    samples = _sample_coefficients(cal, archetype, n=100)

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
    samples = _sample_coefficients(cal, archetype, n=200)
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

    # Bayesian update: narrow distributions toward coefficients that predicted correctly
    target = cal.get("archetypes", {}).get(archetype, cal.get("global", {}))

    if correct_coeffs:
        for coeff in ["alpha", "beta", "gamma", "delta", "epsilon"]:
            values = [c[coeff] for c in correct_coeffs]
            new_mean = sum(values) / len(values)
            new_std = max(0.05, (sum((v - new_mean) ** 2 for v in values) / len(values)) ** 0.5)

            old = target.get(coeff, {"mean": 0.5, "std": 0.2, "samples": 0})
            n = old.get("samples", 0)

            # Weighted average: more samples = more trust in existing
            weight = min(n / (n + len(correct_coeffs)), 0.9)
            target[coeff] = {
                "mean": round(weight * old["mean"] + (1 - weight) * new_mean, 4),
                "std": round(weight * old["std"] + (1 - weight) * new_std, 4),
                "samples": n + 1,
            }

    # Save to archetype if specified
    if archetype:
        cal.setdefault("archetypes", {})[archetype] = target
    else:
        cal["global"] = target

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
            "total_interactions": cal.get("total_interactions", 0),
            "accuracy": round(accuracy, 2),
            "history_size": len(acc),
            "convergence": "calibrating" if len(acc) < 50 else ("converged" if accuracy > 0.7 else "needs_more_data"),
        },
        "message": (
            f"PUT Calibration: {cal.get('total_interactions', 0)} interactions, "
            f"{accuracy:.0%} accuracy, {len(cal.get('archetypes', {}))} archetypes. "
            f"Status: {'converged' if len(acc) >= 50 and accuracy > 0.7 else 'calibrating'}"
        ),
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
]
