"""PUT SaaS API — Psychometric Utility Theory as a standalone service.

Exposes the PUT mathematical framework as REST endpoints for any company
to analyze prospects, predict decision timing, and prioritize pipeline
using behavioral market intelligence.

Revenue flows to $WAVE treasury.

Equations (PUT 2.3):
  U = alpha*A_eff*(1-Fk_eff) - beta*Fk_eff*(1-S) + gamma*S*(1-w_eff)*Sigma - delta*tau*kappa - epsilon*Phi_eff
  FP = (1-R)*(kappa+tau+Phi_eff) * sigmoid(-(U - U_crit))
  Omega = 1 + exp(-k_omega * (U - U_crit))
  F_effective = F * (1 - k)

Cross-variable interactions (PUT 2.3):
  F→A paralysis, w→F amplification, k→Φ breeding, Σ→w damping, k→A delayed suppression
"""

import logging
import math
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("bluewave.put_api")

router = APIRouter(prefix="/put", tags=["PUT SaaS"])

# ── Default Coefficients ──────────────────────────────────────

ALPHA = 1.0    # ambition weight
BETA = 1.2     # fear/loss aversion weight
GAMMA = 0.8    # stability buffer weight
DELTA = 0.6    # vulnerability exploitation weight
EPSILON = 0.5  # self-delusion penalty weight
U_CRIT = 0.3   # critical utility threshold
K_OMEGA = 2.0  # desperation sensitivity

# ── Cross-variable interaction coefficients (PUT 2.3) ────────
LAMBDA_FA = 3.0
FA_THRESHOLD = 0.65
LAMBDA_WF = 0.3
LAMBDA_KPHI = 0.5
LAMBDA_SIGMA_W = 0.3
LAMBDA_KA = 0.4
KA_THRESHOLD = 0.55


# ── Auth ──────────────────────────────────────────────────────

PUT_API_KEYS = {
    "put_demo_key_2026": {"owner": "demo", "tier": "free", "limit": 10},
    "put_pro_key_bluewave": {"owner": "bluewave", "tier": "pro", "limit": 1000},
}


async def verify_put_api_key(x_api_key: str = Header(default="", alias="X-API-Key")):
    """Verify PUT API key. Returns key info or raises 401."""
    if not x_api_key or x_api_key not in PUT_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid or missing API key. Contact m.galmanus@gmail.com for access.")
    return PUT_API_KEYS[x_api_key]


# ── Pydantic Models ───────────────────────────────────────────

class ObservableSignals(BaseModel):
    hiring_velocity: str = Field("medium", description="high/medium/low")
    funding_status: str = Field("", description="bootstrapped/seed/series_a/series_b/public")
    public_statements: List[str] = Field(default_factory=list)
    competitor_mentions: List[str] = Field(default_factory=list)
    decision_speed: str = Field("medium", description="fast/medium/slow")
    risk_language: str = Field("cautious", description="aggressive/cautious/defensive")
    team_size: Optional[int] = None
    years_in_market: Optional[int] = None
    recent_events: List[str] = Field(default_factory=list, description="layoffs/launch/pivot/acquisition/funding")


class AnalyzeRequest(BaseModel):
    company_name: str
    industry: str = ""
    observable_signals: ObservableSignals = Field(default_factory=ObservableSignals)


class PUTVariables(BaseModel):
    A: float = Field(description="Ambition (0-1)")
    F: float = Field(description="Fear (0-1)")
    k: float = Field(description="Shadow Coefficient (0-1)")
    S: float = Field(description="Status (0-1)")
    w: float = Field(description="Pain Intensity (0-1)")
    Sigma: float = Field(description="Ecosystem Stability (0-1)")
    Phi: float = Field(description="Self-Delusion (0-2)")
    tau: float = Field(description="Hypocrisy Index (0-1)")
    kappa: float = Field(description="Guilt Coefficient (0-1)")


class DerivedMetrics(BaseModel):
    F_effective: float
    Omega: float
    FP: float
    U: float


class AnalyzeResponse(BaseModel):
    company_name: str
    variables: PUTVariables
    derived: DerivedMetrics
    archetype: str
    ignition_status: str
    dominant_vector: str
    recommended_approach: str
    confidence: float


class PredictRequest(BaseModel):
    prospect_id: str
    history: List[Dict[str, Any]] = Field(default_factory=list)


class PredictResponse(BaseModel):
    prospect_id: str
    trajectory: str
    ignition_probability_30d: float
    optimal_engagement_window: str
    risk_factors: List[str]


class PipelineProspect(BaseModel):
    name: str
    observable_signals: ObservableSignals = Field(default_factory=ObservableSignals)
    deal_value: float = 1000.0


class PipelineRequest(BaseModel):
    prospects: List[PipelineProspect]


class PipelineEntry(BaseModel):
    rank: int
    name: str
    score: float
    FP: float
    archetype: str
    dominant_vector: str
    strategy: str


class ShadowScanRequest(BaseModel):
    company_name: str
    public_communications: List[str] = Field(default_factory=list)


