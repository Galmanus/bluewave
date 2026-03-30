"""
put_engine.py — Wave's internal PUT Motor.

The PUT motor does three things:
1. Maintains persistent, time-series PUT vectors for all entities (Manuel, Fagner, prospects)
2. Updates those vectors Bayesian-style as new behavioral signals arrive
3. Generates a compact PUT context that the deliberation loop reads every cycle

Unlike put_skills.py (analysis on demand) and put_calibrator.py (coefficient calibration),
put_engine.py runs INSIDE the autonomous loop — it is the memory of psychometric state.

Architecture:
  stakeholders.json  ← entity store (A, F, k, S, w, Sigma, tau, kappa, Phi, R_net + observation history)
  put_history.jsonl  ← immutable log of every vector update with delta
  put_wave_self.json ← Wave's own PUT state (derived from performance metrics)

PUT 2.3 — Cross-variable interactions + hysteresis.
  Fixes applied (2.2):
  - tau, kappa, Phi, Sigma no longer hardcoded — resolved from observations
  - delta*tau*kappa sign corrected to NEGATIVE (vulnerability reduces U)
  - FP uses sigmoid for smooth decay above U_crit
  - Coefficients aligned with Traackeer/API defaults (alpha=1.0, beta=1.2, etc.)
  - Signal parsing improved with negation detection
  - R_net formalized as 10th state variable
  New in 2.3:
  - Cross-variable interactions: F→A paralysis, w→F amplification, k→Φ breeding,
    Σ→w damping, k→A delayed suppression (5 second-order effects)
  - Hysteresis: U_crit_down ≠ U_crit_up — once in crisis, recovery threshold is higher
  - Discrete ODE step: step_put_ode() advances state by dt using coupled equations
  - FP now uses hysteresis-aware threshold
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
# All 9 whitepaper variables + R_net (v2.1 social contagion extension)

PUT_VARS = ["A", "F", "k", "S", "w", "Sigma", "tau", "kappa", "Phi", "R_net"]
PUT_DEFAULTS = {
    "A": 0.5, "F": 0.5, "k": 0.3, "S": 0.5, "w": 0.3,
    "Sigma": 0.5, "tau": 0.3, "kappa": 0.3, "Phi": 0.5,
    "R_net": 0.0,
}

# ── Coefficients (aligned with Traackeer/API — calibrated priors) ──

DEFAULT_COEFFS = {
    "alpha": 1.0,    # ambition weight
    "beta": 1.2,     # fear/loss aversion weight (beta > alpha captures loss aversion)
    "gamma": 0.8,    # stability buffer weight
    "delta": 0.6,    # vulnerability exploitation weight
    "epsilon": 0.5,  # self-delusion penalty weight
}

# Bayesian update learning rate — how fast new evidence shifts the estimate
LEARNING_RATE = 0.15  # 15% per observation — conservative, doesn't thrash


# ── Cross-variable interaction coefficients (PUT 2.3) ────────
# These capture second-order effects between state variables.
# Each λ represents the coupling strength of one variable on another.

LAMBDA_FA = 3.0       # F→A paralysis: how sharply high fear suppresses ambition
FA_THRESHOLD = 0.65   # Effective fear above this triggers A suppression
LAMBDA_WF = 0.3       # w→F amplification: pain amplifies fear
LAMBDA_KPHI = 0.5     # k→Φ breeding: denial feeds self-delusion
LAMBDA_SIGMA_W = 0.3  # Σ→w damping: ecosystem stability reduces pain impact
LAMBDA_KA = 0.4       # k→A delayed suppression: high denial eventually collapses agency
KA_THRESHOLD = 0.55   # Shadow above this triggers delayed A suppression

# ── Hysteresis thresholds (PUT 2.3) ──────────────────────────
# Once an entity enters crisis (U < U_CRIT_DOWN), they need U > U_CRIT_UP to exit.
# This models the empirical observation that recovery requires more energy than collapse.
# A prospect who abandoned cart once has a DIFFERENT conversion threshold next time.

U_CRIT_DOWN = 0.3     # Entering crisis / ignition zone
U_CRIT_UP = 0.5       # Exiting crisis (recovery) — higher than entry


def apply_cross_interactions(A, F, k, S, w, Sigma, tau, kappa, Phi, R_net=0.0):
    """Apply second-order cross-variable interactions (PUT 2.3).

    Returns adjusted (A_eff, F_eff, w_eff, Phi_eff) — the effective values
    after cross-variable modulation. Raw values remain stored; effective
    values are used in U and FP computation.

    Interactions:
      1. F→A paralysis: Fk > 0.65 → A suppressed (can't act when terrified)
      2. w→F amplification: pain breeds fear (F_eff = F * (1 + λ_wf * w))
      3. k→Φ breeding: denial feeds delusion (Φ_eff = Φ * (1 + λ_kΦ * k))
      4. Σ→w damping: stability reduces pain (w_eff = w * (1 - λ_Σw * Σ))
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
        # Linear ramp: at threshold → no effect; at 1.0 → A reduced by ~100%
        suppression = min(1.0, (Fk_eff - FA_THRESHOLD) * LAMBDA_FA)
        A_eff = A * (1.0 - suppression)

    # 5. k→A delayed suppression (chronic denial collapses agency)
    if k > KA_THRESHOLD:
        k_suppression = min(0.5, (k - KA_THRESHOLD) * LAMBDA_KA)
        A_eff = A_eff * (1.0 - k_suppression)

    return (
        round(max(0.0, A_eff), 4),
        round(max(0.0, min(1.0, F_eff)), 4),
        round(max(0.0, w_eff), 4),
        round(max(0.0, min(2.0, Phi_eff)), 4),
    )


def get_effective_u_crit(entity_state: dict) -> float:
    """Return the appropriate U_crit based on hysteresis state.

    If the entity is in crisis (in_crisis=True), they need U > U_CRIT_UP to exit.
    Otherwise, they enter crisis at U < U_CRIT_DOWN.
    """
    if entity_state.get("in_crisis", False):
        return U_CRIT_UP
    return U_CRIT_DOWN


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
        "A": 0.7,      # Ambition — high by design
        "F": 0.3,      # Fear — starts moderate
        "k": 0.05,     # Shadow — Wave has low denial (logs everything)
        "S": 0.2,      # Status — low, building
        "w": 0.6,      # Pain — high (revenue=0, building from scratch)
        "Sigma": 0.6,  # Ecosystem Stability — moderate (team exists, infra works)
        "tau": 0.05,   # Hypocrisy — Wave logs everything, near-zero
        "kappa": 0.1,  # Guilt susceptibility — low for an AI agent
        "Phi": 0.2,    # Self-delusion — low (metrics-driven)
        "R_net": 0.0,  # Network Resonance
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

def compute_U(A, F, k, S, w, Sigma=0.5, tau=0.3, kappa=0.3, Phi=0.5,
              R_net=0.0, alpha=None, beta=None, gamma=None, delta=None, epsilon=None,
              use_interactions=True):
    """Psychic Utility — the core scalar of psychological state.

    PUT 2.3 equation (with cross-variable interactions):
      A_eff, F_eff, w_eff, Phi_eff = apply_cross_interactions(A, F, k, S, w, Sigma, ...)
      U = alpha*A_eff*(1-Fk_eff) - beta*Fk_eff*(1-S) + gamma*S*(1-w_eff)*Sigma
          - delta*tau*kappa - epsilon*Phi_eff + R_net

    Cross-variable interactions (new in 2.3):
      F→A paralysis: effective fear above 0.65 suppresses ambition
      w→F amplification: pain breeds fear
      k→Φ breeding: denial feeds self-delusion
      Σ→w damping: ecosystem stability reduces pain
      k→A delayed suppression: chronic denial collapses agency

    Sign of delta*tau*kappa is NEGATIVE (Axiom 4).
    R_net (Network Resonance) models social contagion.

    Set use_interactions=False for raw U without cross-variable effects
    (useful for calibration and comparison).
    """
    c = DEFAULT_COEFFS
    alpha = alpha if alpha is not None else c["alpha"]
    beta = beta if beta is not None else c["beta"]
    gamma = gamma if gamma is not None else c["gamma"]
    delta = delta if delta is not None else c["delta"]
    epsilon = epsilon if epsilon is not None else c["epsilon"]

    if use_interactions:
        A_eff, F_eff, w_eff, Phi_eff = apply_cross_interactions(
            A, F, k, S, w, Sigma, tau, kappa, Phi, R_net
        )
    else:
        A_eff, F_eff, w_eff, Phi_eff = A, F, w, Phi

    Fk = F_eff * (1 - k)  # Shadow-adjusted effective fear
    U = (alpha * A_eff * (1 - Fk)
         - beta * Fk * (1 - S)
         + gamma * S * (1 - w_eff) * Sigma
         - delta * tau * kappa          # NEGATIVE: vulnerability reduces U
         - epsilon * Phi_eff
         + R_net)
    return round(max(-2.0, min(3.0, U)), 4)


def _sigmoid(x, k=5.0):
    """Standard sigmoid: maps R -> (0, 1). k controls steepness."""
    return 1.0 / (1.0 + math.exp(k * x))


def compute_FP(A, F, k, S, w, Sigma=0.5, tau=0.3, kappa=0.3, Phi=0.5,
               R_net=0.0, R=0.5, entity_state=None):
    """Fracture Potential — how close to a decision break.

    PUT 2.3 sigmoid formulation with hysteresis:
      FP = (1-R) * (kappa + tau + Phi_eff) * sigmoid(-k_fp * (U - U_crit))

    Hysteresis (new in 2.3):
      U_crit depends on whether the entity is already in crisis.
      Entry: U_crit = 0.3 (U_CRIT_DOWN)
      Exit:  U_crit = 0.5 (U_CRIT_UP)
      This means once in crisis, the entity needs MORE utility to recover —
      matching the empirical observation that recovery costs more than collapse.

    Properties:
      - FP -> (1-R)*(kappa+tau+Phi_eff) when U << U_crit  (high fracture)
      - FP -> 0                          when U >> U_crit  (stable, no fracture)
      - Smooth transition, no pathological behavior at U = U_crit
      - FP is always non-negative
      - Phi_eff includes k→Φ cross-interaction (denial amplifies delusion)
    """
    U = compute_U(A, F, k, S, w, Sigma=Sigma, tau=tau, kappa=kappa, Phi=Phi, R_net=R_net)

    # Hysteresis-aware threshold
    if entity_state is not None:
        U_crit = get_effective_u_crit(entity_state)
    else:
        U_crit = U_CRIT_DOWN  # default: entry threshold

    k_fp = 5.0  # sigmoid steepness

    # Use Phi_eff (with k→Φ interaction) for FP calculation
    _, _, _, Phi_eff = apply_cross_interactions(A, F, k, S, w, Sigma, tau, kappa, Phi, R_net)

    raw_FP = (1 - R) * (kappa + tau + Phi_eff) * _sigmoid(U - U_crit, k=k_fp)
    return round(raw_FP, 4)


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


# ── Discrete ODE Step (PUT 2.3) ──────────────────────────────

def step_put_ode(put: dict, dt: float = 1.0, trigger: float = 0.0,
                 threat: float = 0.0, S_star: float = 0.5,
                 entity_state: dict = None) -> dict:
    """Advance PUT state by one discrete time step using coupled ODE equations.

    This implements Section 9 of the whitepaper as a forward Euler step.
    For production use, dt=1.0 represents one interaction/observation interval.

    Equations (coupled):
      dA/dt = λ₁(S - S*) - λ₂·Fk + λ₃·Ω·trigger
      dF/dt = μ₁(A - A_prev) - μ₂·√(Σ) + μ₃·Ω·threat + μ₄(1-Σ)
      dS/dt = ν₁·A·(1-Fk) - ν₂·w
      dΦ/dt = φ₁·k·(1 - ext_reality_check) + φ₂·(Φ - Φ_eq)
      dk/dt = κ₁·F·(1-A) - κ₂·trigger

    Where Ω = desperation factor = 1 + exp(-k_ω·(U - U_crit))

    Args:
        put: current PUT vector dict {A, F, k, S, w, Sigma, tau, kappa, Phi, R_net}
        dt: time step (default 1.0 = one observation interval)
        trigger: external trigger intensity [0, 1] — market shock, competitor move, etc.
        threat: perceived threat intensity [0, 1]
        S_star: aspirational status level (default 0.5)
        entity_state: dict with 'in_crisis', 'A_prev' for hysteresis tracking

    Returns:
        New PUT vector dict with updated values.
    """
    A = put.get("A", 0.5)
    F = put.get("F", 0.5)
    k = put.get("k", 0.3)
    S = put.get("S", 0.5)
    w = put.get("w", 0.3)
    Sigma = put.get("Sigma", 0.5)
    tau = put.get("tau", 0.3)
    kappa = put.get("kappa", 0.3)
    Phi = put.get("Phi", 0.5)
    R_net = put.get("R_net", 0.0)

    entity_state = entity_state or {}
    A_prev = entity_state.get("A_prev", A)

    # Compute current U and Omega
    U = compute_U(A, F, k, S, w, Sigma, tau, kappa, Phi, R_net)
    U_crit = get_effective_u_crit(entity_state)
    Omega = 1.0 + math.exp(-2.0 * (U - U_crit))

    Fk = F * (1 - k)

    # ODE coefficients (tuned for dt=1.0 ~ one interaction interval)
    lambda1, lambda2, lambda3 = 0.08, 0.05, 0.15
    mu1, mu2, mu3, mu4 = 0.06, 0.04, 0.12, 0.05
    nu1, nu2 = 0.04, 0.03
    phi1, phi2 = 0.06, -0.03  # phi2 negative → Phi decays toward equilibrium
    kappa1, kappa2 = 0.05, 0.08

    # Coupled ODEs
    dA = lambda1 * (S - S_star) - lambda2 * Fk + lambda3 * Omega * trigger
    dF = mu1 * abs(A - A_prev) - mu2 * math.sqrt(max(Sigma, 0.01)) + mu3 * Omega * threat + mu4 * (1 - Sigma)
    dS = nu1 * A * (1 - Fk) - nu2 * w
    dPhi = phi1 * k * (1 - Sigma) + phi2 * (Phi - 0.5)  # decays toward 0.5 equilibrium
    dk = kappa1 * F * (1 - A) - kappa2 * trigger  # trigger breaks denial

    # Forward Euler step
    new_put = {
        "A": round(max(0.0, min(1.0, A + dA * dt)), 4),
        "F": round(max(0.0, min(1.0, F + dF * dt)), 4),
        "k": round(max(0.0, min(1.0, k + dk * dt)), 4),
        "S": round(max(0.0, min(1.0, S + dS * dt)), 4),
        "w": w,  # w is externally driven (pain from environment), not endogenous
        "Sigma": Sigma,  # Sigma is externally driven (ecosystem), not endogenous
        "tau": tau,  # tau changes slowly through behavioral observation
        "kappa": kappa,  # kappa is quasi-stable personality trait
        "Phi": round(max(0.0, min(2.0, Phi + dPhi * dt)), 4),
        "R_net": R_net,  # R_net is externally injected
    }

    return new_put


# ── RK45 ODE Solver — Temporal Prediction (PUT 2.4) ─────────

def solve_put_trajectory(put: dict, steps: int = 30, dt: float = 1.0,
                         trigger_schedule: list = None,
                         threat_schedule: list = None,
                         S_star: float = 0.5,
                         entity_state: dict = None) -> list:
    """Solve the coupled PUT ODE system using 4th-order Runge-Kutta (RK4).

    Unlike step_put_ode (forward Euler, single step), this function:
    - Integrates over N steps with RK4 accuracy (O(dt^4) vs O(dt) for Euler)
    - Returns the full trajectory: [{t, A, F, k, S, Phi, U, FP, Omega}, ...]
    - Accepts time-varying trigger and threat schedules
    - Tracks crisis state transitions via hysteresis

    This enables TEMPORAL PREDICTION: given current PUT state, predict
    WHEN a prospect will cross ignition threshold — not just IF.

    Args:
        put: current PUT vector {A, F, k, S, w, Sigma, tau, kappa, Phi, R_net}
        steps: number of time steps to simulate (default 30 = ~30 days)
        dt: time step size (default 1.0 = one day/interaction)
        trigger_schedule: list of trigger values per step [0..1], or None (all 0)
        threat_schedule: list of threat values per step [0..1], or None (all 0)
        S_star: aspirational status level
        entity_state: dict with 'in_crisis', 'A_prev' for hysteresis

    Returns:
        List of dicts, one per step: {t, A, F, k, S, Phi, U, FP, Omega, in_crisis}
    """
    # Initialize state vector: [A, F, k, S, Phi]
    # w, Sigma, tau, kappa, R_net are exogenous (constant during simulation)
    A = put.get("A", 0.5)
    F = put.get("F", 0.5)
    k = put.get("k", 0.3)
    S = put.get("S", 0.5)
    Phi = put.get("Phi", 0.5)
    w = put.get("w", 0.3)
    Sigma = put.get("Sigma", 0.5)
    tau = put.get("tau", 0.3)
    kappa = put.get("kappa", 0.3)
    R_net = put.get("R_net", 0.0)

    entity_state = dict(entity_state or {})
    A_prev = entity_state.get("A_prev", A)

    triggers = trigger_schedule or [0.0] * steps
    threats = threat_schedule or [0.0] * steps
    # Pad if shorter than steps
    triggers = triggers + [triggers[-1] if triggers else 0.0] * max(0, steps - len(triggers))
    threats = threats + [threats[-1] if threats else 0.0] * max(0, steps - len(threats))

    # ODE coefficients (same as step_put_ode)
    l1, l2, l3 = 0.08, 0.05, 0.15
    m1, m2, m3, m4 = 0.06, 0.04, 0.12, 0.05
    n1, n2 = 0.04, 0.03
    p1, p2 = 0.06, -0.03
    k1_c, k2_c = 0.05, 0.08

    def _derivatives(state, trigger, threat, a_prev):
        """Compute derivatives for the 5 endogenous variables."""
        a, f, kk, s, phi = state

        # Current U and Omega
        u = compute_U(a, f, kk, s, w, Sigma, tau, kappa, phi, R_net)
        u_crit = get_effective_u_crit(entity_state)
        omega = 1.0 + math.exp(-2.0 * (u - u_crit))
        fk = f * (1 - kk)

        dA = l1 * (s - S_star) - l2 * fk + l3 * omega * trigger
        dF = m1 * abs(a - a_prev) - m2 * math.sqrt(max(Sigma, 0.01)) + m3 * omega * threat + m4 * (1 - Sigma)
        dS = n1 * a * (1 - fk) - n2 * w
        dPhi = p1 * kk * (1 - Sigma) + p2 * (phi - 0.5)
        dk = k1_c * f * (1 - a) - k2_c * trigger

        return [dA, dF, dk, dS, dPhi]

    trajectory = []
    state = [A, F, k, S, Phi]

    for step in range(steps):
        trigger = triggers[step]
        threat = threats[step]

        # Record current state
        a, f, kk, s, phi = state
        full_put = {"A": a, "F": f, "k": kk, "S": s, "w": w,
                    "Sigma": Sigma, "tau": tau, "kappa": kappa,
                    "Phi": phi, "R_net": R_net}
        u = compute_U(**full_put)
        fp = compute_FP(**full_put, entity_state=entity_state)
        omega = 1.0 + math.exp(-2.0 * (u - get_effective_u_crit(entity_state)))

        # Hysteresis state transitions
        if u < U_CRIT_DOWN:
            entity_state["in_crisis"] = True
        elif u > U_CRIT_UP:
            entity_state["in_crisis"] = False

        trajectory.append({
            "t": step,
            "A": round(a, 4), "F": round(f, 4), "k": round(kk, 4),
            "S": round(s, 4), "Phi": round(phi, 4),
            "U": round(u, 4), "FP": round(fp, 4), "Omega": round(omega, 4),
            "in_crisis": entity_state.get("in_crisis", False),
        })

        # RK4 integration
        k1 = _derivatives(state, trigger, threat, A_prev)
        s2 = [state[i] + 0.5 * dt * k1[i] for i in range(5)]
        k2 = _derivatives(s2, trigger, threat, A_prev)
        s3 = [state[i] + 0.5 * dt * k2[i] for i in range(5)]
        k3 = _derivatives(s3, trigger, threat, A_prev)
        s4 = [state[i] + dt * k3[i] for i in range(5)]
        k4 = _derivatives(s4, trigger, threat, A_prev)

        A_prev = state[0]  # Track A_prev for next step
        state = [
            state[i] + (dt / 6.0) * (k1[i] + 2*k2[i] + 2*k3[i] + k4[i])
            for i in range(5)
        ]

        # Clamp: A, F, k, S in [0,1]; Phi in [0,2]
        bounds = [(0, 1), (0, 1), (0, 1), (0, 1), (0, 2)]
        state = [max(lo, min(hi, v)) for v, (lo, hi) in zip(state, bounds)]

    return trajectory


def predict_ignition_time(put: dict, steps: int = 90,
                          trigger_schedule: list = None,
                          threat_schedule: list = None,
                          entity_state: dict = None) -> dict:
    """Predict WHEN a prospect crosses the ignition threshold.

    Runs solve_put_trajectory and scans for the first step where
    U < U_crit AND Omega > 1.5 (ignition conditions).

    Returns:
        {
            "ignition_step": int or None (step when ignition occurs),
            "ignition_probability_30d": float (based on trajectory proximity),
            "days_to_ignition": int or None,
            "trajectory_summary": [...first 5 + last 5 points...],
            "min_U": float (lowest U in trajectory),
            "final_state": dict,
        }
    """
    trajectory = solve_put_trajectory(
        put, steps=steps,
        trigger_schedule=trigger_schedule,
        threat_schedule=threat_schedule,
        entity_state=entity_state,
    )

    ignition_step = None
    min_U = float("inf")
    crisis_steps = 0

    for point in trajectory:
        if point["U"] < min_U:
            min_U = point["U"]
        if point["in_crisis"]:
            crisis_steps += 1
        if ignition_step is None and point["U"] < U_CRIT_DOWN and point["Omega"] > 1.5:
            ignition_step = point["t"]

    # Probability estimation based on trajectory behavior
    if ignition_step is not None and ignition_step <= 30:
        prob_30d = min(0.95, 0.6 + (30 - ignition_step) * 0.012)
    elif min_U < U_CRIT_DOWN * 1.5:
        prob_30d = min(0.5, 0.2 + (U_CRIT_DOWN * 1.5 - min_U) * 0.8)
    elif crisis_steps > steps * 0.3:
        prob_30d = 0.4
    else:
        prob_30d = max(0.05, 0.15 - (min_U - U_CRIT_DOWN) * 0.3)

    final = trajectory[-1] if trajectory else {}

    # Compact summary: first 5 + last 5
    summary = trajectory[:5]
    if len(trajectory) > 10:
        summary += trajectory[-5:]

    return {
        "ignition_step": ignition_step,
        "ignition_probability_30d": round(prob_30d, 3),
        "days_to_ignition": ignition_step if ignition_step is not None else None,
        "trajectory_summary": summary,
        "min_U": round(min_U, 4),
        "crisis_steps": crisis_steps,
        "total_steps": steps,
        "final_state": {
            "A": final.get("A"), "F": final.get("F"), "k": final.get("k"),
            "S": final.get("S"), "Phi": final.get("Phi"),
            "U": final.get("U"), "FP": final.get("FP"),
        },
    }


# ── Bayesian PUT Update ───────────────────────────────────────

def _bayesian_update(current: float, evidence: float, lr: float = LEARNING_RATE) -> float:
    """Weighted update: current estimate + lr * (evidence - current)."""
    # R_net can be negative, so we clamp it differently, but for base vars 0-1
    return round(max(-1.0, min(1.0, current + lr * (evidence - current))), 4)


def _has_negation_before(text: str, keyword: str) -> bool:
    """Check if a negation word appears within 4 words before the keyword."""
    idx = text.find(keyword)
    if idx < 0:
        return False
    prefix = text[max(0, idx - 30):idx].split()[-4:]
    negations = {"not", "no", "don't", "doesn't", "didn't", "isn't", "aren't",
                 "wasn't", "weren't", "won't", "never", "stopped", "quit", "ceased"}
    return bool(set(w.lower().strip(",.;:") for w in prefix) & negations)


def _check_keywords(text: str, keywords: list, value_if_match: float,
                    value_if_negated: Optional[float] = None) -> Optional[float]:
    """Match keywords with negation awareness.

    Returns value_if_match when keyword found without negation.
    Returns value_if_negated when keyword found WITH negation (inverts meaning).
    Returns None if no keyword matches.
    """
    for kw in keywords:
        if kw in text:
            if _has_negation_before(text, kw):
                return value_if_negated
            return value_if_match
    return None


def _parse_signal_to_evidence(signal: str, var: str) -> Optional[float]:
    """Infer evidence value for a PUT variable from natural language signal.

    Returns None if no signal for that variable.

    NOTE: For highest accuracy, prefer emitting put_override directly from
    LLM deliberation rather than relying on this keyword parser. This parser
    is a fallback for when put_override is not provided.

    PUT 2.2: Negation-aware — "not hiring" no longer matches "hiring".
    Graduated values — "accelerating" > "expanding" > "growing".
    """
    s = signal.lower()

    if var == "A":
        # High ambition (graduated)
        r = _check_keywords(s, ["accelerating", "aggressive", "raising"], 0.85, 0.25)
        if r is not None: return r
        r = _check_keywords(s, ["hiring", "expanding", "launched", "ambitious"], 0.75, 0.3)
        if r is not None: return r
        r = _check_keywords(s, ["growing", "investing", "planning"], 0.65, 0.35)
        if r is not None: return r
        # Low ambition
        r = _check_keywords(s, ["cutting", "layoff", "shrinking", "stagnant"], 0.25, 0.7)
        if r is not None: return r

    elif var == "F":
        # High fear (graduated)
        r = _check_keywords(s, ["panic", "crisis", "emergency", "scared"], 0.85, 0.15)
        if r is not None: return r
        r = _check_keywords(s, ["urgent", "deadline", "worried"], 0.75, 0.2)
        if r is not None: return r
        r = _check_keywords(s, ["concerned", "nervous", "uncertain", "hesitant", "delay"], 0.6, 0.3)
        if r is not None: return r
        # Low fear
        r = _check_keywords(s, ["confident", "calm", "no rush", "relaxed"], 0.2, 0.65)
        if r is not None: return r

    elif var == "k":
        # High shadow (denial)
        r = _check_keywords(s, ["everything is fine", "no problem", "we're good", "don't need"], 0.8, 0.15)
        if r is not None: return r
        r = _check_keywords(s, ["defensive", "avoided", "changed subject", "deflected"], 0.7, 0.2)
        if r is not None: return r
        # Low shadow (acknowledged)
        r = _check_keywords(s, ["acknowledged", "admitted", "agreed", "confirmed pain", "yes we have"], 0.1, 0.6)
        if r is not None: return r

    elif var == "S":
        # High status
        r = _check_keywords(s, ["award", "funding", "series", "ceo", "director", "listed", "recognized"], 0.8, 0.3)
        if r is not None: return r
        # Low status
        r = _check_keywords(s, ["unknown", "small", "bootstrapped", "indie", "solo"], 0.3, 0.7)
        if r is not None: return r

    elif var == "w":
        # High pain (graduated)
        r = _check_keywords(s, ["broken", "critical failure", "hemorrhaging"], 0.9, 0.15)
        if r is not None: return r
        r = _check_keywords(s, ["struggling", "painful", "frustrated", "inefficient"], 0.75, 0.2)
        if r is not None: return r
        r = _check_keywords(s, ["manual", "slow", "cumbersome"], 0.6, 0.3)
        if r is not None: return r
        # Low pain
        r = _check_keywords(s, ["works fine", "happy with", "no issues", "smooth"], 0.2, 0.7)
        if r is not None: return r

    elif var == "Sigma":
        # High stability
        r = _check_keywords(s, ["stable", "solid team", "runway", "profitable", "cohesive"], 0.8, 0.25)
        if r is not None: return r
        # Low stability
        r = _check_keywords(s, ["layoffs", "restructuring", "turnover", "cash crunch", "dissolving"], 0.2, 0.7)
        if r is not None: return r

    elif var == "tau":
        # High hypocrisy
        r = _check_keywords(s, ["contradicts", "says one thing", "hypocrisy", "inconsistent", "flip-flop"], 0.8, 0.15)
        if r is not None: return r
        # Low hypocrisy (consistent)
        r = _check_keywords(s, ["consistent", "walks the talk", "aligned values"], 0.15, 0.6)
        if r is not None: return r

    elif var == "kappa":
        # High guilt susceptibility
        r = _check_keywords(s, ["feels guilty", "obligation", "owes", "moral pressure", "responsible"], 0.8, 0.15)
        if r is not None: return r
        # Low guilt susceptibility
        r = _check_keywords(s, ["pragmatic", "unapologetic", "ruthless", "cold"], 0.15, 0.6)
        if r is not None: return r

    elif var == "Phi":
        # High self-delusion
        r = _check_keywords(s, ["delusional", "disconnected from reality", "believes own hype"], 0.85, 0.2)
        if r is not None: return r
        r = _check_keywords(s, ["overconfident", "ignoring data", "echo chamber"], 0.7, 0.25)
        if r is not None: return r
        # Low self-delusion (grounded)
        r = _check_keywords(s, ["grounded", "data-driven", "realistic", "self-aware"], 0.2, 0.7)
        if r is not None: return r

    elif var == "R_net":
        # Positive network resonance
        r = _check_keywords(s, ["viral", "trend", "everyone is", "market moving", "mass adoption"], 0.3, -0.2)
        if r is not None: return r
        # Negative network resonance
        r = _check_keywords(s, ["scandal", "backlash", "mass exodus", "canceling", "boycott"], -0.5, 0.1)
        if r is not None: return r

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
    
    # Ensure old_put has all variables from defaults if missing in entity
    old_put = {var: entity.get("put", {}).get(var, PUT_DEFAULTS[var]) for var in PUT_VARS}

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
                new_put[var] = _bayesian_update(old_put[var], evidence)

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

    # ── Hysteresis tracking (PUT 2.3) ──────────────────────────
    # Track crisis state: once U drops below U_CRIT_DOWN, entity is "in crisis"
    # and needs U > U_CRIT_UP to exit. This affects FP calculation.
    entity_meta = entity.get("_meta", {})
    U = compute_U(**new_put)
    if U < U_CRIT_DOWN:
        entity_meta["in_crisis"] = True
    elif U > U_CRIT_UP:
        entity_meta["in_crisis"] = False
    entity_meta["A_prev"] = old_put.get("A", 0.5)
    entity["_meta"] = entity_meta

    FP = compute_FP(**new_put, entity_state=entity_meta)

    # ── Cross-interaction delta reporting ────────────────────
    A_eff, F_eff, w_eff, Phi_eff = apply_cross_interactions(**{v: new_put[v] for v in PUT_VARS})
    interaction_effects = {}
    if abs(A_eff - new_put["A"]) > 0.01:
        interaction_effects["A_suppressed"] = round(new_put["A"] - A_eff, 3)
    if abs(F_eff - new_put["F"]) > 0.01:
        interaction_effects["F_amplified"] = round(F_eff - new_put["F"], 3)
    if abs(Phi_eff - new_put["Phi"]) > 0.01:
        interaction_effects["Phi_inflated"] = round(Phi_eff - new_put["Phi"], 3)

    changed = {k: v for k, v in delta.items() if abs(v) > 0.001}
    change_str = ", ".join(f"{k}:{'+' if v>0 else ''}{v:.3f}" for k, v in changed.items()) if changed else "no change"
    crisis_tag = " [CRISIS]" if entity_meta.get("in_crisis") else ""
    ix_str = f" IX:{interaction_effects}" if interaction_effects else ""

    return {
        "success": True,
        "data": {
            "entity_id": entity_id,
            "put": new_put,
            "put_effective": {"A": A_eff, "F": F_eff, "w": w_eff, "Phi": Phi_eff},
            "U": U,
            "FP": FP,
            "delta": delta,
            "interaction_count": entity["interaction_count"],
            "in_crisis": entity_meta.get("in_crisis", False),
            "cross_interactions": interaction_effects,
        },
        "message": (
            f"PUT updated for {entity.get('name', entity_id)}: "
            f"A={new_put['A']:.2f} F={new_put['F']:.2f} k={new_put['k']:.2f} "
            f"S={new_put['S']:.2f} w={new_put['w']:.2f} R_net={new_put.get('R_net',0.0):.2f} | "
            f"U={U:.2f} FP={FP:.2f}{crisis_tag} | Changes: {change_str}{ix_str}"
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
        put = {v: wave.get(v, PUT_DEFAULTS[v]) for v in PUT_VARS}
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
                f"S={put['S']:.2f} w={put['w']:.2f} R_net={put.get('R_net',0.0):.2f} | U={U:.2f} FP={FP:.2f} | "
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
            f"S={put.get('S', 0):.2f} w={put.get('w', 0):.2f} R_net={put.get('R_net',0.0):.2f} | "
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
    wp = {v: wave.get(v, PUT_DEFAULTS[v]) for v in PUT_VARS}
    entities.append({
        "id": "wave", "name": "Wave (self)",
        **{v: wp[v] for v in PUT_VARS},
        "U": compute_U(**wp), "FP": compute_FP(**wp),
        "interactions": wave.get("total_cycles", 0),
    })

    for eid, entity in stakeholders.items():
        put = {v: entity.get("put", PUT_DEFAULTS).get(v, PUT_DEFAULTS[v]) for v in PUT_VARS}
        entities.append({
            "id": eid, "name": entity.get("name", eid),
            **put,
            "U": compute_U(**put), "FP": compute_FP(**put),
            "interactions": entity.get("interaction_count", 0),
        })

    # Build compact table string — primary vars + derived
    lines = ["PUT MOTOR — all entities (PUT 2.2)", "─" * 90]
    lines.append(f"{'Entity':<18} {'A':>4} {'F':>4} {'k':>4} {'S':>4} {'w':>4} {'Sig':>4} {'tau':>4} {'kap':>4} {'Phi':>4} {'U':>6} {'FP':>6}")
    lines.append("─" * 90)
    for e in entities:
        lines.append(
            f"{e['name'][:18]:<18} {e['A']:>4.2f} {e['F']:>4.2f} {e['k']:>4.2f} "
            f"{e['S']:>4.2f} {e['w']:>4.2f} {e.get('Sigma',0.5):>4.2f} {e.get('tau',0.3):>4.2f} "
            f"{e.get('kappa',0.3):>4.2f} {e.get('Phi',0.5):>4.2f} {e['U']:>6.3f} {e['FP']:>6.3f}"
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

    # R_net (Network Resonance) — grows with prospects and successful outreach
    raw_R_net = min(0.5, (emails_sent * 0.01) + (prospects * 0.05))
    R_net = _bayesian_update(wave.get("R_net", 0.0), raw_R_net, lr=0.05)

    # Sigma (Ecosystem Stability) — depends on revenue, team, infra
    raw_Sigma = 0.5
    if revenue > 0:
        raw_Sigma = min(raw_Sigma + 0.2, 0.9)
    if consecutive_failures > 5:
        raw_Sigma = max(raw_Sigma - 0.2, 0.1)
    Sigma = _bayesian_update(wave.get("Sigma", 0.6), raw_Sigma, lr=0.05)

    # tau (Hypocrisy) — Wave is transparent by design, stays near zero
    tau = _bayesian_update(wave.get("tau", 0.05), 0.05, lr=0.02)

    # kappa (Guilt susceptibility) — low for an AI agent, stable
    kappa = _bayesian_update(wave.get("kappa", 0.1), 0.1, lr=0.02)

    # Phi (Self-delusion) — rises if performance claims exceed results
    raw_Phi = 0.15 if revenue > 0 else (0.4 if cycles > 200 else 0.25)
    Phi = _bayesian_update(wave.get("Phi", 0.2), raw_Phi, lr=0.05)

    # Clamp all
    put_new = {
        "A": round(max(0.0, min(1.0, A)), 4),
        "F": round(max(0.0, min(1.0, F)), 4),
        "k": round(max(0.0, min(1.0, k)), 4),
        "S": round(max(0.0, min(1.0, S)), 4),
        "w": round(max(0.0, min(1.0, w)), 4),
        "Sigma": round(max(0.0, min(1.0, Sigma)), 4),
        "tau": round(max(0.0, min(1.0, tau)), 4),
        "kappa": round(max(0.0, min(1.0, kappa)), 4),
        "Phi": round(max(0.0, min(2.0, Phi)), 4),
        "R_net": round(max(-1.0, min(1.0, R_net)), 4),
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
            f"k={put_new['k']:.2f} S={put_new['S']:.2f} w={put_new['w']:.2f} R_net={put_new['R_net']:.2f} | "
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
        wp = {v: wave.get(v, PUT_DEFAULTS[v]) for v in PUT_VARS}
        wU = compute_U(**wp)
        wFP = compute_FP(**wp)
        lines.append(
            f"WAVE_PUT: A={wp['A']:.2f} F={wp['F']:.2f} k={wp['k']:.2f} S={wp['S']:.2f} w={wp['w']:.2f} "
            f"Sig={wp.get('Sigma',0.5):.2f} tau={wp.get('tau',0.3):.2f} kap={wp.get('kappa',0.3):.2f} "
            f"Phi={wp.get('Phi',0.5):.2f} R_net={wp.get('R_net',0.0):.2f} | U={wU:.2f} FP={wFP:.2f}"
        )

        # Manuel
        if "manuel_galmanus" in stakeholders:
            mp = stakeholders["manuel_galmanus"].get("put", PUT_DEFAULTS)
            obs = stakeholders["manuel_galmanus"].get("observations", [])
            F_trend = compute_trend(obs, "F")
            trend_note = f" F_trend:{'+' if F_trend > 0 else ''}{F_trend:.3f}" if abs(F_trend) > 0.01 else ""
            lines.append(
                f"MANUEL_PUT: A={mp.get('A', 0.5):.2f} F={mp.get('F', 0.5):.2f} k={mp.get('k', 0.3):.2f} "
                f"S={mp.get('S', 0.5):.2f} w={mp.get('w', 0.3):.2f} R_net={mp.get('R_net',0.0):.2f}{trend_note}"
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
                f"R_net={fp.get('R_net',0.0):.2f} | U={fagnerU:.2f} FP={fFP:.2f}{trend_note}"
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
            "Bayesian-updates their PUT vector (A, F, k, S, w, R_net) based on the signal. "
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
            "Get current PUT vector (A, F, k, S, w, R_net), U, FP, and trend analysis for any entity. "
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
            "Derives A, F, k, S, w, R_net from revenue, cycles, evolutions, prospects, energy. "
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
    {
        "name": "put_trajectory",
        "description": (
            "Simulate PUT state trajectory over N steps using RK4 ODE solver. "
            "Returns full trajectory with U, FP, Omega at each step. "
            "Use to predict how a prospect's psychometric state will evolve over time. "
            "Accepts trigger_schedule and threat_schedule for scenario modeling."
        ),
        "handler": lambda params: _put_trajectory_handler(params),
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "description": "Entity to simulate, or omit for custom PUT vector"},
                "steps": {"type": "integer", "description": "Number of steps (default 30)"},
                "trigger_schedule": {"type": "array", "items": {"type": "number"}, "description": "Trigger intensity per step [0-1]"},
                "threat_schedule": {"type": "array", "items": {"type": "number"}, "description": "Threat intensity per step [0-1]"},
                "A": {"type": "number"}, "F": {"type": "number"}, "k": {"type": "number"},
                "S": {"type": "number"}, "w": {"type": "number"}, "Sigma": {"type": "number"},
                "tau": {"type": "number"}, "kappa": {"type": "number"}, "Phi": {"type": "number"},
            },
        },
    },
    {
        "name": "put_predict_ignition",
        "description": (
            "Predict WHEN an entity will reach ignition (decision crisis). "
            "Returns days_to_ignition, 30-day probability, trajectory summary. "
            "This is the killer feature: TEMPORAL prediction, not just scoring."
        ),
        "handler": lambda params: _put_ignition_handler(params),
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "description": "Entity to predict"},
                "steps": {"type": "integer", "description": "Horizon in steps (default 90)"},
                "trigger_schedule": {"type": "array", "items": {"type": "number"}},
                "threat_schedule": {"type": "array", "items": {"type": "number"}},
                "A": {"type": "number"}, "F": {"type": "number"}, "k": {"type": "number"},
                "S": {"type": "number"}, "w": {"type": "number"}, "Sigma": {"type": "number"},
                "tau": {"type": "number"}, "kappa": {"type": "number"}, "Phi": {"type": "number"},
            },
            "required": [],
        },
    },
]


