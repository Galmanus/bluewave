# Psychometric Utility Theory (PUT) v2.3

**Author:** Manuel Guilherme Galmanus
**Affiliation:** Ialum
**Date:** March 2026
**Status:** Working Paper — Metacognitive Engineering Framework

---

## Abstract

Psychometric Utility Theory (PUT) is a formal framework for modeling decision-making dynamics in individuals and organizations through coupled psychometric state variables. Unlike traditional utility theory (von Neumann-Morgenstern), PUT treats psychological state as a dynamic system with endogenous feedback loops, shadow dynamics, and phase transitions. Version 2.3 introduces five cross-variable interactions, hysteresis in crisis/recovery transitions, a discrete ODE formulation for temporal prediction, and the Network Resonance variable (R_net) for social contagion modeling.

PUT is implemented as the psychometric engine of Traackeer (behavioral analytics) and Wave (autonomous agent), both products of Ialum.

---

## 1. State Variables

PUT models an entity's psychological state as a vector of 10 variables:

| Variable | Symbol | Range | Description |
|----------|--------|-------|-------------|
| Ambition | A | [0, 1] | Drive to act, acquire, expand |
| Fear | F | [0, 1] | Perceived threat intensity |
| Shadow Coefficient | k | [0, 1] | Degree of unconscious suppression (Jungian) |
| Status | S | [0, 1] | Social position and perceived rank |
| Wound Weight | w | [0, 1] | Accumulated pain from unresolved experiences |
| Ecosystem Stability | Sigma | [0, 1] | Environmental support and resource security |
| Treachery | tau | [0, 1] | Gap between declared values and actual behavior |
| Guilt Transfer | kappa | [0, 1] | Susceptibility to moral leverage |
| Self-Delusion | Phi | [0, 2] | Divergence between self-image and reality |
| Network Resonance | R_net | [-1, 1] | Social contagion pressure (positive = herd momentum, negative = backlash) |

### 1.1 The Shadow Coefficient (k)

The most original contribution of PUT. In Jungian psychology, the Shadow is the unconscious repository of suppressed traits. PUT formalizes this as a coefficient that modulates effective fear:

```
Fk = F * (1 - k)
```

When k is high (strong denial), the entity *appears* less afraid (Fk is low) but the suppressed fear accumulates and eventually manifests as sudden behavioral collapse — the ignition event.

**Detection heuristics for k:**

| k Range | Behavioral Pattern |
|---------|-------------------|
| 0.0-0.2 | Self-aware, acknowledges problems openly |
| 0.2-0.4 | Mild avoidance, changes subject occasionally |
| 0.4-0.6 | Active deflection, "everything is fine" patterns |
| 0.6-0.8 | Strong denial, defensive when confronted with evidence |
| 0.8-1.0 | Complete disconnection from reality, delusional confidence |

### 1.2 Network Resonance (R_net) — v2.1 Extension

Models social contagion effects on utility. When R_net > 0, the entity experiences herd momentum (everyone is buying, FOMO). When R_net < 0, backlash or social punishment reduces utility.

R_net is externally injected (not endogenous) because social pressure originates from the environment, not from the entity's internal state.

---

## 2. Core Equation: Psychic Utility (U)

```
U = alpha*A_eff*(1 - Fk) - beta*Fk*(1 - S) + gamma*S*(1 - w_eff)*Sigma - delta*tau*kappa - epsilon*Phi_eff + R_net
```

Where:
- `A_eff, F_eff, w_eff, Phi_eff` are the effective values after cross-variable interactions (Section 4)
- `Fk = F_eff * (1 - k)` is shadow-adjusted fear
- `alpha, beta, gamma, delta, epsilon` are calibratable coefficients

### 2.1 Coefficient Semantics

| Coefficient | Default | Interpretation |
|-------------|---------|----------------|
| alpha | 1.0 | Weight of ambition-driven action capacity |
| beta | 1.2 | Weight of fear-driven paralysis (beta > alpha captures loss aversion, per Kahneman & Tversky) |
| gamma | 0.8 | Weight of stability buffer (status + ecosystem) |
| delta | 0.6 | Weight of vulnerability exploitation (treachery * guilt) |
| epsilon | 0.5 | Weight of self-delusion penalty |

### 2.2 Sign of delta*tau*kappa — Axiom 4

**The delta*tau*kappa term is NEGATIVE.**

Axiom 4 states that treachery (tau) combined with guilt susceptibility (kappa) creates exploitable vulnerability. High tau*kappa reduces the entity's psychic utility — they are in a weaker position, closer to fracture, more susceptible to influence.