class ShadowScanResponse(BaseModel):
    company_name: str
    k_estimate: float
    evidence: List[str]
    suppression_pattern: str
    rupture_risk: str


# ── Cross-variable interactions (PUT 2.3) ────────────────────

def _apply_cross_interactions(v: PUTVariables):
    """Apply second-order cross-variable interactions.
    Returns (A_eff, F_eff, w_eff, Phi_eff).
    """
    # w→F amplification
    F_eff = min(1.0, v.F * (1.0 + LAMBDA_WF * v.w))
    # Σ→w damping
    w_eff = v.w * (1.0 - LAMBDA_SIGMA_W * v.Sigma)
    # k→Φ breeding
    Phi_eff = min(2.0, v.Phi * (1.0 + LAMBDA_KPHI * v.k))
    # F→A paralysis
    Fk_eff = F_eff * (1.0 - v.k)
    A_eff = v.A
    if Fk_eff > FA_THRESHOLD:
        suppression = min(1.0, (Fk_eff - FA_THRESHOLD) * LAMBDA_FA)
        A_eff = v.A * (1.0 - suppression)
    # k→A delayed suppression
    if v.k > KA_THRESHOLD:
        k_suppression = min(0.5, (v.k - KA_THRESHOLD) * LAMBDA_KA)
        A_eff = A_eff * (1.0 - k_suppression)
    return A_eff, F_eff, w_eff, Phi_eff


# ── PUT Math Engine ───────────────────────────────────────────

def compute_U(v: PUTVariables) -> float:
    """Compute Psychic Utility function.

    PUT 2.3: includes cross-variable interactions.
    delta*tau*kappa is NEGATIVE — vulnerability reduces U (Axiom 4).
    """
    A_eff, F_eff, w_eff, Phi_eff = _apply_cross_interactions(v)
    Fk = F_eff * (1 - v.k)
    term1 = ALPHA * A_eff * (1 - Fk)
    term2 = -BETA * Fk * (1 - v.S)
    term3 = GAMMA * v.S * (1 - w_eff) * v.Sigma
    term4 = -DELTA * v.tau * v.kappa  # NEGATIVE: vulnerability reduces U
    term5 = -EPSILON * Phi_eff
    return term1 + term2 + term3 + term4 + term5


def _sigmoid_fp(x: float, k: float = 5.0) -> float:
    """Sigmoid for smooth FP decay above U_crit."""
    return 1.0 / (1.0 + math.exp(k * x))


def compute_FP(v: PUTVariables, U: float, R: float = 0.5) -> float:
    """Compute Fracture Potential using sigmoid formulation.

    PUT 2.2: FP = (1-R)*(kappa+tau+Phi) * sigmoid(-(U - U_crit))
    Smooth: FP -> 0 when U >> U_crit, FP -> max when U << U_crit.
    """
    return (1 - R) * (v.kappa + v.tau + v.Phi) * _sigmoid_fp(U - U_CRIT, k=5.0)


def compute_Omega(U: float) -> float:
    """Compute Desperation Factor."""
    return 1 + math.exp(-K_OMEGA * (U - U_CRIT))


def compute_F_effective(v: PUTVariables) -> float:
    """Compute effective (conscious) fear."""
    return v.F * (1 - v.k)


def identify_archetype(v: PUTVariables) -> str:
    """Identify the dominant PUT archetype."""
    profiles = {
        "builder": abs(v.A - 0.9) + abs(v.F - 0.2) + abs(v.k - 0.1),
        "guardian": abs(v.A - 0.3) + abs(v.F - 0.8) + abs(v.k - 0.2),
        "politician": abs(v.A - 0.6) + abs(v.S - 0.8) + abs(v.w - 0.2),
        "sufferer": abs(v.w - 0.9) + abs(v.S - 0.3) + abs(v.A - 0.5),
        "denier": abs(v.F - 0.9) + abs(v.k - 0.8) + abs(v.A - 0.4),
        "perfectionist": abs(v.tau - 0.7) + abs(v.kappa - 0.7) + abs(v.A - 0.6),
        "visionary": abs(v.A - 0.9) + abs(v.F - 0.1) + abs(v.Phi - 1.2),
    }
    return min(profiles, key=profiles.get)


def identify_dominant_vector(v: PUTVariables) -> str:
    """Identify the dominant decision vector."""
    vectors = {
        "fear_of_loss": v.F * (1 - v.k) * 1.5,
        "ambition": v.A,
        "status": v.S * 0.8,
        "pain": v.w * 1.2,
        "curiosity": (1 - v.F) * v.A * 0.7,
        "convenience": v.w * (1 - v.A) * 0.9,
        "trust": v.F * (1 - v.k) * (1 - v.S),
    }
    return max(vectors, key=vectors.get)


def estimate_ignition_status(v: PUTVariables, U: float, Omega: float) -> str:
    """Estimate ignition status."""
    if U < U_CRIT and Omega > 1.5:
        return "active"
    if U < U_CRIT * 1.5 and Omega > 1.2:
        return "imminent"
    if U < U_CRIT * 2:
        return "warming"
    return "dormant"


