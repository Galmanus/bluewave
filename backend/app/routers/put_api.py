"""PUT SaaS API — Psychometric Utility Theory as a standalone service.

Exposes the PUT mathematical framework as REST endpoints for any company
to analyze prospects, predict decision timing, and prioritize pipeline
using behavioral market intelligence.

Revenue flows to $WAVE treasury.

Equations:
  U = alpha*A*(1-Fk) - beta*Fk*(1-S) + gamma*S*(1-w)*Sigma + delta*tau*kappa - epsilon*Phi
  FP = [(1-R)*(kappa+tau+Phi)] / (U_crit - U + epsilon)
  Omega = 1 + exp(-k_omega * (U - U_crit))
  F_effective = F * (1 - k)
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


# ── PUT Math Engine ───────────────────────────────────────────

def compute_U(v: PUTVariables) -> float:
    """Compute Psychic Utility function."""
    Fk = v.F * (1 - v.k)
    term1 = ALPHA * v.A * (1 - Fk)
    term2 = -BETA * Fk * (1 - v.S)
    term3 = GAMMA * v.S * (1 - v.w) * v.Sigma
    term4 = DELTA * v.tau * v.kappa
    term5 = -EPSILON * v.Phi
    return term1 + term2 + term3 + term4 + term5


def compute_FP(v: PUTVariables, U: float, R: float = 0.5) -> float:
    """Compute Fracture Potential."""
    numerator = (1 - R) * (v.kappa + v.tau + v.Phi)
    denominator = max(U_CRIT - U + 1e-3, 1e-3)
    return numerator / denominator


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
            "psychic_utility": "U = alpha*A*(1-Fk) - beta*Fk*(1-S) + gamma*S*(1-w)*Sigma + delta*tau*kappa - epsilon*Phi",
            "fracture_potential": "FP = [(1-R)*(kappa+tau+Phi)] / (U_crit - U + epsilon)",
            "desperation": "Omega = 1 + exp(-k_omega * (U - U_crit))",
            "effective_fear": "F_effective = F * (1 - k)",
            "ignition": "U < U_crit AND |dF/dt| > threshold AND trigger_narrative available",
        },
        "reference": "Galmanus, M. (2026). Psychometric Utility Theory. Bluewave Research.",
    }


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
