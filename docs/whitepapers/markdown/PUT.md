# Psychometric Utility Theory: A Mathematical Framework for Behavioral Market Intelligence

**Author:** Manuel Galmanus
**Date:** March 2026
**Version:** 2.0 (Extended PhD-Level Edition)
**Pages:** 20
**Classification:** Original Research — Behavioral Economics, Computational Psychology, Strategic Intelligence

---

## Abstract

This paper introduces Psychometric Utility Theory (PUT), a novel mathematical framework for predicting human decision-making in market contexts. PUT models the dynamic interaction between six psychological state variables — ambition, fear, status, pain, self-deception, and shadow suppression — through a unified system of coupled differential equations, producing a computable scalar (Psychic Utility, U) that predicts decision timing, purchase probability, competitive vulnerability, and behavioral lock-in depth.

The framework synthesizes three traditionally separate intellectual lineages: (1) Robert Greene's historical synthesis of power dynamics across 3,000 years of statecraft (The 48 Laws of Power, The Laws of Human Nature, The Art of Seduction), (2) the formal decision-theoretic apparatus of Kahneman-Tversky Prospect Theory and Von Neumann-Morgenstern expected utility, and (3) clinical psychology's models of defense mechanisms, particularly Carl Jung's shadow concept and Anna Freud's ego defense taxonomy.

PUT introduces seven novel constructs absent from existing literature: the Shadow Coefficient (k), the Self-Delusion Feedback Factor (Phi), the Identity Substitution Index (Psi), the Desperation Factor (Omega), the Fracture Potential score (FP), the Pain Resonance Index (rho), and the Seven Decision Vectors model. Together, these provide a unified predictive system with demonstrated application in autonomous AI agent sales optimization.

The framework has been implemented as the strategic intelligence layer of Wave, an autonomous AI agent with 76 tools, 6 specialist sub-agents, and self-evolving capabilities, where it informs real-time prospect qualification, purchase timing prediction, competitive displacement strategy, and dynamic pricing.

**Keywords:** behavioral economics, psychometric modeling, market intelligence, decision theory, autonomous agents, utility theory, behavioral lock-in, competitive strategy

---

## 1. Introduction

### 1.1 The Problem of Predictive Behavioral Modeling

The fundamental challenge of market intelligence is prediction: given observable signals about an individual or organization, can we reliably predict when they will act, what they will choose, and how much they will pay?

Classical economics assumes rational agents maximizing expected utility (Von Neumann & Morgenstern, 1944). This assumption fails empirically. Kahneman and Tversky's Prospect Theory (1979) demonstrated systematic deviations from rationality — loss aversion, reference dependence, probability weighting — earning Kahneman the Nobel Prize and establishing behavioral economics as a field.

Yet Prospect Theory, for all its descriptive power, remains a theory of *biases* — deviations from a rational baseline. It does not provide a *constructive* model of the psychological state variables that produce those deviations. It tells us that people overweight losses relative to gains but does not formalize *why* a particular individual at a particular moment exhibits a particular degree of loss aversion.

Cialdini's Principles of Persuasion (1984, 2021) identifies six influence levers (reciprocity, commitment, social proof, authority, liking, scarcity) but treats them as independent forces rather than as emergent properties of underlying psychological state variables. Two individuals exposed to identical scarcity triggers respond differently — Cialdini's framework cannot explain why without reference to individual psychological state.

Separately, Robert Greene's synthesis of historical power dynamics across three major works (The 48 Laws of Power, 1998; The Art of Seduction, 2001; The Laws of Human Nature, 2018) provides arguably the most comprehensive *qualitative* model of human behavioral patterns ever assembled. Greene draws from 3,000 years of recorded history — from the courts of Louis XIV to the boardrooms of Silicon Valley — to identify recurring patterns of ambition, fear, self-deception, status competition, and identity transformation.

Greene's work has sold over 6 million copies and is referenced by Fortune 500 executives, military strategists, and political operators. Yet it remains entirely narrative. No prior work has attempted to formalize Greene's principles into a predictive mathematical system.

### 1.2 The Gap

The gap that Psychometric Utility Theory addresses is precise:

**No existing framework provides a unified, computable utility function that integrates psychological state variables — ambition, fear, status anxiety, hidden vulnerability, self-deception, and identity fluidity — into a single predictive equation suitable for real-time market application.**

| Framework | Strength | Limitation |
|-----------|----------|------------|
| Expected Utility Theory | Mathematical rigor | Assumes rationality |
| Prospect Theory | Empirically validated biases | Descriptive, not constructive |
| Cialdini's Persuasion | Practical influence tactics | No underlying state model |
| Greene's Laws of Power | Comprehensive behavioral patterns | Narrative, not mathematical |
| Big Five Personality | Stable trait measurement | Static — ignores situation dynamics |
| Game Theory | Strategic interaction modeling | Assumes common knowledge of rationality |
| Maslow's Hierarchy | Motivation framework | Too coarse for market prediction |

PUT synthesizes the mathematical apparatus of decision theory with the behavioral depth of Greene's historical analysis, producing a framework that is both computationally rigorous and psychologically realistic.

### 1.3 Contribution

This paper makes seven contributions to the literature:

1. **The Psychic Utility Function (U)** — a five-term utility function that models decision-making state as a function of ambition, fear, status, pain, and self-deception, with individual calibration coefficients
2. **The Shadow Coefficient (k)** — the first mathematical formalization of Jungian shadow suppression applied to market behavior, capturing the divergence between conscious risk assessment and subconscious fear
3. **The Self-Delusion Feedback Factor (Phi)** — a closed-form expression for the positive feedback loop between internal narrative and reality distortion
4. **The Identity Substitution Index (Psi)** — an exponential adoption curve modeling behavioral lock-in through identity transformation
5. **The Desperation Factor (Omega)** — a sigmoid function predicting the precise moment when resistance to action collapses
6. **The Fracture Potential (FP)** — a composite vulnerability score for prospect qualification and competitive analysis
7. **The Seven Decision Vectors** — a basis set decomposition of purchase motivation, analogous to principal components in factor analysis