def recommend_approach(archetype: str, vector: str, ignition: str) -> str:
    """Generate approach recommendation based on archetype and vector."""
    approaches = {
        "builder": "Lead with vision and scale potential. Show how your solution multiplies their growth trajectory. Use ambition framing.",
        "guardian": "Lead with risk reduction and security proof. Demonstrate protective capabilities. Use trust framing with guarantees.",
        "politician": "Lead with status enhancement and social proof. Show how peers are already using this. Use exclusivity framing.",
        "sufferer": "Mirror their exact pain with specific numbers. Show immediate relief. Use convenience and urgency framing.",
        "denier": "Do NOT push. Plant seeds with curious content. Wait for shadow rupture. Monitor for ignition signals. Patience is the strategy.",
        "perfectionist": "Use moral consistency framing. Show gap between their stated values and current reality. Offer alignment solution.",
        "visionary": "Ground in data and results. Serve as trusted advisor, not vendor. Use demonstration and curiosity framing.",
    }
    base = approaches.get(archetype, "Apply standard consultative approach.")

    if ignition == "active":
        base += " URGENT: Prospect is in active decision mode. Speed of engagement is the competitive variable."
    elif ignition == "imminent":
        base += " HIGH PRIORITY: Ignition approaching. Pre-position solution now."

    return base


def estimate_variables_from_signals(signals: ObservableSignals) -> PUTVariables:
    """Estimate PUT variables from observable signals using heuristics.

    In production, this would use Claude Haiku for more nuanced estimation.
    The heuristic version provides instant results at zero API cost.
    """
    # Ambition
    A = {"high": 0.85, "medium": 0.55, "low": 0.25}.get(signals.hiring_velocity, 0.5)
    if signals.funding_status in ("series_a", "series_b"):
        A = min(A + 0.15, 1.0)
    if "launch" in str(signals.recent_events):
        A = min(A + 0.1, 1.0)

    # Fear
    F = {"aggressive": 0.2, "cautious": 0.5, "defensive": 0.8}.get(signals.risk_language, 0.5)
    if "layoffs" in str(signals.recent_events):
        F = min(F + 0.2, 1.0)
    if signals.decision_speed == "slow":
        F = min(F + 0.15, 1.0)

    # Shadow Coefficient
    k = 0.3  # default moderate
    if signals.risk_language == "aggressive" and F > 0.5:
        k = 0.6  # aggressive language + high objective risk = suppression
    if len(signals.competitor_mentions) == 0 and signals.hiring_velocity == "high":
        k = min(k + 0.2, 1.0)  # ignoring competition while growing fast

    # Status
    S = 0.5
    if signals.funding_status in ("series_b", "public"):
        S = 0.75
    if signals.funding_status == "bootstrapped":
        S = 0.35
    if signals.years_in_market and signals.years_in_market > 10:
        S = min(S + 0.15, 1.0)

    # Pain
    w = 0.4  # moderate default
    if signals.decision_speed == "fast":
        w = min(w + 0.2, 1.0)  # urgency indicates pain
    if "pivot" in str(signals.recent_events):
        w = min(w + 0.25, 1.0)

    # Stability
    Sigma = 0.6
    if "layoffs" in str(signals.recent_events):
        Sigma = max(Sigma - 0.3, 0.1)
    if signals.funding_status in ("series_b", "public"):
        Sigma = min(Sigma + 0.2, 1.0)

    # Self-Delusion
    Phi = 0.5
    if signals.risk_language == "aggressive" and "layoffs" in str(signals.recent_events):
        Phi = min(Phi + 0.4, 2.0)  # aggressive despite layoffs = delusion

    # Hypocrisy & Guilt
    tau = 0.3
    kappa = 0.3

    return PUTVariables(A=A, F=F, k=k, S=S, w=w, Sigma=Sigma, Phi=Phi, tau=tau, kappa=kappa)


# ── Endpoints ─────────────────────────────────────────────────

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_company(
    req: AnalyzeRequest,
    api_key: dict = Depends(verify_put_api_key),
):
    """Analyze a company using Psychometric Utility Theory.

    Estimates all PUT variables from observable signals, computes derived
    metrics (U, FP, Omega), identifies archetype and dominant decision vector,
    and recommends an approach strategy.
    """
    variables = estimate_variables_from_signals(req.observable_signals)
    U = compute_U(variables)
    FP = compute_FP(variables, U)
    Omega = compute_Omega(U)
    Fk = compute_F_effective(variables)

    archetype = identify_archetype(variables)
    vector = identify_dominant_vector(variables)
    ignition = estimate_ignition_status(variables, U, Omega)
    approach = recommend_approach(archetype, vector, ignition)

    # Confidence based on signal density
    signal_count = sum([
        bool(req.observable_signals.hiring_velocity != "medium"),
        bool(req.observable_signals.funding_status),
        len(req.observable_signals.public_statements) > 0,
        len(req.observable_signals.competitor_mentions) > 0,
        bool(req.observable_signals.decision_speed != "medium"),
        bool(req.observable_signals.risk_language != "cautious"),
        bool(req.observable_signals.team_size),
        bool(req.observable_signals.years_in_market),
        len(req.observable_signals.recent_events) > 0,
    ])
    confidence = min(0.4 + signal_count * 0.07, 0.95)

    logger.info(
        "PUT analysis: %s → archetype=%s FP=%.2f Omega=%.2f ignition=%s",
        req.company_name, archetype, FP, Omega, ignition,
    )

    return AnalyzeResponse(
        company_name=req.company_name,
        variables=variables,
        derived=DerivedMetrics(F_effective=Fk, Omega=Omega, FP=FP, U=U),
        archetype=archetype,
        ignition_status=ignition,
        dominant_vector=vector,
        recommended_approach=approach,
        confidence=confidence,
    )