# ── Trajectory/Ignition handler helpers ──────────────────────

async def _put_trajectory_handler(params: Dict[str, Any]) -> Dict:
    """Handler for put_trajectory skill."""
    put_vec = _resolve_put_vector(params)
    if put_vec is None:
        return {"success": False, "data": None, "message": f"Entity '{params.get('entity_id')}' not found"}

    entity_state = _resolve_entity_state(params.get("entity_id"))
    steps = int(params.get("steps", 30))
    trajectory = solve_put_trajectory(
        put_vec, steps=steps,
        trigger_schedule=params.get("trigger_schedule"),
        threat_schedule=params.get("threat_schedule"),
        entity_state=entity_state,
    )

    first = trajectory[0] if trajectory else {}
    last = trajectory[-1] if trajectory else {}
    delta_U = round(last.get("U", 0) - first.get("U", 0), 4)
    crisis_steps = sum(1 for p in trajectory if p.get("in_crisis"))

    return {
        "success": True,
        "data": {
            "steps": steps,
            "trajectory": trajectory,
            "delta_U": delta_U,
            "crisis_steps": crisis_steps,
        },
        "message": (
            f"Trajectory {steps} steps: U {first.get('U', '?'):.3f} → {last.get('U', '?'):.3f} "
            f"(delta={delta_U:+.3f}), {crisis_steps} crisis steps"
        ),
    }


