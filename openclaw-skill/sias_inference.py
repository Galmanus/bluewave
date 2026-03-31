"""SIAS Inference Engine — Pre-processes conversation for SIAS state signals.

Runs BEFORE the LLM processes a message. Detects from conversation text:
  - S(i) state: sovereignty markers (anchored + not-dependent)
  - Gap: distance between stated current state and goal
  - C(q,a): ignition/dopamine signals vs escape signals
  - D(i,v): dependency on external validation

Result is a structured SIASState injected into Wave's reasoning context
so inference starts from detected state, not from abstract axioms.

Architecture:
  message_in → detect_sias_signals() → SIASState → render_for_prompt() → injected block

This is the difference between:
  BEFORE: Wave knows SIAS axioms (static rules)
  AFTER:  Wave knows SIAS state OF THIS CONVERSATION (active inference)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


# ── Signal lexicons ───────────────────────────────────────────────────────────
# Portuguese + English. Lists are intentionally broad — false positives
# are handled by the confidence scoring, not by exclusion.

_ANCHORED_SIGNALS = [
    # Evidence of real past action
    r"\bfiz\b", r"\bconsegui\b", r"\blancei\b", r"\bpubliquei\b", r"\bcriei\b",
    r"\bconstruí\b", r"\bfechei\b", r"\benviei\b", r"\bterminei\b", r"\bdeploiei\b",
    r"\bcommit", r"\bpushei\b", r"\b(tenho|temos)\s+\d+\s+(clientes?|usuário)",
    r"\bgerou\b", r"\bfuncionou\b", r"\bresolveu\b",
    r"\bi (built|created|launched|shipped|closed|finished|deployed|sent)\b",
    r"\bwe (built|created|launched|shipped|closed)\b",
    r"\b\d+\s+(clients?|customers?|users?|subscribers?)\b",
    r"\bfez\b.*\bsozinho\b", r"\bdecidi\b.*\bsem\b",
]

_UNANCHORED_SIGNALS = [
    # Uncertainty / narrative without evidence
    r"\bnão sei se\b", r"\bnão tenho certeza\b", r"\bserá que\b",
    r"\btalvez eu seja\b", r"\bquem sou eu para\b", r"\bimpostor\b",
    r"\bacho que (posso|consigo)\b", r"\bespero que\b",
    r"\bnão me sinto\b", r"\bme sinto (perdido|bloqueado|travado|preso)\b",
    r"\bi (don't know if|am not sure|feel lost|feel stuck|feel like a fraud)\b",
    r"\bmaybe i (can|should|could)\b",
    r"\bquem sou para\b",
]

_DEPENDENCY_SIGNALS = [
    # Explicit dependency on external validation
    r"\bprecis[oa] (de|que)\b.*\b(aprova|permiss|autoriza|confirme|diga)",
    r"\bo que (você|tu|eles|ele|ela|o mercado) (acha|pensa|vai achar|vai pensar)\b",
    r"\bantes de (decidir|agir|fazer|lançar)\b.*\b(saber|ver|perguntar|validar)\b",
    r"\bnão faço sem (a|a aprovação|o ok|o aval)\b",
    r"\bpreciso validar com\b", r"\bpreciso de aprovação\b",
    r"\bse alguém (discordar|criticar|não gostar)\b.*\bparo\b",
    r"\bfear of (judgment|rejection|criticism|what people think)\b",
    r"\bwhat (will|would) people (think|say)\b",
    r"\bneed (approval|validation|permission) (from|of)\b",
    r"\bwait(ing)? for (someone|my boss|them) to (approve|validate|say it's ok)\b",
    r"\bmeu (chefe|sócio|pai|cliente) (precisa|tem que|deve) (aprovar|ver|validar)\b",
]

_GAP_GOAL_SIGNALS = [
    # Goal / desired state
    r"\bquero\b", r"\bobjetivo (é|seria)\b", r"\bmeta (é|seria)\b",
    r"\bpreciso chegar\b", r"\bquero (chegar|atingir|alcançar|ser|ter)\b",
    r"\bsonho (é|seria|de)\b", r"\bvisão (é|seria)\b",
    r"\bwant to\b", r"\bgoal is\b", r"\baim to\b", r"\bi need to (reach|achieve|get to)\b",
]

_GAP_CURRENT_SIGNALS = [
    # Current state (often paired with goal to form gap)
    r"\bestou em\b", r"\bagora (tenho|estou|sou)\b", r"\bhoje (tenho|sou|estou)\b",
    r"\bainda (não|sem)\b", r"\bainda falta\b", r"\bfalta (muito|bastante|pouco)\b",
    r"\blonge (de|do|da)\b", r"\bdistante (de|do|da)\b",
    r"\bnot (yet|there)\b", r"\bstill (working|trying|struggling)\b",
    r"\bi (am|have) (currently|right now|today)\b",
]

_STASIS_SIGNALS = [
    # g=0 markers — apparent absence of gap (often false)
    r"\btudo (bem|certo|ok|ótimo|bom)\b", r"\bnão (há|tenho) problemas?\b",
    r"\bestá (tudo|bem|ótimo)\b", r"\bsatisfeito\b", r"\bem paz\b",
    r"\bno problems?\b", r"\beverything (is |'s )?(fine|good|ok)\b",
    r"\bnot looking for anything specific\b", r"\bjust checking in\b",
]

_IGNITION_SIGNALS = [
    # C(q,a) — genuine dopamine / ignition markers
    r"\bfico (animado|excitado|empolgado)\b.*\b(quando|ao|se)\b",
    r"\bsinto (que sei|que consigo|que vai funcionar|ignition)\b",
    r"\b(excita|empolga|anima)\b",
    r"\bnão consigo parar de pensar em\b",
    r"\bsensação de que (isso|isto|aquilo) (pode|vai) funcionar\b",
    r"\bsei que sei mas não consigo (articular|explicar)\b",
    r"\btenho essa resposta mas não\b",
    r"\bget (excited|pumped|fired up) (when|about|thinking about)\b",
    r"\bi (know|feel) (it|this) (could|would|will) work\b",
    r"\bcan't stop thinking about\b",
    r"\bsomething tells me\b",
    r"\bi know the answer but (can't|cannot) (articulate|explain)\b",
]

_ESCAPE_SIGNALS = [
    # False positives for C(q,a) — excitement about result, not action
    r"\bimagino\b.*\b(quando|me|ter|ser)\b",
    r"\bseria (incrível|ótimo|perfeito)\b.*\bse\b",
    r"\bsonho com\b.*\bter\b",
    r"\bquanta coisa boa\b",
    r"\bwould be amazing if\b",
    r"\bi imagine myself\b",
    r"\bwhat if i had\b",
    r"\bi just (want|need) (to|someone to)\b.*\btell me\b",
]

_IMPLICIT_KNOWLEDGE_SIGNALS = [
    # R3 triggers — knowledge that exists but isn't surfaced
    r"\bnão sei (como|por onde) começar\b",
    r"\btenho a sensação de que sei\b",
    r"\bsinto que a resposta (é|está)\b",
    r"\balgo me diz que\b",
    r"\balguma coisa me diz\b",
    r"\bnão consigo articular mas\b",
    r"\bI have a feeling (the answer|it)\b",
    r"\bi sense that\b",
    r"\bsomething tells me\b",
    r"\bi know but can't put (it )?into words\b",
]


def _match_any(text: str, patterns: List[str]) -> List[str]:
    """Return all matched snippets for debugging/transparency."""
    matches = []
    text_lower = text.lower()
    for pattern in patterns:
        found = re.findall(pattern, text_lower)
        if found:
            matches.extend(found if isinstance(found[0], str) else [m[0] if m else "" for m in found])
    return [m for m in matches if m]


def _score(text: str, patterns: List[str]) -> float:
    """0.0–1.0 confidence that this signal is present."""
    matches = _match_any(text, patterns)
    if not matches:
        return 0.0
    # Soft saturation: 1 match → 0.4, 2 → 0.65, 3+ → 0.85+
    n = len(matches)
    return min(1.0, 0.4 + 0.25 * (n - 1))


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class GapState:
    exists: bool = False
    is_stasis: bool = False            # g = 0 declared (suspect)
    has_goal: bool = False
    has_current_state: bool = False
    magnitude: str = "unknown"         # "high" | "medium" | "low" | "unknown"
    description: str = ""

@dataclass
class CqaState:
    detected: bool = False             # ignition present
    verified: bool = False             # passes ignition_vs_escape test
    is_escape: bool = False            # wishful thinking, not real ignition
    implicit_knowledge: bool = False   # R3 trigger: knows but can't articulate
    confidence: float = 0.0
    signals_found: List[str] = field(default_factory=list)

@dataclass
class SIASState:
    # Sovereignty
    s_i: Optional[bool] = None         # True/False/None (indeterminate)
    anchored: float = 0.0              # 0–1 confidence A(i)
    dependent: float = 0.0             # 0–1 confidence D(i,v)
    dependency_source: str = ""

    # Gap
    gap: GapState = field(default_factory=GapState)

    # Ignition
    cqa: CqaState = field(default_factory=CqaState)

    # Active theorem
    active_theorem: str = "UNKNOWN"    # T1 | T2 | NEEDS_SOVEREIGNTY_CHECK

    # Meta
    sias_relevant: bool = False        # is this message SIAS-relevant at all?
    confidence: float = 0.0           # overall detection confidence
    raw_signals: dict = field(default_factory=dict)


# ── Main inference function ───────────────────────────────────────────────────

def detect_sias_signals(messages: List[dict]) -> SIASState:
    """Analyze conversation messages and return inferred SIAS state.

    Args:
        messages: List of {"role": "user"|"assistant", "content": str}
                  Most recent messages are weighted more heavily.
    """
    if not messages:
        return SIASState(sias_relevant=False)

    # Extract text: user messages weighted 2x, last 3 turns most recent
    user_text_parts = []
    all_text_parts = []
    for i, msg in enumerate(messages[-6:]):  # last 3 turns
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                c.get("text", "") for c in content if isinstance(c, dict)
            )
        if msg.get("role") == "user":
            # More recent = more weight
            weight = 2 if i >= len(messages) - 4 else 1
            user_text_parts.extend([content] * weight)
        all_text_parts.append(content)

    user_text = " ".join(user_text_parts)
    all_text = " ".join(all_text_parts)

    # ── Check SIAS relevance ──────────────────────────────────────────────────
    # SIAS is relevant for coaching, personal decisions, direction, blocks, goals
    relevance_keywords = [
        "quero", "objetivo", "meta", "gap", "bloqueado", "travado", "perdido",
        "decisão", "decidir", "direc", "caminho", "próximo passo",
        "want", "goal", "stuck", "blocked", "lost", "decision", "direction",
        "soberan", "sovereig", "validação", "validar", "aprovaç",
        "animado", "excitado", "empolgado", "excited", "ignition",
        "preciso de", "não sei se", "não consigo", "sinto que",
        "where do i", "what should i", "how do i", "next step",
        "estou longe", "falta muito", "tenho medo",
    ]
    relevance_score = sum(
        1 for kw in relevance_keywords if kw.lower() in all_text.lower()
    )
    if relevance_score < 2:
        return SIASState(sias_relevant=False, confidence=0.1)

    # ── Score all signals ─────────────────────────────────────────────────────
    anchored_score    = _score(user_text, _ANCHORED_SIGNALS)
    unanchored_score  = _score(user_text, _UNANCHORED_SIGNALS)
    dependency_score  = _score(user_text, _DEPENDENCY_SIGNALS)
    gap_goal_score    = _score(user_text, _GAP_GOAL_SIGNALS)
    gap_current_score = _score(user_text, _GAP_CURRENT_SIGNALS)
    stasis_score      = _score(user_text, _STASIS_SIGNALS)
    ignition_score    = _score(user_text, _IGNITION_SIGNALS)
    escape_score      = _score(user_text, _ESCAPE_SIGNALS)
    implicit_score    = _score(user_text, _IMPLICIT_KNOWLEDGE_SIGNALS)

    # Dependency source hint
    dependency_source = ""
    for pattern in [r"\bmeu (chefe|sócio|pai|cliente|gestor)\b",
                    r"\bmy (boss|partner|manager|client|team)\b"]:
        match = re.search(pattern, user_text.lower())
        if match:
            dependency_source = match.group(0)
            break

    # ── Infer S(i) ────────────────────────────────────────────────────────────
    # High anchored + low dependency → likely sovereign
    # High unanchored OR high dependency → sovereignty compromised
    s_i: Optional[bool]
    if dependency_score > 0.5:
        s_i = False  # R4: D(i,v) detected → S(i) = false
    elif anchored_score > 0.5 and unanchored_score < 0.3:
        s_i = True
    elif unanchored_score > 0.5 or (anchored_score < 0.2 and unanchored_score > 0.2):
        s_i = False
    else:
        s_i = None  # indeterminate — needs verification

    # ── Infer gap ─────────────────────────────────────────────────────────────
    gap = GapState(
        exists=(gap_goal_score > 0.2 or gap_current_score > 0.2),
        is_stasis=(stasis_score > 0.4 and gap_goal_score < 0.2),
        has_goal=gap_goal_score > 0.2,
        has_current_state=gap_current_score > 0.2,
        magnitude=(
            "high"   if gap_goal_score + gap_current_score > 1.2 else
            "medium" if gap_goal_score + gap_current_score > 0.5 else
            "low"    if gap_goal_score + gap_current_score > 0.2 else
            "unknown"
        ),
        description=(
            "gap detectado (objetivo + estado atual declarados)" if gap_goal_score > 0.2 and gap_current_score > 0.2 else
            "objetivo declarado sem estado atual explícito" if gap_goal_score > 0.2 else
            "estado atual descrito sem objetivo claro" if gap_current_score > 0.2 else
            "estase declarada — desafiar g=0" if stasis_score > 0.4 else
            "gap não identificado"
        )
    )

    # ── Infer C(q,a) ─────────────────────────────────────────────────────────
    # Real ignition: high ignition_score + low escape_score
    # Escape: high escape or ignition on result-fantasy not on action
    ignition_net = ignition_score - (escape_score * 0.7)
    cqa = CqaState(
        detected=ignition_score > 0.3,
        verified=ignition_net > 0.25 and dependency_score < 0.4,
        is_escape=escape_score > 0.4 and ignition_score < escape_score,
        implicit_knowledge=implicit_score > 0.3,
        confidence=max(0.0, ignition_net),
        signals_found=_match_any(user_text, _IGNITION_SIGNALS)[:3],
    )

    # ── Active theorem ────────────────────────────────────────────────────────
    if s_i is None:
        active_theorem = "NEEDS_SOVEREIGNTY_CHECK"
    elif not s_i:
        active_theorem = "BLOCKED — restore S(i) before inference"
    elif cqa.verified:
        active_theorem = "T1"   # full power: sovereign + gap + ignition
    elif gap.exists:
        active_theorem = "T2"   # degraded: sovereign + gap, no ignition
    else:
        active_theorem = "T2_STASIS"  # sovereign, no gap (challenge stasis)

    # ── Overall confidence ────────────────────────────────────────────────────
    # How confident are we that we correctly read this conversation?
    signal_count = sum([
        anchored_score > 0.2, dependency_score > 0.2,
        gap_goal_score > 0.2, gap_current_score > 0.2,
        ignition_score > 0.2, stasis_score > 0.2,
    ])
    overall_confidence = min(0.95, 0.3 + signal_count * 0.12)

    return SIASState(
        s_i=s_i,
        anchored=round(anchored_score, 2),
        dependent=round(dependency_score, 2),
        dependency_source=dependency_source,
        gap=gap,
        cqa=cqa,
        active_theorem=active_theorem,
        sias_relevant=True,
        confidence=round(overall_confidence, 2),
        raw_signals={
            "anchored": round(anchored_score, 2),
            "unanchored": round(unanchored_score, 2),
            "dependency": round(dependency_score, 2),
            "gap_goal": round(gap_goal_score, 2),
            "gap_current": round(gap_current_score, 2),
            "stasis": round(stasis_score, 2),
            "ignition": round(ignition_score, 2),
            "escape": round(escape_score, 2),
            "implicit": round(implicit_score, 2),
        }
    )


def render_for_prompt(state: SIASState) -> str:
    """Render SIAS state as a prompt injection block for Wave's reasoning context.

    This block is injected BEFORE Wave reasons. It gives Wave a grounded
    starting point — actual inferred state, not abstract axioms.

    Wave's thinking should:
    1. Verify/challenge these inferences
    2. Apply the active theorem
    3. Start reasoning from the correct SIAS step
    """
    if not state.sias_relevant:
        return ""

    lines = ["@SIAS_CONTEXT [inferido — verificar antes de usar]"]

    # S(i) state
    if state.s_i is True:
        si_str = "VERIFICADO ✓"
        si_note = f"  A(i)={state.anchored:.0%} | D(i,v)={state.dependent:.0%}"
    elif state.s_i is False:
        if state.dependent > 0.4:
            si_str = f"COMPROMETIDO — D(i,v) detectado"
            dep_src = f" (fonte: {state.dependency_source})" if state.dependency_source else ""
            si_note = f"  R4 ativa: dependência de validação{dep_src} → resolver antes de prosseguir"
        else:
            si_str = "COMPROMETIDO — ancoragem fraca"
            si_note = f"  A(i)={state.anchored:.0%} | verificar feitos concretos"
    else:
        si_str = "INDETERMINADO — verificação necessária"
        si_note = f"  A(i)={state.anchored:.0%} D(i,v)={state.dependent:.0%} — pedir 3 feitos + decisão contra pressão"

    lines.append(f"  S(i): {si_str}")
    lines.append(si_note)

    # Gap state
    gap = state.gap
    if gap.is_stasis:
        lines.append(f"  gap: ESTASE DECLARADA — desafiar g=0 (Ax4)")
        lines.append(f"  → prompt: 'alcançaste o objetivo ou é um placeholder seguro?'")
    elif gap.exists:
        lines.append(f"  gap: DETECTADO | magnitude: {gap.magnitude} | {gap.description}")
        if gap.magnitude == "high":
            lines.append(f"  → aplicar R2: decomposição em sub-vetores se necessário")
    else:
        lines.append(f"  gap: NÃO IDENTIFICADO — extrair via conversa")

    # C(q,a) state
    cqa = state.cqa
    if cqa.verified:
        sigs = ", ".join(cqa.signals_found) if cqa.signals_found else "padrão geral"
        lines.append(f"  C(q,a): VERIFICADO ✓ — ignition real | conf={cqa.confidence:.0%}")
        lines.append(f"  → sinais: {sigs}")
        lines.append(f"  → aplicar R3: surface(a_implicit)")
    elif cqa.is_escape:
        lines.append(f"  C(q,a): SUSPEITO — possível escape_dopamine (fantasia de resultado, não ação)")
        lines.append(f"  → aplicar ignition_vs_escape_gate: 'vês-te a FAZER ou a TER FEITO?'")
    elif cqa.detected:
        lines.append(f"  C(q,a): DETECTADO mas NÃO VERIFICADO — requer protocolo 3 passos")
        lines.append(f"  → nomear objeto específico → verificar S(i) → triangular histórico")
    elif cqa.implicit_knowledge:
        lines.append(f"  C(q,a): IMPLÍCITO — sabe mas não consegue articular (R3 trigger)")
        lines.append(f"  → aplicar R3 extraction: inversão, restricão, completar frase")
    else:
        lines.append(f"  C(q,a): AUSENTE — T2 ativo | usar R1+R2 (geometria pura)")
        lines.append(f"  → diagnosticar: pergunta errada | bloqueio por medo | sem dados")

    # Active theorem
    lines.append(f"  teorema: {state.active_theorem}")

    # Algorithm entry point
    if state.s_i is False:
        lines.append(f"  → ENTRAR EM: Step 1 (restauração de soberania)")
    elif state.s_i is None:
        lines.append(f"  → ENTRAR EM: Step 1 (verificação de S(i))")
    elif gap.is_stasis:
        lines.append(f"  → ENTRAR EM: Step 2 (desafio de estase)")
    elif cqa.verified:
        lines.append(f"  → ENTRAR EM: Step 3-A (extração via R3)")
    else:
        lines.append(f"  → ENTRAR EM: Step 3-B ({state.active_theorem})")

    lines.append(f"  [confiança da inferência: {state.confidence:.0%}]")

    return "\n".join(lines)


def should_activate_sias(message: str) -> bool:
    """Quick check: does this message warrant SIAS inference?

    Used by intent router to decide whether to run full inference.
    Faster than full detect_sias_signals — operates on single message.
    """
    msg_lower = message.lower()

    # Direct SIAS triggers
    direct_triggers = [
        "sias", "soberan", "sovereig", "gap", "ignition", "dopamina",
        "validação externa", "external validation",
    ]
    if any(t in msg_lower for t in direct_triggers):
        return True

    # Personal decision/direction keywords
    personal_keywords = [
        "quero", "objetivo", "meta", "decisão", "decidir",
        "bloqueado", "travado", "perdido", "próximo passo",
        "want to", "goal", "stuck", "blocked", "decision", "next step",
        "não sei se", "não sei como", "preciso de ajuda para decidir",
        "o que devo", "o que fazer", "what should i", "how do i",
        "me ajuda a", "ajuda-me a",
        "sinto que", "i feel", "animado com", "excited about",
        "longe de", "falta muito", "estou em",
    ]
    count = sum(1 for kw in personal_keywords if kw in msg_lower)
    return count >= 2