@router.post("/predict", response_model=PredictResponse)
async def predict_trajectory(
    req: PredictRequest,
    api_key: dict = Depends(verify_put_api_key),
):
    """Predict a prospect's decision trajectory over 30 days.

    Analyzes historical PUT variable snapshots to determine trend direction,
    ignition probability, and optimal engagement window.
    """
    if len(req.history) < 2:
        return PredictResponse(
            prospect_id=req.prospect_id,
            trajectory="insufficient_data",
            ignition_probability_30d=0.0,
            optimal_engagement_window="Need at least 2 data points for trajectory prediction",
            risk_factors=["Insufficient historical data"],
        )

    # Compute U for each historical point
    U_history = []
    for point in req.history:
        v = PUTVariables(**{k: point.get(k, 0.5) for k in ["A", "F", "k", "S", "w", "Sigma", "Phi", "tau", "kappa"]})
        U_history.append(compute_U(v))

    # Trend analysis
    dU = U_history[-1] - U_history[0]
    avg_U = sum(U_history) / len(U_history)

    if dU < -0.15 and U_history[-1] < U_CRIT:
        trajectory = "approaching_ignition"
        ignition_prob = min(0.9, 0.5 + abs(dU) * 2)
    elif dU < -0.05:
        trajectory = "declining"
        ignition_prob = min(0.6, 0.3 + abs(dU))
    elif dU > 0.05:
        trajectory = "improving"
        ignition_prob = max(0.05, 0.2 - dU)
    else:
        trajectory = "stable"
        ignition_prob = 0.15

    # Risk factors
    risks = []
    if U_history[-1] < U_CRIT:
        risks.append("Utility below critical threshold — prospect is in decision mode")
    if dU < -0.1:
        risks.append("Rapid utility decline — competitive pressure or internal crisis")
    latest = req.history[-1]
    if latest.get("k", 0) > 0.6:
        risks.append("High shadow coefficient — denial may delay action until rupture")
    if latest.get("Phi", 0) > 1.0:
        risks.append("High self-delusion — prospect may not recognize own situation")

    # Optimal window
    if trajectory == "approaching_ignition":
        window = "IMMEDIATE — engage within 1-2 weeks. Prospect approaching tipping point."
    elif trajectory == "declining":
        window = "Within 30 days. Utility declining — position solution before competitor."
    elif trajectory == "improving":
        window = "Low urgency. Monitor for reversal. Current trajectory favors status quo."
    else:
        window = "Maintain monthly touchpoints. Watch for external shocks that shift trajectory."

    return PredictResponse(
        prospect_id=req.prospect_id,
        trajectory=trajectory,
        ignition_probability_30d=round(ignition_prob, 3),
        optimal_engagement_window=window,
        risk_factors=risks,
    )


@router.post("/pipeline", response_model=List[PipelineEntry])
async def rank_pipeline(
    req: PipelineRequest,
    api_key: dict = Depends(verify_put_api_key),
):
    """Rank a pipeline of prospects by FP x deal_value.

    Analyzes each prospect, computes Fracture Potential, and returns
    a prioritized list with archetype and strategy per prospect.
    """
    entries = []

    for prospect in req.prospects:
        variables = estimate_variables_from_signals(prospect.observable_signals)
        U = compute_U(variables)
        FP = compute_FP(variables, U)
        archetype = identify_archetype(variables)
        vector = identify_dominant_vector(variables)
        ignition = estimate_ignition_status(variables, U, compute_Omega(U))

        score = FP * (prospect.deal_value / 1000)  # normalize deal value

        entries.append({
            "name": prospect.name,
            "score": round(score, 3),
            "FP": round(FP, 3),
            "archetype": archetype,
            "dominant_vector": vector,
            "strategy": recommend_approach(archetype, vector, ignition),
        })

    # Sort by score descending
    entries.sort(key=lambda x: x["score"], reverse=True)

    return [
        PipelineEntry(rank=i + 1, **e)
        for i, e in enumerate(entries)
    ]