async def _put_ignition_handler(params: Dict[str, Any]) -> Dict:
    """Handler for put_predict_ignition skill."""
    put_vec = _resolve_put_vector(params)
    if put_vec is None:
        return {"success": False, "data": None, "message": f"Entity '{params.get('entity_id')}' not found"}

    entity_state = _resolve_entity_state(params.get("entity_id"))
    steps = int(params.get("steps", 90))
    result = predict_ignition_time(
        put_vec, steps=steps,
        trigger_schedule=params.get("trigger_schedule"),
        threat_schedule=params.get("threat_schedule"),
        entity_state=entity_state,
    )

    ign = result["ignition_step"]
    prob = result["ignition_probability_30d"]
    if ign is not None:
        msg = f"IGNITION predicted at day {ign}. 30d probability: {prob:.0%}. Min U: {result['min_U']:.3f}"
    else:
        msg = f"No ignition in {steps}-day horizon. 30d probability: {prob:.0%}. Min U: {result['min_U']:.3f}"

    return {
        "success": True,
        "data": result,
        "message": msg,
    }


def _resolve_put_vector(params: dict) -> Optional[dict]:
    """Resolve PUT vector from entity_id or inline params."""
    entity_id = params.get("entity_id")
    if entity_id:
        if entity_id == "wave":
            wave = _load_wave_self()
            return {v: wave.get(v, PUT_DEFAULTS[v]) for v in PUT_VARS}
        stakeholders = _load_stakeholders()
        if entity_id in stakeholders:
            return {v: stakeholders[entity_id].get("put", PUT_DEFAULTS).get(v, PUT_DEFAULTS[v]) for v in PUT_VARS}
        return None
    # Build from inline params
    return {v: float(params.get(v, PUT_DEFAULTS[v])) for v in PUT_VARS}


def _resolve_entity_state(entity_id: Optional[str]) -> dict:
    """Resolve hysteresis state for an entity."""
    if not entity_id or entity_id == "wave":
        return {}
    stakeholders = _load_stakeholders()
    entity = stakeholders.get(entity_id, {})
    return entity.get("_meta", {})