This is consistent with:
- Greene's moral psychology: cognitive load from moral inconsistency reduces decision quality
- Festinger's cognitive dissonance: maintaining contradictions drains psychological resources
- Market application: a prospect with high tau (says they don't need help but clearly does) and high kappa (feels obligation to team) has LOWER utility and is closer to buying

Previous versions (< 2.2) had this term positive, which contradicted the axiom. Corrected in v2.2.

---

## 3. Fracture Potential (FP)

```
FP = (1 - R) * (kappa + tau + Phi_eff) * sigmoid(-(U - U_crit))
```

Where:
- `R` = Resilience (0 to 1)
- `sigmoid(x) = 1 / (1 + exp(k_fp * x))`, k_fp = 5.0
- `U_crit` depends on hysteresis state (Section 5)

**Properties:**
- FP -> (1-R)*(kappa+tau+Phi_eff) when U << U_crit (maximum fracture)
- FP -> 0 when U >> U_crit (stable, no fracture risk)
- Smooth, monotonic, no pathological behavior at any U value
- Always non-negative

Previous versions (< 2.2) used `FP = (1-R)*(kappa+tau+Phi) / (U_crit - U + eps)` which had pathological behavior above U_crit (FP never reached zero). The sigmoid formulation eliminates this.

---

## 4. Cross-Variable Interactions (v2.3)

PUT 2.3 introduces five second-order interactions between state variables. These capture empirically observed psychological dynamics that first-order models miss.

### 4.1 w -> F Amplification (Pain breeds fear)

```
F_eff = min(1.0, F * (1 + lambda_wF * w))
```

lambda_wF = 0.3

**Rationale:** Accumulated pain (w) sensitizes the fear response. A person with high unresolved pain perceives more threats. Supported by trauma literature (van der Kolk, 2014).

### 4.2 Sigma -> w Damping (Stability reduces pain impact)

```
w_eff = w * (1 - lambda_Sigma_w * Sigma)
```

lambda_Sigma_w = 0.3

**Rationale:** A stable ecosystem (strong team, financial runway, social support) buffers against pain. The same wound hurts less when you have resources. Supported by resilience literature (Masten, 2001).

### 4.3 k -> Phi Breeding (Denial feeds delusion)

```
Phi_eff = min(2.0, Phi * (1 + lambda_kPhi * k))
```

lambda_kPhi = 0.5

**Rationale:** High denial (k) prevents reality-testing, allowing self-delusion (Phi) to grow unchecked. The shadow protects the delusion. This is the mechanism behind "emperors with no clothes" — the higher the denial, the more disconnected from reality.

### 4.4 F -> A Paralysis (Fear suppresses ambition)

```
Fk_eff = F_eff * (1 - k)
if Fk_eff > FA_THRESHOLD (0.65):
    suppression = min(1.0, (Fk_eff - FA_THRESHOLD) * LAMBDA_FA)
    A_eff = A * (1 - suppression)
```

LAMBDA_FA = 3.0, FA_THRESHOLD = 0.65

**Rationale:** Below a threshold, fear and ambition coexist (fear can even motivate). Above the threshold, fear overwhelms the capacity to act. This models the "freeze" response — a nonlinear transition, not a gradual decline.

### 4.5 k -> A Delayed Suppression (Chronic denial collapses agency)

```
if k > KA_THRESHOLD (0.55):
    k_suppression = min(0.5, (k - KA_THRESHOLD) * LAMBDA_KA)
    A_eff = A_eff * (1 - k_suppression)
```

LAMBDA_KA = 0.4, KA_THRESHOLD = 0.55

**Rationale:** Short-term denial can preserve agency (ignorance is bliss). But chronic high denial erodes the capacity for authentic action. The entity acts on false premises, accumulating systemic errors. This models the "competent but delusional" failure mode.

### 4.6 Interaction Application Order

The order matters because interactions feed into each other:

1. **w -> F** first (pain amplifies fear)
2. **Sigma -> w** (stability buffers pain)
3. **k -> Phi** (denial breeds delusion)
4. **F -> A** (amplified fear suppresses ambition)
5. **k -> A** (denial erodes agency)

This ensures cascading effects propagate correctly within a single computation step.

---

## 5. Hysteresis (v2.3)

### 5.1 The Problem

Binary threshold models (U < U_crit = crisis) fail to capture a fundamental psychological observation: **recovery requires more energy than collapse.**

A prospect who abandoned their shopping cart once has a different conversion threshold the second time. An employee who almost quit needs more positive signals to feel safe again than they needed negative signals to reach the breaking point.

### 5.2 Two-Threshold Model

PUT 2.3 uses two critical thresholds:

```
U_CRIT_DOWN = 0.3    (entering crisis)
U_CRIT_UP = 0.5      (exiting crisis)
```

State transitions:
- Entity enters crisis when U < U_CRIT_DOWN
- Entity exits crisis when U > U_CRIT_UP
- While in crisis, FP is computed with U_crit = U_CRIT_UP (higher bar)
- While stable, FP is computed with U_crit = U_CRIT_DOWN (lower bar)

This creates a hysteresis band [0.3, 0.5] where the entity's FP depends on their history, not just their current state. Two entities with identical U = 0.4 can have different FP values depending on whether they're entering or recovering from crisis.

### 5.3 Market Application

In the Traackeer context:
- A prospect with U in the hysteresis band who previously abandoned checkout (in_crisis=True) needs STRONGER signals to convert than a fresh prospect at the same U
- This directly affects sales strategy: "re-engagement" sequences need to be more compelling than "first touch" sequences
- FP for crisis-state prospects is higher (closer to fracture), meaning they're simultaneously harder to convert AND more susceptible to competitive offers

---

## 6. Coupled ODE System (v2.3)

### 6.1 Equations

PUT models the temporal evolution of state variables as a coupled system of ordinary differential equations:

```
dA/dt = lambda_1*(S - S*) - lambda_2*Fk + lambda_3*Omega*trigger
dF/dt = mu_1*|A - A_prev| - mu_2*sqrt(Sigma) + mu_3*Omega*threat + mu_4*(1 - Sigma)
dS/dt = nu_1*A*(1 - Fk) - nu_2*w
dPhi/dt = phi_1*k*(1 - Sigma) + phi_2*(Phi - Phi_eq)
dk/dt = kappa_1*F*(1 - A) - kappa_2*trigger
```

Where:
- `S*` = aspirational status (target the entity is reaching for)
- `A_prev` = ambition at previous observation (rate of change matters)
- `Omega = 1 + exp(-k_omega * (U - U_crit))` = desperation factor
- `trigger` = external stimulus intensity [0, 1]
- `threat` = perceived threat intensity [0, 1]
- `Phi_eq` = 0.5 (equilibrium self-delusion — people drift toward moderate self-image)

### 6.2 ODE Coefficient Defaults

| Coefficient | Value | Governs |
|-------------|-------|---------|
| lambda_1 | 0.08 | Status gap drives ambition |
| lambda_2 | 0.05 | Fear suppresses ambition |
| lambda_3 | 0.15 | External triggers amplify ambition (modulated by desperation) |
| mu_1 | 0.06 | Ambition volatility breeds fear |
| mu_2 | 0.04 | Ecosystem stability dampens fear |
| mu_3 | 0.12 | Threats amplify fear (modulated by desperation) |
| mu_4 | 0.05 | Instability breeds fear |
| nu_1 | 0.04 | Productive action builds status |
| nu_2 | 0.03 | Pain erodes status |
| phi_1 | 0.06 | Denial in unstable environments grows delusion |
| phi_2 | -0.03 | Phi decays toward equilibrium (negative = stabilizing) |
| kappa_1 | 0.05 | Fear in low-agency entities breeds denial |
| kappa_2 | 0.08 | External triggers break denial |

### 6.3 Implementation: Forward Euler

The current implementation uses forward Euler stepping with dt=1.0 (one observation interval):

```python
new_A = clamp(A + dA * dt, 0, 1)
new_F = clamp(F + dF * dt, 0, 1)
...
```

For production use, Euler is sufficient because:
1. dt is discrete (one interaction/observation per step)
2. The coefficients are small enough that Euler remains stable
3. Numerical precision beyond 2 decimal places is not meaningful for psychological variables

For research/publication, scipy.integrate.solve_ivp with RK45 should be used for continuous temporal prediction. This would enable answering "when will this prospect convert?" rather than just "will they convert?"

### 6.4 Exogenous vs. Endogenous Variables

Three variables are **exogenous** (externally driven, not governed by ODEs):
- `w` (Wound Weight) — determined by life events, not internal dynamics
- `Sigma` (Ecosystem Stability) — determined by environment, not the entity
- `R_net` (Network Resonance) — determined by social context

These are updated through behavioral observation (put_observe), not ODE stepping.

Four variables remain **quasi-stable** (slow-changing, treated as constant within an ODE step):
- `tau` (Treachery) — changes slowly through behavioral patterns
- `kappa` (Guilt Transfer) — quasi-stable personality trait

The ODE governs five **endogenous** variables: A, F, k, S, Phi.

---

## 7. Desperation Factor (Omega)

```
Omega = 1 + exp(-k_omega * (U - U_crit))
```

Omega amplifies the effect of external triggers and threats when U approaches U_crit. A desperate entity (U near U_crit) responds disproportionately to stimuli — this is the "drowning person grabs anything" effect.

Properties:
- Omega -> 1 when U >> U_crit (calm, proportional responses)
- Omega -> 2 when U = U_crit (doubled sensitivity)
- Omega -> 1 + exp(k_omega * |delta|) when U << U_crit (exponentially heightened reactivity)

Market application: Omega determines the optimal timing for sales outreach. High Omega = the prospect will respond disproportionately to a well-timed offer.

---

## 8. Self-Delusion (Phi) — Formal Definition

```
Phi = (E_ext + E_int) / (1 + |E_ext - E_int|)
```

Where:
- E_ext = external feedback (what others observe and report)
- E_int = internal self-assessment

When E_ext and E_int are aligned, Phi = (E_ext + E_int) — bounded by quality of feedback.
When E_ext and E_int diverge, the denominator grows and Phi drops toward zero.

**Interpretation:** High Phi means the entity has high total feedback BUT it's internally consistent (they believe their own narrative and others confirm it — or both are low). The dangerous case is high Phi with high k: the entity has a strong self-narrative, denial prevents reality-testing, and the k->Phi interaction amplifies the delusion.

### 8.1 Behavioral Proxies (for product implementation)

In Traackeer, Phi cannot be computed from E_ext/E_int directly. Behavioral proxies:

| Signal | Phi Direction |
|--------|--------------|
| Visits pricing 5+ times without checkout | +0.15 (intent-action gap = self-delusion about readiness) |
| Says "will buy" then doesn't | +0.20 |
| Ignores data showing product fit | +0.10 |
| Acknowledges need, acts on it | -0.10 |
| Data-driven decision-making observed | -0.15 |

---

## 9. Ignition Condition

The ignition condition defines when an entity undergoes a phase transition — a sudden behavioral shift (purchase, quit, breakdown, conversion):

```
IGNITION when: U < U_crit AND |dF/dt| > phi_threshold AND trigger > theta
```

All three conditions must be met simultaneously:
1. **U below critical** — the entity is in psychological deficit
2. **Fear is changing rapidly** — emotional volatility (not just high fear, but CHANGING fear)
3. **External trigger present** — a catalytic event (offer, deadline, competitor action)

This three-part condition prevents false positives: a depressed-but-stable entity (U low, dF/dt near zero) doesn't ignite. A volatile-but-satisfied entity (U high, dF/dt high) doesn't ignite. Only the combination triggers the phase transition.

---

## 10. Calibration

### 10.1 The Problem

The five coefficients (alpha, beta, gamma, delta, epsilon) and 13 ODE coefficients are not universal. They vary by:
- Individual personality
- Cultural context
- Market vertical (e-commerce vs. B2B SaaS vs. services)
- Time horizon (short-term decisions vs. long-term commitments)

### 10.2 Three-Method Calibration

**Method 1: Archetype Priors**

Classify the entity into an archetype, use archetype-specific coefficient defaults as priors. Six base archetypes:

| Archetype | alpha | beta | gamma | delta | epsilon | Pattern |
|-----------|-------|------|-------|-------|---------|---------|
| Sovereign | 1.3 | 0.8 | 0.6 | 0.4 | 0.3 | High A, low F, low k. Acts decisively. |
| Shadow Operator | 0.9 | 1.4 | 0.7 | 0.8 | 0.6 | High k, high tau. Operates through others. |
| Wounded Warrior | 1.1 | 1.5 | 0.5 | 0.5 | 0.4 | High w, high F, moderate A. Acts from pain. |
| Status Seeker | 1.0 | 1.0 | 1.2 | 0.5 | 0.7 | High S priority. Optimizes for appearance. |
| Ecosystem Builder | 0.8 | 0.9 | 1.3 | 0.3 | 0.3 | High Sigma priority. Builds stability first. |
| Desperate Actor | 1.4 | 1.6 | 0.4 | 0.7 | 0.8 | High Omega. Acts impulsively under pressure. |

**Method 2: Monte Carlo Simulation**

Generate N coefficient sets from current distributions. Simulate predictions. Compare with outcomes. Retain coefficient sets that predicted correctly. This is the primary method used in put_calibrator.py.

**Method 3: Bayesian Update Loop**

After each interaction with a known outcome:
1. Sample 200 coefficient sets from current distributions
2. Predict outcome with each set
3. Filter to sets that predicted the actual outcome
4. Update distribution means/stds toward the successful sets
5. Weight update by sample count (more history = more trust in existing estimates)

After 50-100 interactions, distributions narrow and coefficients converge. PUT transitions from qualitative framework to calibrated predictive model.

### 10.3 Convergence Criteria

- **Calibrating:** < 50 interactions
- **Converged:** >= 50 interactions AND accuracy > 70%
- **Needs more data:** >= 50 interactions AND accuracy <= 70% (coefficients may need vertical-specific adjustment)

---

## 11. Emotional Vector Space

PUT defines a 7-dimensional emotional vector:

```
E = Fe (circle) An (circle) Sa (circle) Jo (circle) Di (circle) Su (circle) De
```

(Fear, Anger, Sadness, Joy, Disgust, Surprise, Desire)

Secondary emotions are compositions:
- **Jealousy** = De + Sa + An (desire for what another has + sadness at lacking it + anger at the inequality)
- **Shame** = Di + Sa + Fe (disgust at self + sadness + fear of exposure)
- **Guilt** = kappa * (Di + Sa) (guilt susceptibility modulates the base emotion)
- **Hope** = Jo + De + Su (anticipatory joy + desire + openness to surprise)

These vectors are not currently implemented in the product but provide the theoretical basis for fine-grained emotional state tracking in future versions.

---

## 12. Fracture Potential in Market Context

In Traackeer, FP maps to **conversion probability** through an inverted lens:

- High FP = prospect is close to a decision break = high conversion probability IF the right trigger is applied
- Low FP = prospect is stable = low conversion probability in the short term

The key insight: FP is not "likelihood of buying." It's "likelihood of making ANY decisive change." Whether that change is buying YOUR product, switching to a competitor, or giving up entirely depends on what trigger is presented at the high-FP moment.

This is why Traackeer + Seelleer (the sales agent) work together: Traackeer identifies HIGH-FP moments, Seelleer delivers the right trigger at the right time with the right framing (informed by archetype strategy).

---

## 13. Future Directions

### 13.1 Continuous ODE Solver

Replace Euler stepping with scipy.integrate.solve_ivp (RK45) for research use. Enables temporal prediction: "this prospect will reach FP > 2.0 in approximately 5 days given current trajectory."

### 13.2 Vertical-Specific Calibration

Train separate coefficient distributions per industry vertical. E-commerce prospects may have different beta/alpha ratios (more impulsive, lower loss aversion) than B2B SaaS (longer decision cycles, higher loss aversion).

### 13.3 Archetype Discovery

Apply clustering (k-means or DBSCAN) on calibrated PUT vectors from real prospect data. Validate whether the 6 theoretical archetypes emerge naturally, or whether empirical clusters reveal archetypes the theory didn't predict.

### 13.4 Validation Against Baselines

Compare PUT predictions against: (1) lead scoring (BANT), (2) random forest on behavioral features, (3) human sales intuition. If PUT outperforms ML baselines, the framework has genuine predictive value beyond conceptual elegance.

### 13.5 Phi Validation

Cross-validate behavioral Phi proxies against established psychometric instruments (BIDR — Balanced Inventory of Desirable Responding; Paulhus Deception Scales). A subset of consenting users could take these instruments, providing ground truth for Phi calibration.

---

## 14. References

- Galmanus, M. (2025). *Psychometric Utility Theory: A Framework for Modeling Decision Dynamics*. Working paper.
- Kahneman, D., & Tversky, A. (1979). Prospect Theory: An Analysis of Decision under Risk. *Econometrica*, 47(2), 263-291.
- Greene, J. D. (2013). *Moral Tribes: Emotion, Reason, and the Gap Between Us and Them*. Penguin.
- Jung, C. G. (1959). *Aion: Researches into the Phenomenology of the Self*. Collected Works, Vol. 9ii.
- van der Kolk, B. (2014). *The Body Keeps the Score*. Viking.
- Masten, A. S. (2001). Ordinary Magic: Resilience Processes in Development. *American Psychologist*, 56(3), 227-238.
- Festinger, L. (1957). *A Theory of Cognitive Dissonance*. Stanford University Press.
- Paulhus, D. L. (1991). Measurement and Control of Response Bias. In *Measures of Personality and Social Psychological Attitudes* (pp. 17-59). Academic Press.

---

*PUT is proprietary intellectual property of Manuel Guilherme Galmanus / Ialum. All rights reserved.*