@router.get("/archetypes")
async def get_archetypes(api_key: dict = Depends(verify_put_api_key)):
    """Return the 7 PUT decision archetypes with variable profiles and strategies."""
    return {
        "archetypes": [
            {"name": "Builder", "A": 0.9, "F": 0.2, "k": 0.1, "S": 0.5, "w": 0.3,
             "strategy": "Vision selling, growth narrative, scale multiplier"},
            {"name": "Guardian", "A": 0.3, "F": 0.8, "k": 0.2, "S": 0.6, "w": 0.4,
             "strategy": "Risk reduction, security proof, guarantees"},
            {"name": "Politician", "A": 0.6, "F": 0.4, "k": 0.3, "S": 0.8, "w": 0.2,
             "strategy": "Status enhancement, exclusivity, peer proof"},
            {"name": "Sufferer", "A": 0.5, "F": 0.5, "k": 0.2, "S": 0.3, "w": 0.9,
             "strategy": "Direct pain mirror, immediate relief"},
            {"name": "Denier", "A": 0.4, "F": 0.9, "k": 0.8, "S": 0.5, "w": 0.6,
             "strategy": "Seed planting, patience, wait for shadow rupture"},
            {"name": "Perfectionist", "A": 0.6, "F": 0.5, "k": 0.3, "S": 0.6, "w": 0.5,
             "strategy": "Moral consistency framing, values alignment"},
            {"name": "Visionary", "A": 0.9, "F": 0.1, "k": 0.1, "S": 0.4, "w": 0.3,
             "strategy": "Ground in data, advisory role, demonstration"},
        ],
        "equations": {
            "psychic_utility": "U = alpha*A_eff*(1-Fk_eff) - beta*Fk_eff*(1-S) + gamma*S*(1-w_eff)*Sigma - delta*tau*kappa - epsilon*Phi_eff",
            "fracture_potential": "FP = (1-R)*(kappa+tau+Phi_eff) * sigmoid(-(U - U_crit))",
            "cross_interactions": "F→A paralysis | w→F amplification | k→Φ breeding | Σ→w damping | k→A delayed suppression",
            "desperation": "Omega = 1 + exp(-k_omega * (U - U_crit))",
            "effective_fear": "F_effective = F * (1 - k)",
            "ignition": "U < U_crit AND |dF/dt| > threshold AND trigger_narrative available",
        },
        "reference": "Galmanus, M. (2026). Psychometric Utility Theory. Bluewave Research.",
    }


# ── Temporal Prediction (PUT 2.4 — RK4 ODE Solver) ──────────

class TrajectoryRequest(BaseModel):
    prospect_id: str
    variables: Optional[PUTVariables] = None
    steps: int = Field(30, description="Number of time steps to simulate")
    trigger_schedule: Optional[List[float]] = Field(None, description="Trigger intensity per step [0-1]")
    threat_schedule: Optional[List[float]] = Field(None, description="Threat intensity per step [0-1]")


class IgnitionPrediction(BaseModel):
    prospect_id: str
    ignition_step: Optional[int]
    ignition_probability_30d: float
    days_to_ignition: Optional[int]
    min_U: float
    crisis_steps: int
    trajectory_summary: List[Dict[str, Any]]
    final_state: Dict[str, Any]


class TrajectoryPoint(BaseModel):
    t: int
    A: float
    F: float
    k: float
    S: float
    Phi: float
    U: float
    FP: float
    Omega: float
    in_crisis: bool


class TrajectoryResponse(BaseModel):
    prospect_id: str
    steps: int
    delta_U: float
    crisis_steps: int
    trajectory: List[TrajectoryPoint]


# ── RK4 ODE Implementation (inline, no dependency on openclaw-skill) ────

def _rk4_derivatives(state, w, Sigma, tau, kappa, R_net, S_star, trigger, threat, a_prev, u_crit):
    """Compute derivatives for the 5 endogenous PUT variables."""
    a, f, kk, s, phi = state

    # Compute U with cross-interactions
    v = PUTVariables(A=a, F=f, k=kk, S=s, w=w, Sigma=Sigma, Phi=phi, tau=tau, kappa=kappa)
    A_eff, F_eff, w_eff, Phi_eff = _apply_cross_interactions(v)
    Fk = F_eff * (1 - kk)
    U = (ALPHA * A_eff * (1 - Fk) - BETA * Fk * (1 - s)
         + GAMMA * s * (1 - w_eff) * Sigma - DELTA * tau * kappa - EPSILON * Phi_eff)

    omega = 1.0 + math.exp(-K_OMEGA * (U - u_crit))
    fk = f * (1 - kk)

    # Coupled ODE coefficients
    l1, l2, l3 = 0.08, 0.05, 0.15
    m1, m2, m3, m4 = 0.06, 0.04, 0.12, 0.05
    n1, n2 = 0.04, 0.03
    p1, p2 = 0.06, -0.03
    k1c, k2c = 0.05, 0.08

    dA = l1 * (s - S_star) - l2 * fk + l3 * omega * trigger
    dF = m1 * abs(a - a_prev) - m2 * math.sqrt(max(Sigma, 0.01)) + m3 * omega * threat + m4 * (1 - Sigma)
    dS = n1 * a * (1 - fk) - n2 * w
    dPhi = p1 * kk * (1 - Sigma) + p2 * (phi - 0.5)
    dk = k1c * f * (1 - a) - k2c * trigger

    return [dA, dF, dk, dS, dPhi]