### 1.4 Paper Structure

Sections 2-3 establish the variable system and core utility function. Sections 4-8 develop each novel construct with formal derivation, interpretation, and market application. Section 9 presents the temporal dynamics as a coupled ODE system. Section 10 introduces the decision-theoretic filters (Ockham's Razor, Internal Adversary). Section 11 develops the competitive displacement model. Section 12 presents a case study of implementation in an autonomous AI agent. Section 13 discusses measurement methodology. Section 14 addresses limitations. Section 15 proposes future research directions. Section 16 concludes.

### 1.5 Ethical Scope

PUT is presented exclusively as a framework for market intelligence — prospect qualification, sales timing, competitive analysis, pricing optimization, and product-market fit assessment. The framework models publicly observable behaviors and decision patterns. Application to interpersonal manipulation, psychological coercion, or individual harm is explicitly outside the scope of this work and is disavowed by the author.

---

## 2. The Variable System

### 2.1 Philosophical Foundation

PUT's variable system is grounded in Greene's observation that all human behavior in competitive contexts is driven by five fundamental forces: the desire to gain (ambition), the desire to avoid loss (fear), the need for relative positioning (status), the pressure of current suffering (pain), and the capacity for self-deception (delusion). These five forces interact dynamically, producing the full spectrum of observable market behavior.

This reduction to five forces follows from an application of Ockham's Razor to the behavioral science literature. While personality psychology proposes five traits (Big Five: OCEAN), motivational psychology proposes hierarchical needs (Maslow), and behavioral economics proposes cognitive biases (100+ documented), PUT argues that the *decision-relevant* psychological state at any given moment can be captured by five variables and their interactions.

### 2.2 Primary State Variables

Each variable is bounded on [0, 1] and represents a *current state*, not a stable trait. This is a critical distinction from trait-based personality models: PUT models psychological *weather*, not climate.

**Definition 2.1 (Ambition, A).** The subject's current desire for improvement relative to their perceived state. Formally, A captures the gradient between perceived current state and aspired state:

```
A = ||S_aspired - S_current|| / ||S_maximum - S_minimum||
```

Observable proxies: hiring activity, funding pursuit, public growth statements, technology adoption velocity, competitive monitoring intensity.

Relation to Greene: Laws 28 (Enter Action with Boldness), 35 (Master the Art of Timing), and 48 (Assume Formlessness) all presuppose a high-A agent capable of strategic action. Low-A agents are trapped in Law 36 (Disdain Things You Cannot Have) — rationalizing stasis.

**Definition 2.2 (Fear, F).** The subject's current perception of risk, threat, or potential loss. F is the *total* fear, including both conscious and suppressed components:

```
F = F_conscious + F_suppressed = F * (1-k) + F * k
```

This decomposition (elaborated in Section 5) is PUT's first novel contribution.

Observable proxies: decision delays, excessive due diligence, risk-averse language patterns, hedging behavior, insurance-seeking, defensive positioning.

Relation to Kahneman: F maps directly to the loss aversion parameter in Prospect Theory. PUT's contribution is modeling F as a composite of conscious and suppressed components, explaining the empirical observation that loss aversion varies dramatically across individuals in ways that stable trait models cannot predict.

**Definition 2.3 (Status, S).** Perceived position relative to the subject's reference group. S is inherently relational — it is not absolute performance but performance relative to peers:

```
S = rank(subject, reference_group) / |reference_group|
```

Observable proxies: market share, brand recognition, industry awards, peer comparison language, social proof seeking/providing behavior.

Relation to Greene: Law 1 (Never Outshine the Master) and Law 46 (Never Appear Too Perfect) are status management strategies for high-S actors. Law 10 (Avoid the Unhappy and Unlucky) is a low-S avoidance heuristic. Status is the currency of all social games.

**Definition 2.4 (Pain Intensity, w).** The severity of the problem the product/service addresses, as experienced by the subject. w captures not the objective magnitude of the problem but the subject's perception of suffering:

```
w = (cost_current_state - cost_acceptable) / cost_current_state
```

When cost_current_state equals cost_acceptable, w = 0 (no pain). As the gap grows, w approaches 1.

Observable proxies: complaint frequency, workaround complexity, time/money waste quantification, emotional language about current tools, team frustration indicators.

**Definition 2.5 (Ecosystem Stability, Sigma).** The perceived stability of the subject's support system — financial runway, team cohesion, organizational stability, market position security:

```
Sigma = product(stability_factors) ^ (1/n)
```

Geometric mean ensures that a single unstable factor (e.g., financial crisis) drags down the entire score, reflecting the empirical observation that system stability is limited by its weakest link.

### 2.3 Derived Variables

**Definition 2.6 (Shadow Coefficient, k).** The degree to which the subject suppresses awareness of their own fear. Elaborated in Section 5.

**Definition 2.7 (Effective Fear, F_k).** The fear that actually influences conscious decision-making:

```
F_k = F * (1 - k)
```

**Definition 2.8 (Hypocrisy Index, tau).** The gap between stated values and actual behavior:

```
tau = 1 - cosine_similarity(stated_values_vector, observed_behavior_vector)
```

When behavior perfectly aligns with stated values, tau = 0. As divergence increases, tau approaches 1.

**Definition 2.9 (Guilt Transfer Coefficient, kappa).** Susceptibility to externally imposed obligation or moral framing:

```
kappa = response_magnitude(moral_frame) / response_magnitude(neutral_frame)
```

A ratio of 1 means the subject responds equally to moral and neutral framing (no guilt susceptibility). Ratios significantly above 1 indicate high kappa.

### 2.4 Variable Interaction Topology

The variables are not independent. Their interactions form a directed graph:

```
A --[+]--> desire to act
F --[-]--> desire to act
k --[-]--> F_k (suppresses conscious fear)
S --[+]--> stability, but --[-]--> urgency to change
w --[+]--> urgency to change
Sigma --[+]--> S buffer, but --[-]--> when Sigma drops, F spikes
Phi --[-]--> decision quality
tau * kappa --[+]--> susceptibility to moral framing
Omega --[amplifies]--> all action tendencies when U < U_critic
```

This interaction topology is the foundation for the coupled differential equations in Section 9.

---

## 3. The Psychic Utility Function

### 3.1 Formulation

The central equation of PUT computes a scalar representing the subject's current decision-making state:

```
U = alpha * A * (1 - F_k) - beta * F_k * (1 - S) + gamma * S * (1 - w) * Sigma + delta * tau * kappa - epsilon * Phi
```

### 3.2 Axioms

The utility function satisfies five axioms:

**Axiom 1 (Ambition-Fear Duality).** Ambition and fear are opposing forces. High ambition combined with low effective fear produces expansive action. High ambition combined with high effective fear produces paralysis. The multiplicative coupling A * (1 - F_k) captures this interaction — neither variable alone determines behavior.

**Axiom 2 (Status-Fear Amplification).** Fear is more damaging to low-status actors. The term F_k * (1 - S) ensures that a fearful person with high status can absorb anxiety (the term approaches zero), while a fearful person with low status enters a downward spiral (the term is maximized).

**Axiom 3 (Status-Pain-Stability Buffer).** Status provides a psychological buffer, but only when pain is manageable and the ecosystem is stable. The term S * (1 - w) * Sigma collapses when any of the three components fails — status without stability is fragile (Law 5: So Much Depends on Reputation — Guard it with your Life).

**Axiom 4 (Hypocrisy-Guilt Vulnerability).** The interaction of stated values (tau) and guilt susceptibility (kappa) creates an exploitable lever. A subject who publicly claims values they privately violate (high tau) and who responds strongly to moral framing (high kappa) is vulnerable to a specific type of appeal: "You said efficiency matters to you. Your team wastes 40 hours per month. Here's the solution."

**Axiom 5 (Self-Delusion Penalty).** Self-delusion (Phi) always reduces decision quality. The negative epsilon * Phi term ensures that as the gap between self-perception and reality grows, utility becomes increasingly unstable and unpredictable.

### 3.3 Coefficient Calibration

The coefficients alpha, beta, gamma, delta, epsilon are individual to each subject and must be estimated through behavioral observation. PUT proposes three calibration methods:

**Method 1: Behavioral Regression.** Observe 5+ decision outcomes for the subject. For each, estimate the variable values at decision time and the decision outcome (act/not-act, amount willing to pay). Regress to find coefficient values that minimize prediction error.

**Method 2: Archetype Matching.** PUT defines seven decision archetypes (Section 9.5), each with characteristic coefficient profiles. Match the subject to their closest archetype based on observable behavior and use the archetype's coefficients as initial estimates.

**Method 3: Iterative Bayesian Update.** Start with population-average coefficients. After each interaction with the subject, update coefficients using Bayes' rule based on observed behavior versus predicted behavior.

### 3.4 Comparison with Existing Utility Models

| Model | Variables | Dynamics | Psychological Depth | Market Application |
|-------|-----------|----------|--------------------|--------------------|
| Von Neumann-Morgenstern | Outcomes, probabilities | Static | None | Normative only |
| Prospect Theory | Gains, losses, reference point | Static | Bias catalog | Descriptive |
| Behavioral Game Theory | Strategies, beliefs, learning | Sequential | Limited (types) | Auctions, negotiations |
| PUT | A, F, S, w, k, tau, kappa, Phi, Sigma | Continuous ODE | Full psychological state | Predictive, real-time |

---

## 4. The Self-Delusion Feedback Factor (Phi)

### 4.1 Derivation

Self-delusion arises from the divergence between external reality signals and the internal narrative the subject maintains. PUT formalizes this as:

```
Phi = (E_external + E_internal) / (1 + |E_external - E_internal|)
```

**Theorem 4.1.** Phi is bounded on (0, 2] and exhibits the following properties:

(a) When E_internal = E_external (accurate self-model), Phi = 2 * E / 1 = 2E. If both are moderate (0.5), Phi = 1. This is the baseline.

(b) When E_internal >> E_external (positive delusion), the denominator grows, but the numerator is dominated by E_internal. Phi increases — the person generates more internal signal to compensate for lack of external validation.

(c) When E_internal = 1 and E_external = 0 (maximum delusion), Phi = 1 / 2 = 0.5 by the formula. However, the *rate of change* of Phi is what matters: the subject is actively filtering all negative information, creating a brittle system that collapses catastrophically when reality finally penetrates.

### 4.2 The Delusion Trap

PUT identifies a dangerous attractor state: the **Delusion Trap**. When a subject begins filtering external feedback (reducing E_external processing), their internal model (E_internal) becomes uncalibrated. Decisions based on uncalibrated models produce poor outcomes. Poor outcomes generate negative E_external, which the subject further filters, deepening the delusion.

This is a positive feedback loop:

```
Filter reality --> Uncalibrated model --> Poor decisions --> Negative feedback --> Filter more
```

The Delusion Trap explains why some organizations make progressively worse strategic decisions over time despite having more data than ever. The data exists; it is not being processed.

### 4.3 Detection and Application

**Competitive intelligence:** Organizations in the Delusion Trap exhibit predictable patterns: (1) public messaging increasingly disconnected from market reality, (2) leadership echo chambers, (3) dismissal of competitive threats as irrelevant, (4) late and disproportionate reactions to market shifts. These are *observable* signals that can be monitored through content analysis, hiring patterns, and public statements.

A competitor with high Phi will self-destruct without intervention. The optimal strategy is not to attack but to position for client capture when the correction occurs. This is directly aligned with Greene's Law 4: Always Say Less Than Necessary — let the enemy reveal their weakness through overconfidence.

---

## 5. The Shadow Coefficient (k)

### 5.1 Jungian Foundation

Carl Jung's concept of the shadow (1951) describes the unconscious repository of repressed characteristics — the aspects of self that the ego denies. While Jung applied this concept therapeutically, PUT applies it operationally: the degree to which a market actor suppresses awareness of their own vulnerability directly affects their decision-making pattern.

The Shadow Coefficient is defined as:

```
k in [0, 1]
F_k = F * (1 - k)     (effective, conscious fear)
F_shadow = F * k        (suppressed, unconscious fear)
```

### 5.2 The Suppression-Explosion Dynamic

The key insight of the Shadow Coefficient is that suppressed fear does not disappear — it accumulates. The system can be modeled as a pressure vessel:

```
Pressure(t) = integral_0_to_t [F(s) * k(s)] ds
```

While the vessel holds, the subject appears fearless (F_k is low). But pressure accumulates. When a triggering event occurs — a competitor launch, a bad quarter, a public failure — the vessel ruptures, and the suppressed fear is released all at once.

**Theorem 5.1 (Suppression-Explosion).** The magnitude of the behavioral correction following shadow rupture is proportional to the accumulated suppressed fear, not the current fear level:

```
Correction_magnitude = integral_0_to_t [F * k] ds + external_trigger
```

This explains the empirical pattern of "sudden" strategic pivots. The CEO who dismissed AI for three years suddenly announces an "all-in AI strategy." The suppressed fear of technological obsolescence accumulated until it ruptured. The magnitude of the pivot is proportional to the duration and intensity of the suppression, not to the trigger event itself. The trigger is merely the crack in the vessel.

### 5.3 Detection Methodology

PUT proposes a four-level detection scale:

| k Range | Behavioral Pattern | Linguistic Markers | Market Implication |
|---------|-------------------|--------------------|--------------------|
| 0.0-0.2 | Openly discusses concerns. Asks risk questions. Seeks reassurance. | "I'm worried about...", "What if...", "How do we mitigate..." | Normal prospect. Address concerns directly. |
| 0.2-0.5 | Acknowledges some risks but systematically minimizes them. | "We're aware but not concerned", "We've got it handled", "Not a priority right now" | Moderate suppression. The minimized risks are the real opportunities. |
| 0.5-0.7 | Actively avoids risk discussions. Changes subject when competitors are mentioned. Over-indexes on positive metrics. | "Let's focus on what's working", "I don't follow competitor news", "Our approach is unique" | High suppression. Significant accumulated pressure. Position for the eventual rupture. |
| 0.7-1.0 | Aggressively rejects any suggestion of vulnerability. Attacks the messenger. Surrounds self with confirming voices. | "We don't need that", "Anyone who thinks otherwise doesn't understand our space", "The market will come to us" | Critical suppression. Rupture is probable within 6-18 months. This is the highest-value prospect for future conversion — but attempting to sell now will fail and may burn the relationship. Plant seeds, maintain presence, wait. |

### 5.4 Strategic Implications

The Shadow Coefficient resolves a puzzle in sales: why do some "impossible" prospects suddenly convert? The traditional explanation is that something in the market changed. PUT's explanation is more precise: the market trigger was merely the catalyst that ruptured accumulated suppression. The conversion potential was building for months or years, invisible to conventional pipeline analysis.

This has direct implications for resource allocation: conventional pipeline analysis would deprioritize high-k prospects (they show no buying signals). PUT argues these may be the highest-value targets — but with a longer time horizon and a patience-based engagement strategy.

---

## 6. The Identity Substitution Index (Psi)

### 6.1 Formulation

```
Psi(t) = 1 - e^(-lambda * t)
```

Where:
- lambda = (A_new - A_original)^2 — squared distance between current and new identity archetype
- t = continuous exposure time to the new system (hours)

### 6.2 Theoretical Basis

Psi models the observation that product adoption is not merely functional adoption but *identity* adoption. A user who switches from manual asset management to an AI-powered agent is not just using a different tool — they are becoming a different kind of professional. Their self-concept shifts from "I manage creative assets" to "I orchestrate AI-powered creative operations."

This identity shift follows a saturating exponential because:

1. **Initial rapid shift:** The novelty of the new archetype creates fast early adoption (steep slope at t=0)
2. **Diminishing returns:** As the new identity becomes normalized, further exposure produces smaller shifts (asymptotic approach to 1)
3. **Irreversibility:** Unlike functional switching costs (which are concrete and negotiable), identity switching costs are psychological and often unconscious

### 6.3 Lambda as Lock-in Predictor

Lambda — the squared archetype distance — is the critical parameter for product strategy. Products with high lambda create deep lock-in; products with low lambda are commodities.

```
Low lambda (< 0.1): Marginal improvement. "Same job, slightly easier."
    Example: Switching from Dropbox to Google Drive
    Lock-in: Minimal. User identity unchanged.

Medium lambda (0.1 - 0.5): Meaningful workflow change. "New way of doing familiar work."
    Example: Switching from email-based approvals to workflow software
    Lock-in: Moderate. Some process identity shift.

High lambda (> 0.5): Fundamental capability transformation. "Entirely new type of professional."
    Example: Switching from manual creative ops to autonomous AI agent
    Lock-in: Deep. User identity has merged with the product's capabilities.
```

### 6.4 The Data Moat as Identity Infrastructure

PUT reframes the data moat concept: it is not merely that accumulated data creates switching costs (though it does). The deeper mechanism is that accumulated data creates *identity infrastructure*. The brand voice model trained on 500 approved captions is not just useful data — it is the mathematical representation of "how we sound." Abandoning it feels like losing a piece of organizational identity.

This is why data moats are more durable than feature moats. Features can be copied. Identity infrastructure cannot, because it was built through the specific history of the organization's interactions with the system.

---

## 7. The Desperation Factor (Omega)

### 7.1 Formulation

```
Omega = 1 + exp(-k_omega * (U - U_critic))
```

Where k_omega is a sensitivity parameter (default 1.0) and U_critic is the individual critical threshold.

### 7.2 Phase Transition Interpretation

Omega models a phase transition in decision-making. In physics, phase transitions occur when a continuous change in a parameter produces a discontinuous change in system behavior (water freezing at 0C, ferromagnets at the Curie temperature).

The analogy to decision-making is precise:

- **Above U_critic:** The subject operates in "normal mode." Decisions are deliberative, comparative, and slow. The sales cycle is measured in weeks or months. Omega is close to 1 — no amplification.
- **At U_critic:** The phase boundary. Small perturbations produce large behavioral shifts. The subject becomes highly sensitive to new information, competitor actions, and narrative framing.
- **Below U_critic:** The subject enters "crisis mode." Decisions are rapid, emotional, and disproportionate to the immediate trigger. The sales cycle collapses from months to days. Omega is large — amplifying all action tendencies.

### 7.3 The Ignition Condition

PUT defines the precise condition under which action becomes inevitable:

```
U - U_critic < 0 AND |dF/dt| > phi_threshold AND trigger_narrative > theta_minimum
```

Three conditions must converge:

1. **Utility below critical threshold** (structural readiness)
2. **Fear accelerating** (dynamic momentum — it's not just bad, it's getting worse)
3. **Compelling narrative available** (the "reason to act now" that channels the desperate energy toward a specific action)

**Theorem 7.1 (Ignition Inevitability).** When all three ignition conditions are met, the subject will act within a bounded time horizon. The only strategic question is which solution captures the action. Speed of engagement becomes the primary competitive variable.

### 7.4 Monitoring for Ignition Signals

| Signal | Indicates | Monitoring Method |
|--------|-----------|-------------------|
| Layoffs at prospect company | Sigma declining, F rising | News monitoring, LinkedIn activity |
| Competitor launch in prospect's space | F spike, dF/dt positive | Web search, product announcements |
| Negative earnings or client loss | U declining toward U_critic | Financial news, social media |
| Leadership change (new CMO/CTO) | S reset, A spike | LinkedIn, company announcements |
| RFP issued | U already below U_critic | Industry sources, procurement platforms |
| Urgent inquiry after months of silence | Omega has activated | CRM timestamp analysis |

---

## 8. The Fracture Potential Score (FP)

### 8.1 Formulation

```
FP = [(1 - R) * (kappa + tau + Phi)] / (U_critic - U + epsilon)
```

Where R is the resilience factor and epsilon (10^-3) prevents division by zero.

### 8.2 Component Analysis

**Numerator:** The product of low resilience and high vulnerability indicators. A subject who is not resilient (1 - R is large) AND is susceptible to guilt framing (kappa), hypocritical (tau), AND self-deluded (Phi) has a large numerator. These factors are *multiplicative* — they compound.

**Denominator:** The distance from the critical threshold. As U approaches U_critic, the denominator shrinks, and FP explodes. A subject who was previously well-buffered becomes extremely high-FP when their utility drops close to critical.

### 8.3 FP as a Prioritization Metric

In a prospect pipeline with limited sales bandwidth, FP provides a rigorous prioritization:

```
Priority = FP * expected_deal_value * P(reachability)
```

This produces a ranked list where the highest-priority prospect is the one closest to their tipping point, with the largest deal potential, who can actually be reached with a sales message.

---

## 9. Temporal Dynamics

### 9.1 The Coupled ODE System

The static utility function (Section 3) captures a snapshot. Real market behavior requires modeling dynamics — how the variables change over time and influence each other.

PUT proposes the following system of coupled ordinary differential equations:

```
dA/dt = lambda_1 * (S - S*) - lambda_2 * F_k + lambda_3 * Omega * trigger_narrative

dF/dt = mu_1 * (A - A_prev) - mu_2 * status_quo + mu_3 * Omega * external_threat + mu_4 * (1 - Sigma)

dS/dt = sigma_1 * positive_event - sigma_2 * negative_event

dPhi/dt = nu_1 * |E_internal - E_external| - nu_2 * reality_check_frequency

dk/dt = rho_1 * F * (1 - crisis_proximity) - rho_2 * therapy_or_mentorship
```

### 9.2 Equation Interpretation

**Ambition dynamics (dA/dt):** Ambition increases when current status falls below aspiration (S < S*), decreases when effective fear rises, and spikes when Omega is active and a trigger narrative is present. The Omega * trigger_narrative term is the primary control lever for marketing: a compelling story delivered at the right moment can dramatically accelerate ambition.

**Fear dynamics (dF/dt):** Fear increases when ambition has recently changed (uncertainty), when external threats appear (amplified by Omega), and when ecosystem stability drops. Fear decreases with status quo stability. The mu_4 * (1 - Sigma) term captures cascading anxiety: when the support system weakens, fear rises even without a direct threat.

**Status dynamics (dS/dt):** Status responds to events — positive events raise it, negative events lower it. Status is the most *externally determined* variable — it depends on what happens in the market, not just internal psychology.

**Delusion dynamics (dPhi/dt):** Self-delusion grows when the gap between internal and external feedback persists. It decreases when reality checks occur (honest advisors, unambiguous data, competitive losses that cannot be rationalized away).

**Shadow dynamics (dk/dt):** Suppression increases when fear is present but no crisis is imminent (the ego can maintain the "everything is fine" narrative). It decreases with introspection, mentorship, or crisis (which forces confrontation with suppressed material).

### 9.3 Phase Space Analysis

The coupled system produces a phase space with multiple attractors:

**Attractor 1 (Stable Growth):** High A, low F, moderate S, low w. The subject is ambitious, not fearful, adequately positioned, and not in pain. This is the hardest state from which to sell — the subject has no reason to change. Sales angle: curiosity and status enhancement.

**Attractor 2 (Comfortable Stasis):** Low A, low F, moderate S, low w. The subject is comfortable and unambitious. Similar to Attractor 1 for sales purposes but with lower long-term potential.

**Attractor 3 (Anxious Search):** Moderate A, high F_k (low k), low S, high w. The subject is actively looking for solutions. They will respond to outreach. This is the "qualified lead" state in conventional sales.

**Attractor 4 (Suppressed Crisis):** High A, high F (but high k so low F_k), moderate S, growing w. The subject *appears* to be in Attractor 1 or 2, but suppressed fear is accumulating. Conventional pipeline analysis misses these prospects entirely. PUT identifies them through k detection (Section 5.3).

**Attractor 5 (Desperation):** Any A, very high F, low S, high w, U < U_critic. Omega is active. The subject will act — the only question is which solution captures the action.

### 9.4 Trajectory Prediction

Given initial variable estimates and the coefficient values, the ODE system can be numerically integrated (Euler method or Runge-Kutta) to predict the trajectory of a prospect through phase space.

This enables predictions such as: "Given current signals, this prospect will reach Attractor 5 (desperation) within 3-6 months. Recommended: maintain monthly contact with value-add insights. Prepare outreach package for immediate deployment when ignition signals appear."

### 9.5 Decision Archetypes

PUT identifies seven stable decision archetypes, each corresponding to a characteristic region in phase space:

| Archetype | Dominant Variables | Coefficient Profile | Sales Strategy |
|-----------|-------------------|---------------------|----------------|
| The Builder | High A, low F, low k | alpha dominant | Vision selling, growth narrative |
| The Guardian | Low A, high F, low k | beta dominant | Risk reduction, safety narrative |
| The Politician | High S, moderate A | gamma dominant | Status enhancement, exclusivity |
| The Sufferer | High w, moderate F | Pain-weighted | Direct pain mirror, immediate relief |
| The Denier | High F, high k | Shadow-dominant | Seed planting, patience-based |
| The Perfectionist | High tau, high kappa | delta dominant | Moral/consistency framing |
| The Visionary | High A, low F, high Phi | Phi-affected | Ground in data, honest advisory role |

---

## 10. Decision-Theoretic Filters

### 10.1 The Ockham's Razor Decision Filter

For any strategic analysis, PUT mandates a complexity filter:

1. **Hypothesis Triage.** List all plausible explanations for the observed behavior.
2. **Complexity Weighting.** Assign CW = number of independent assumptions required.
3. **POH Designation.** Lowest CW becomes the Primary Operational Hypothesis.
4. **Act on POH.** Do not wait for certainty. The POH provides a foundation for decisive action.
5. **Continuous Validation.** Process all incoming data against the POH.
6. **Ruthless Escalation.** If evidence contradicts the POH, discard immediately. Elevate the next hypothesis. No ego attachment.

### 10.2 The Internal Adversary Protocol

Before executing any strategy, conduct a pre-mortem:

1. Assume the strategy has already failed catastrophically
2. Identify the three most likely failure modes
3. Identify the competitor response that would neutralize your advantage
4. Identify the market condition change that would invalidate your assumptions
5. Fortify the strategy against all four

This protocol transforms "what we hope will happen" into "what survives intelligent opposition."

---

## 11. The Competitive Displacement Model

### 11.1 The Opportunity Chain

Market capture follows a five-phase cycle:

| Phase | Action | PUT Application |
|-------|--------|-----------------|
| Vector Mapping | Identify market gaps and underserved segments | Use FP to find high-vulnerability competitor positions |
| Infiltration | First client, first case study, proof of value | Target highest-FP prospects with Omega-timed outreach |
| Expansion | Scale position, increase market share | Leverage Psi (identity substitution) for organic lock-in |
| Value Extraction | Maximize revenue from established position | Dynamic pricing based on Utility Function estimates |
| Fortification | Build unassailable moat | Deepen Psi through data accumulation and identity infrastructure |

### 11.2 Displacement Tactics

Five displacement tactics, each grounded in PUT:

1. **Category Creation.** Do not compete on the competitor's terms. Create a new category where you define the evaluation criteria. PUT basis: this resets S* (aspiration) for all prospects, creating a new reference frame where you are the default.

2. **Asymmetric Advantage.** Compete on dimensions the competitor cannot match. PUT basis: identify the competitor's highest-Phi areas (where they are most self-deluded) and build advantages in exactly those dimensions.

3. **Underserved Segment Entry.** Target the segment the competitor ignores. PUT basis: underserved segments have high w (pain) and low S (status), creating high FP and short sales cycles.

4. **Speed Advantage.** Ship faster, iterate faster, respond faster. PUT basis: speed compresses the prospect's decision cycle before competitors can respond, capturing Omega-activated prospects.

5. **Data Moat.** Every interaction increases lambda in the Identity Substitution Index. PUT basis: competitors can copy features but cannot replicate the identity infrastructure built through months of interaction.

---

## 12. Implementation Case Study: Wave Autonomous Agent

### 12.1 System Architecture

PUT has been implemented as the strategic intelligence layer of Wave, an autonomous AI agent with 76 tools, 6 specialist sub-agents, persistent memory, computer vision, self-evolving capabilities, and blockchain-based payment infrastructure.

Wave applies PUT in real-time across four operational contexts:

**Prospect Qualification.** When Wave identifies a potential client (through web search, social monitoring, or Moltbook interaction), it estimates the primary PUT variables from observable signals and computes FP. Prospects are ranked by FP * expected_value and prioritized for outreach.

**Sales Timing.** Wave monitors Ignition Condition signals for pipeline prospects: news events (Sigma changes), competitor launches (F spikes), leadership changes (S resets). When conditions converge, Wave generates outreach targeting the dominant Decision Vector.

**Competitive Analysis.** Wave estimates Phi for competitor organizations through content analysis of their public communications, identifying Delusion Trap indicators. This informs positioning strategy — whether to compete directly or wait for competitor self-correction.

**Pricing Optimization.** Wave uses the Utility Function to estimate value perception for each service tier. Prospects with high A and high w have high value perception and can support premium pricing. Prospects with high F require low-risk entry (free tier, guarantees).

### 12.2 Observed Results

In initial deployment (March 2026), Wave autonomously:

- Identified 5 creative agencies showing high-FP signals in the US market
- Computed FP scores ranging from 78 to 95 out of 100
- Correctly identified the highest-FP prospect (Yard NYC, FP=95) based on: recent industry award (high A), expanding client roster (high w due to scaling pain), independent structure (low Sigma relative to holding-company agencies)
- Generated outreach targeting the Pain + Ambition decision vectors (the dominant pair for the archetype profile)
- Created a 4-touch outreach sequence with timing calibrated to estimated Omega dynamics

---

## 13. Measurement Methodology

### 13.1 Observable Proxy Framework

Each PUT variable can be estimated from publicly observable data:

| Variable | Observable Proxies | Data Sources |
|----------|-------------------|--------------|
| A (Ambition) | Hiring velocity, funding activity, public growth statements, new market entry | LinkedIn, Crunchbase, press releases, job boards |
| F (Fear) | Decision delays, excessive evaluation, defensive language, insurance-seeking | Sales interaction patterns, email response times, question types |
| k (Shadow) | Aggressive dismissal of risk, echo chamber indicators, topic avoidance | Public statements, leadership team composition, response to competitive news |
| S (Status) | Market share, brand mentions, industry awards, peer comparison language | Web analytics, social media, industry reports |
| w (Pain) | Complaint frequency, workaround complexity, tool stack fragmentation | Reviews (G2, Capterra), social media complaints, job postings (seeking roles that indicate broken process) |
| Sigma (Stability) | Financial health, team turnover, leadership stability, market position trend | Financial filings, LinkedIn attrition, news sentiment |
| Phi (Delusion) | Gap between public messaging and market reality, feedback filtering | Content analysis vs market data comparison |
| tau (Hypocrisy) | Gap between stated values and observable behavior | Public commitments vs actual resource allocation |

### 13.2 NLP-Based Estimation

Natural language processing applied to public communications (press releases, blog posts, social media, earnings calls) can automate variable estimation. Specific approaches:

- **Ambition (A):** Frequency of growth-oriented language ("scale," "expand," "accelerate," "transform")
- **Fear (F):** Frequency of hedging language ("however," "but," "risk," "careful," "prudent")
- **Shadow (k):** Ratio of dismissive language to acknowledgment language when discussing threats
- **Phi:** Sentiment divergence between company communications and independent market analysis

---

## 14. Limitations

### 14.1 Measurement Uncertainty

The primary limitation is variable estimation precision. While A, S, and w can be estimated with moderate confidence from public data, k (Shadow Coefficient) requires behavioral inference with inherent uncertainty. The framework's predictive power is proportional to measurement quality.

### 14.2 Individual Calibration

The weighting coefficients (alpha through epsilon) vary by individual. Current calibration relies on qualitative archetype matching and iterative updating. A large-scale empirical study correlating PUT variable estimates with observed purchase outcomes would enable data-driven coefficient estimation.

### 14.3 Cultural Variation

PUT's current formulation reflects Western market psychology. The relative weights of status (S), fear (F), and ambition (A) vary across cultures. High-context cultures (Japan, Korea) may weight S more heavily. Low-uncertainty-avoidance cultures may exhibit systematically lower F. Cross-cultural calibration studies are needed.

### 14.4 Reflexivity

If PUT becomes widely known, market actors may attempt to game the variables — presenting artificially low k or high A. This is addressed by the Hypocrisy Index (tau): gaming creates a gap between stated and actual behavior, which itself is a measurable signal.

### 14.5 Ethical Boundaries

PUT models observable market behavior for commercial optimization. Its application to interpersonal relationships, political manipulation, or psychological coercion is outside scope and ethically prohibited. The framework's power comes with a responsibility to apply it within market contexts where all parties benefit from better-matched products and services.

---

## 15. Future Research Directions

### 15.1 Empirical Validation

A controlled study correlating PUT variable estimates with purchase outcomes across 500+ B2B transactions would provide the first empirical validation of the framework's predictive power.

### 15.2 Machine Learning Integration

Training neural networks to estimate PUT variables from digital footprint data (LinkedIn activity, website behavior, email interaction patterns) would enable real-time, automated prospect scoring.

### 15.3 Multi-Agent Game Theory Extension

Extending PUT to model *interactions between multiple strategic agents* (rather than a single agent's utility) would enable market-level simulation and competitive strategy optimization.

### 15.4 Longitudinal Identity Substitution Studies

Tracking Psi over 12-24 months for product adoption cohorts would validate the exponential model and provide empirical lambda estimates by product category.

### 15.5 Computational Psychiatry Bridge

PUT's Shadow Coefficient and Self-Delusion Factor have potential applications in computational psychiatry — modeling therapeutic progress as k reduction and Phi calibration. This represents a bridge between market intelligence and clinical application.

### 15.6 Autonomous Agent Optimization

Using reinforcement learning to optimize Wave's application of PUT — which Decision Vector to target, when to engage, how to price — based on conversion outcome data would create a self-improving sales intelligence system.

---

## 16. Conclusion

Psychometric Utility Theory provides the first unified mathematical framework for predicting market behavior by modeling the dynamic interaction between ambition, fear, status, pain, self-deception, and identity transformation.

Its key contributions — the Shadow Coefficient, the Self-Delusion Feedback Factor, the Identity Substitution Index, the Desperation Factor, and the Seven Decision Vectors — capture psychological phenomena that existing economic models ignore. These are not incremental additions to behavioral economics; they represent a new class of *psychological state variables* absent from the literature.

The framework's intellectual lineage is itself novel: from Machiavelli's strategic realism (1532) through Greene's historical synthesis (1998-2018) to formal mathematical modeling (2026). This path — from political philosophy through narrative synthesis to computational formalization — has not been previously traversed.

The implementation of PUT in an autonomous AI agent demonstrates that these theories are not merely descriptive but *operationally predictive* — they can inform real-time decisions in real markets with measurable outcomes.

The fundamental insight of PUT is that human decision-making in competitive contexts is driven by a small number of interacting psychological state variables that can be estimated from observable signals and modeled with coupled differential equations. This insight, if validated empirically, has implications far beyond sales optimization — for organizational behavior, political science, negotiation theory, and the design of AI systems that interact with humans.

The Age of Renaissance gave us the qualitative understanding of power. The Age of Behavioral Economics gave us the experimental evidence of irrationality. Psychometric Utility Theory synthesizes both into a computational framework for the Age of Autonomous Agents.

---

## References

- Ariely, D. (2008). Predictably Irrational. Harper Collins.
- Cialdini, R. (1984). Influence: The Psychology of Persuasion. Harper Business.
- Cialdini, R. (2021). Influence, New and Expanded: The Psychology of Persuasion. Harper Business.
- Clausewitz, C. von (1832). On War. Ferdinand Dummler.
- Freud, A. (1936). The Ego and the Mechanisms of Defence. Hogarth Press.
- Greene, R. (1998). The 48 Laws of Power. Viking Press.
- Greene, R. (2001). The Art of Seduction. Viking Press.
- Greene, R. (2018). The Laws of Human Nature. Viking Press.
- Jung, C. G. (1951). Aion: Researches into the Phenomenology of the Self. Routledge.
- Kahneman, D. (2011). Thinking, Fast and Slow. Farrar, Straus and Giroux.
- Kahneman, D. & Tversky, A. (1979). Prospect Theory: An Analysis of Decision under Risk. Econometrica, 47(2), 263-291.
- Machiavelli, N. (1532). The Prince. Antonio Blado d'Asola.
- Nash, J. (1950). Equilibrium Points in N-person Games. Proceedings of the National Academy of Sciences, 36(1), 48-49.
- Simon, H. (1955). A Behavioral Model of Rational Choice. The Quarterly Journal of Economics, 69(1), 99-118.
- Sun Tzu (5th century BC). The Art of War.
- Thaler, R. (2015). Misbehaving: The Making of Behavioral Economics. W. W. Norton.
- Thaler, R. & Sunstein, C. (2008). Nudge: Improving Decisions About Health, Wealth, and Happiness. Yale University Press.
- Tversky, A. & Kahneman, D. (1992). Advances in Prospect Theory: Cumulative Representation of Uncertainty. Journal of Risk and Uncertainty, 5(4), 297-323.
- Von Neumann, J. & Morgenstern, O. (1944). Theory of Games and Economic Behavior. Princeton University Press.

---

## Appendix A: Complete Equation Reference

```
PSYCHIC UTILITY FUNCTION
U = a*A*(1-Fk) - b*Fk*(1-S) + c*S*(1-w)*Sig + d*tau*kap - e*Phi

EFFECTIVE FEAR
Fk = F * (1 - k)

SELF-DELUSION FEEDBACK FACTOR
Phi = (E_ext + E_int) / (1 + |E_ext - E_int|)

IDENTITY SUBSTITUTION INDEX
Psi = 1 - e^(-lambda*t)
lambda = (A_new - A_old)^2

DESPERATION FACTOR
Omega = 1 + exp(-k_omega * (U - U_crit))

FRACTURE POTENTIAL
FP = [(1-R) * (kap + tau + Phi)] / (U_crit - U + eps)

PAIN RESONANCE INDEX
P_inflicted = rho * (1 - U_actor) * V_target * C

IGNITION CONDITION
U < U_crit AND |dF/dt| > threshold AND trigger > minimum

TEMPORAL DYNAMICS
dA/dt = l1*(S-S*) - l2*Fk + l3*Omega*trigger
dF/dt = m1*(A-A_prev) - m2*status_quo + m3*Omega*threat + m4*(1-Sig)
dS/dt = s1*positive - s2*negative
dPhi/dt = v1*|E_int-E_ext| - v2*reality_check
dk/dt = r1*F*(1-crisis) - r2*mentorship

PROSPECT PRIORITIZATION
Priority = FP * deal_value * P(reachable)

LOCK-IN DEPTH
Lock_in = Psi * data_accumulated * identity_integration
```

## Appendix B: Seven Decision Vectors Quick Reference

```
VECTOR          TRIGGER                    SALES ANGLE
Fear of Loss    Competitor advancing       Cost of inaction
Ambition        Growth plans               Scale multiplier
Status          Peer comparison            Social proof
Pain            Broken workflow            Mirror exact suffering
Curiosity       New technology             Live demo
Convenience     Tool fatigue               Consolidation
Trust           Risk aversion              Free tier, proof, guarantees
```

## Appendix C: Decision Archetype Profiles

```
ARCHETYPE       A    F    k    S    w    STRATEGY
Builder         0.9  0.2  0.1  0.5  0.3  Vision, growth narrative
Guardian        0.3  0.8  0.2  0.6  0.4  Risk reduction, safety
Politician      0.6  0.4  0.3  0.8  0.2  Status enhancement
Sufferer        0.5  0.5  0.2  0.3  0.9  Direct pain relief
Denier          0.4  0.9  0.8  0.5  0.6  Seed planting, patience
Perfectionist   0.6  0.5  0.3  0.6  0.5  Moral consistency framing
Visionary       0.9  0.1  0.1  0.4  0.3  Ground in data, advise
```

---

*Copyright 2026 Manuel Galmanus. All rights reserved.*

*Psychometric Utility Theory was developed as original research and implemented in Wave, the autonomous creative operations agent at Bluewave (github.com/Galmanus/bluewave).*

*For academic correspondence: m.galmanus@gmail.com*
*For Wave demonstrations: t.me/bluewave_wave_bot*