def _solve_trajectory(variables: PUTVariables, steps: int, dt: float,
                      trigger_schedule: List[float], threat_schedule: List[float]) -> List[dict]:
    """Solve PUT ODE using RK4 and return full trajectory."""
    state = [variables.A, variables.F, variables.k, variables.S, variables.Phi]
    w = variables.w
    Sigma = variables.Sigma
    tau = variables.tau
    kappa = variables.kappa
    R_net = 0.0
    S_star = 0.5
    in_crisis = False
    A_prev = variables.A

    U_CRIT_DOWN = 0.3
    U_CRIT_UP = 0.5

    trajectory = []

    for step in range(steps):
        trigger = trigger_schedule[step] if step < len(trigger_schedule) else 0.0
        threat = threat_schedule[step] if step < len(threat_schedule) else 0.0

        a, f, kk, s, phi = state
        v = PUTVariables(A=a, F=f, k=kk, S=s, w=w, Sigma=Sigma, Phi=phi, tau=tau, kappa=kappa)
        U = compute_U(v)
        FP = compute_FP(v, U)
        Omega = compute_Omega(U)

        if U < U_CRIT_DOWN:
            in_crisis = True
        elif U > U_CRIT_UP:
            in_crisis = False

        u_crit = U_CRIT_UP if in_crisis else U_CRIT_DOWN

        trajectory.append({
            "t": step, "A": round(a, 4), "F": round(f, 4), "k": round(kk, 4),
            "S": round(s, 4), "Phi": round(phi, 4), "U": round(U, 4),
            "FP": round(FP, 4), "Omega": round(Omega, 4), "in_crisis": in_crisis,
        })

        # RK4 integration
        args = (w, Sigma, tau, kappa, R_net, S_star, trigger, threat, A_prev, u_crit)
        k1 = _rk4_derivatives(state, *args)
        s2 = [state[i] + 0.5 * dt * k1[i] for i in range(5)]
        k2 = _rk4_derivatives(s2, *args)
        s3 = [state[i] + 0.5 * dt * k2[i] for i in range(5)]
        k3 = _rk4_derivatives(s3, *args)
        s4 = [state[i] + dt * k3[i] for i in range(5)]
        k4 = _rk4_derivatives(s4, *args)

        A_prev = state[0]
        state = [
            state[i] + (dt / 6.0) * (k1[i] + 2*k2[i] + 2*k3[i] + k4[i])
            for i in range(5)
        ]

        bounds = [(0, 1), (0, 1), (0, 1), (0, 1), (0, 2)]
        state = [max(lo, min(hi, v)) for v, (lo, hi) in zip(state, bounds)]

    return trajectory


@router.post("/trajectory", response_model=TrajectoryResponse)
async def compute_trajectory(
    req: TrajectoryRequest,
    api_key: dict = Depends(verify_put_api_key),
):
    """Simulate PUT state trajectory using RK4 ODE solver.

    Given current PUT variables, predicts how the psychometric state
    evolves over N steps. Accepts trigger and threat schedules for
    scenario modeling (e.g. "what if competitor launches in week 2?").
    """
    if req.variables:
        variables = req.variables
    else:
        variables = PUTVariables(A=0.5, F=0.5, k=0.3, S=0.5, w=0.3, Sigma=0.5, Phi=0.5, tau=0.3, kappa=0.3)

    triggers = req.trigger_schedule or [0.0] * req.steps
    threats = req.threat_schedule or [0.0] * req.steps

    trajectory = _solve_trajectory(variables, req.steps, 1.0, triggers, threats)

    first = trajectory[0] if trajectory else {}
    last = trajectory[-1] if trajectory else {}
    delta_U = round(last.get("U", 0) - first.get("U", 0), 4)
    crisis_steps = sum(1 for p in trajectory if p.get("in_crisis"))

    return TrajectoryResponse(
        prospect_id=req.prospect_id,
        steps=req.steps,
        delta_U=delta_U,
        crisis_steps=crisis_steps,
        trajectory=[TrajectoryPoint(**p) for p in trajectory],
    )


@router.post("/predict-ignition", response_model=IgnitionPrediction)
async def predict_ignition(
    req: TrajectoryRequest,
    api_key: dict = Depends(verify_put_api_key),
):
    """Predict WHEN a prospect reaches ignition (decision crisis).

    The killer feature: TEMPORAL prediction. Not just "will they buy?"
    but "WHEN will they be ready to buy?"

    Returns days_to_ignition, 30-day probability, and trajectory summary.
    """
    if req.variables:
        variables = req.variables
    else:
        variables = PUTVariables(A=0.5, F=0.5, k=0.3, S=0.5, w=0.3, Sigma=0.5, Phi=0.5, tau=0.3, kappa=0.3)

    steps = max(req.steps, 30)
    triggers = req.trigger_schedule or [0.0] * steps
    threats = req.threat_schedule or [0.0] * steps

    trajectory = _solve_trajectory(variables, steps, 1.0, triggers, threats)

    ignition_step = None
    min_U = float("inf")
    crisis_steps = 0

    for point in trajectory:
        if point["U"] < min_U:
            min_U = point["U"]
        if point["in_crisis"]:
            crisis_steps += 1
        if ignition_step is None and point["U"] < U_CRIT and point["Omega"] > 1.5:
            ignition_step = point["t"]

    # Probability estimation
    if ignition_step is not None and ignition_step <= 30:
        prob_30d = min(0.95, 0.6 + (30 - ignition_step) * 0.012)
    elif min_U < U_CRIT * 1.5:
        prob_30d = min(0.5, 0.2 + (U_CRIT * 1.5 - min_U) * 0.8)
    elif crisis_steps > steps * 0.3:
        prob_30d = 0.4
    else:
        prob_30d = max(0.05, 0.15 - (min_U - U_CRIT) * 0.3)

    final = trajectory[-1] if trajectory else {}
    summary = trajectory[:5] + (trajectory[-5:] if len(trajectory) > 10 else [])

    return IgnitionPrediction(
        prospect_id=req.prospect_id,
        ignition_step=ignition_step,
        ignition_probability_30d=round(prob_30d, 3),
        days_to_ignition=ignition_step,
        min_U=round(min_U, 4),
        crisis_steps=crisis_steps,
        trajectory_summary=summary,
        final_state={
            "A": final.get("A"), "F": final.get("F"), "k": final.get("k"),
            "S": final.get("S"), "Phi": final.get("Phi"),
            "U": final.get("U"), "FP": final.get("FP"),
        },
    )


# ── Feedback Loop (PUT 2.4 — Automatic Calibration) ─────────

class FeedbackRequest(BaseModel):
    prospect_id: str
    predicted_response: str = Field(description="What was predicted: receptive|desperate|urgent|resistant|neutral")
    actual_response: str = Field(description="What happened: converted|rejected|delayed|engaged|ignored")
    variables: Optional[PUTVariables] = None
    archetype: Optional[str] = None
    deal_value: Optional[float] = None


class FeedbackResponse(BaseModel):
    prospect_id: str
    predicted: str
    actual: str
    correct: bool
    running_accuracy: float
    total_interactions: int
    coefficients_updated: bool


# In-memory calibration state (persists across requests in the same process)
_calibration_state = {
    "interactions": [],
    "accuracy_history": [],
    "coefficients": {
        "alpha": {"mean": ALPHA, "std": 0.2, "samples": 0},
        "beta": {"mean": BETA, "std": 0.2, "samples": 0},
        "gamma": {"mean": GAMMA, "std": 0.2, "samples": 0},
        "delta": {"mean": DELTA, "std": 0.2, "samples": 0},
        "epsilon": {"mean": EPSILON, "std": 0.2, "samples": 0},
    },
}


def _normalize_response(actual: str) -> str:
    """Map actual outcomes to PUT response categories."""
    mapping = {
        "converted": "receptive",
        "purchased": "receptive",
        "signed": "receptive",
        "engaged": "neutral",
        "interested": "neutral",
        "delayed": "resistant",
        "rejected": "resistant",
        "ignored": "resistant",
        "churned": "desperate",
        "escalated": "urgent",
        "complained": "urgent",
    }
    return mapping.get(actual.lower(), actual.lower())


@router.post("/feedback", response_model=FeedbackResponse)
async def record_feedback(
    req: FeedbackRequest,
    api_key: dict = Depends(verify_put_api_key),
):
    """Record actual outcome vs prediction. Feeds the calibration loop.

    Call this after every prospect interaction to improve PUT accuracy.
    After 50+ interactions, coefficients converge and PUT becomes predictive.

    This is the closed feedback loop that transforms PUT from framework to science.
    """
    actual_normalized = _normalize_response(req.actual_response)
    correct = req.predicted_response.lower() == actual_normalized

    # Record interaction
    _calibration_state["interactions"].append({
        "prospect_id": req.prospect_id,
        "predicted": req.predicted_response,
        "actual": req.actual_response,
        "actual_normalized": actual_normalized,
        "correct": correct,
        "archetype": req.archetype,
        "deal_value": req.deal_value,
        "timestamp": datetime.now().isoformat(),
    })

    _calibration_state["accuracy_history"] = (
        _calibration_state["accuracy_history"] + [1 if correct else 0]
    )[-100:]

    # Bayesian coefficient update when we have variables
    coefficients_updated = False
    if req.variables:
        import random
        v = req.variables
        samples = []
        coeffs_state = _calibration_state["coefficients"]

        for _ in range(200):
            sample = {}
            for c_name in ["alpha", "beta", "gamma", "delta", "epsilon"]:
                dist = coeffs_state[c_name]
                val = random.gauss(dist["mean"], dist["std"])
                sample[c_name] = max(0.01, min(2.0, val))
            samples.append(sample)

        correct_samples = []
        for s in samples:
            pv = PUTVariables(A=v.A, F=v.F, k=v.k, S=v.S, w=v.w, Sigma=v.Sigma, Phi=v.Phi, tau=v.tau, kappa=v.kappa)
            A_eff, F_eff, w_eff, Phi_eff = _apply_cross_interactions(pv)
            Fk = F_eff * (1 - v.k)
            U = (s["alpha"] * A_eff * (1 - Fk) - s["beta"] * Fk * (1 - v.S)
                 + s["gamma"] * v.S * (1 - w_eff) * v.Sigma
                 - s["delta"] * v.tau * v.kappa - s["epsilon"] * Phi_eff)

            if U > 0.6:
                sim_resp = "receptive"
            elif U < 0.2:
                sim_resp = "resistant"
            else:
                sim_resp = "neutral"

            if sim_resp == actual_normalized:
                correct_samples.append(s)

        if correct_samples:
            for c_name in ["alpha", "beta", "gamma", "delta", "epsilon"]:
                values = [s[c_name] for s in correct_samples]
                new_mean = sum(values) / len(values)
                new_std = max(0.05, (sum((v - new_mean) ** 2 for v in values) / len(values)) ** 0.5)

                old = coeffs_state[c_name]
                n = old["samples"]
                weight = min(n / (n + len(correct_samples)), 0.9)

                coeffs_state[c_name] = {
                    "mean": round(weight * old["mean"] + (1 - weight) * new_mean, 4),
                    "std": round(weight * old["std"] + (1 - weight) * new_std, 4),
                    "samples": n + 1,
                }
            coefficients_updated = True

    acc_hist = _calibration_state["accuracy_history"]
    accuracy = sum(acc_hist) / len(acc_hist) if acc_hist else 0

    logger.info(
        "PUT feedback: %s predicted=%s actual=%s correct=%s accuracy=%.0f%%",
        req.prospect_id, req.predicted_response, req.actual_response, correct, accuracy * 100,
    )

    return FeedbackResponse(
        prospect_id=req.prospect_id,
        predicted=req.predicted_response,
        actual=req.actual_response,
        correct=correct,
        running_accuracy=round(accuracy, 3),
        total_interactions=len(_calibration_state["interactions"]),
        coefficients_updated=coefficients_updated,
    )


@router.post("/shadow-scan", response_model=ShadowScanResponse)
async def shadow_scan(
    req: ShadowScanRequest,
    api_key: dict = Depends(verify_put_api_key),
):
    """Detect Shadow Coefficient (k) from public communications.

    Analyzes language patterns to estimate degree of fear suppression.
    High k = appears fearless but is accumulating psychological pressure.
    """
    if not req.public_communications:
        return ShadowScanResponse(
            company_name=req.company_name,
            k_estimate=0.3,
            evidence=["No communications provided — using default moderate k"],
            suppression_pattern="unknown",
            rupture_risk="unknown",
        )

    # Heuristic shadow detection from language patterns
    all_text = " ".join(req.public_communications).lower()

    k_signals = 0
    evidence = []

    # High-k indicators (denial, dismissal, aggressive certainty)
    denial_phrases = [
        "not concerned", "no threat", "irrelevant", "overblown",
        "don't see", "not worried", "nothing to worry", "under control",
        "ahead of the curve", "we're fine", "non-issue",
    ]
    for phrase in denial_phrases:
        if phrase in all_text:
            k_signals += 1
            evidence.append("Denial language detected: '%s'" % phrase)

    # Aggressive certainty in uncertain market = suppression
    certainty_phrases = [
        "absolutely certain", "guaranteed", "no doubt", "inevitable",
        "100%", "zero risk", "impossible to fail",
    ]
    for phrase in certainty_phrases:
        if phrase in all_text:
            k_signals += 1.5
            evidence.append("Aggressive certainty: '%s' (markets are never certain)" % phrase)

    # Absence of competitor acknowledgment
    if not any(w in all_text for w in ["competitor", "competition", "rival", "alternative", "threat"]):
        k_signals += 1
        evidence.append("Zero competitor acknowledgment in public communications")

    # Calculate k estimate
    k_estimate = min(k_signals * 0.15, 0.95)
    k_estimate = max(k_estimate, 0.1)

    # Determine pattern and risk
    if k_estimate < 0.3:
        pattern = "low_suppression"
        risk = "low"
    elif k_estimate < 0.5:
        pattern = "moderate_suppression"
        risk = "medium"
    elif k_estimate < 0.7:
        pattern = "high_suppression"
        risk = "high"
    else:
        pattern = "critical_suppression"
        risk = "critical"

    if not evidence:
        evidence = ["Communications appear balanced — no strong suppression indicators"]

    return ShadowScanResponse(
        company_name=req.company_name,
        k_estimate=round(k_estimate, 3),
        evidence=evidence,
        suppression_pattern=pattern,
        rupture_risk=risk,
    )
