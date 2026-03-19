# Psychometric Utility Theory: A Mathematical Framework for Behavioral Market Intelligence

**Author:** Manuel Galmanus
**Date:** March 2026
**Version:** 1.0

---

## Abstract

This paper introduces Psychometric Utility Theory (PUT), a mathematical framework for predicting human decision-making in market contexts by modeling the interaction between ambition, fear, status, psychological vulnerability, and self-deception. Drawing from Robert Greene's synthesis of historical power dynamics (The 48 Laws of Power, The Laws of Human Nature, The Art of Seduction), behavioral economics (Kahneman & Tversky), and classical game theory, PUT formalizes qualitative principles of influence into a system of computable equations with measurable variables.

The framework introduces seven novel constructs: the Psychic Utility Function (U), the Shadow Coefficient (k), the Self-Delusion Feedback Factor (Phi), the Identity Substitution Index (Psi), the Desperation Factor (Omega), the Fracture Potential score (FP), and the Seven Decision Vectors model. Together, these provide a unified predictive system for prospect qualification, purchase timing, competitive displacement, pricing optimization, and behavioral lock-in analysis.

PUT has been implemented as the strategic intelligence layer of Wave, an autonomous AI agent operating in the creative operations market, where it informs real-time sales decisions, prospect scoring, and competitive strategy.

---

## 1. Introduction

### 1.1 The Gap

Behavioral economics has produced powerful descriptive models of human decision-making. Kahneman and Tversky's Prospect Theory (1979) demonstrated that humans evaluate losses and gains asymmetrically. Cialdini's Principles of Persuasion (1984) identified six levers of influence. Game theory provides equilibrium models for strategic interaction.

However, none of these frameworks offers a **unified, computable utility function** that integrates psychological state variables — ambition, fear, status anxiety, hidden vulnerability, self-deception — into a single predictive equation suitable for real-time market application.

Separately, Robert Greene's body of work (The 48 Laws of Power, 1998; The Art of Seduction, 2001; The Laws of Human Nature, 2018) provides arguably the most comprehensive qualitative synthesis of human behavioral patterns across 3,000 years of recorded history. Yet Greene's work remains narrative, not mathematical. No prior work has attempted to formalize Greene's principles into a predictive mathematical system.

### 1.2 Contribution

Psychometric Utility Theory bridges this gap by:

1. Defining a **Psychic Utility Function (U)** that models an individual's decision-making state as a computable scalar
2. Introducing the **Shadow Coefficient (k)** — the degree to which an individual suppresses awareness of their own fear, creating a divergence between stated and actual decision drivers
3. Formalizing **Self-Delusion (Phi)** as a feedback loop between internal narrative and external reality
4. Modeling **Identity Substitution (Psi)** as an exponential adoption curve for behavioral lock-in
5. Defining the **Desperation Factor (Omega)** as a sigmoid function predicting the exact moment when resistance to action collapses
6. Introducing the **Fracture Potential (FP)** score for prospect qualification and competitive vulnerability analysis
7. Proposing the **Seven Decision Vectors** as the fundamental basis set for all purchase decisions

### 1.3 Scope and Ethics

This paper presents PUT exclusively as a framework for **market intelligence** — prospect qualification, sales timing, competitive analysis, pricing optimization, and product-market fit assessment. The framework models publicly observable market behaviors and decision patterns. It is not intended for, and the author explicitly disavows, application to interpersonal manipulation, psychological harm, or coercive influence.

---

## 2. Fundamental Variables

PUT operates on a set of measurable variables, each bounded between 0 and 1 unless otherwise specified.

### 2.1 Primary Variables

| Variable | Name | Range | Description |
|----------|------|-------|-------------|
| A | Ambition | 0-1 | Desire for improvement relative to current state. Measured through hiring signals, funding activity, public growth statements, technology adoption patterns. |
| F | Fear | 0-1 | Perception of risk or potential loss. Measured through risk-averse language, decision delays, excessive due diligence requests, competitor monitoring behavior. |
| S | Status | 0-1 | Perceived position relative to reference group. Measured through market share, brand recognition, industry awards, peer comparison behavior. |
| w | Pain Intensity | 0-1 | Severity of the current problem the product solves. Measured through complaint frequency, workaround complexity, time/money wasted on current solution. |

### 2.2 Derived Variables

| Variable | Name | Range | Description |
|----------|------|-------|-------------|
| k | Shadow Coefficient | 0-1 | Degree to which the subject denies their own fear. Higher k means lower conscious F but higher subterranean F. The gap between what they say and what drives them. |
| F_k | Effective Fear | 0-1 | F * (1 - k). The fear that actually influences conscious decision-making. When k is high, F_k is low — the person appears fearless but is actually the most vulnerable to fear-based triggers. |
| tau | Hypocrisy Index | 0-1 | Gap between stated values and actual behavior. Measured through inconsistency between public statements and observable actions. |
| kappa | Guilt Transfer Coefficient | 0-1 | Susceptibility to externally imposed guilt or obligation. Measured through response to social proof, authority, and reciprocity triggers. |

### 2.3 Environmental Variables

| Variable | Name | Range | Description |
|----------|------|-------|-------------|
| Sigma | Ecosystem Stability | 0-1 | Perceived stability of the subject's support system — financial, organizational, relational. Low Sigma amplifies all other vulnerabilities. |
| U_critic | Critical Utility Threshold | varies | The point below which the subject's utility function triggers desperate action. Individual to each subject. |
| trigger_narrative | Narrative Impulse | 0-1 | External story or framing that shifts perception. The primary control lever in marketing and sales. |

---

## 3. The Psychic Utility Function

### 3.1 Formulation

The core of PUT is the Psychic Utility Function, which computes a scalar value representing an individual's current decision-making state:

```
U = alpha * A * (1 - F_k) - beta * F_k * (1 - S) + gamma * S * (1 - w) * Sigma + delta * tau * kappa - epsilon * Phi
```

Where:
- **alpha, beta, gamma, delta, epsilon** are individual weighting coefficients determined through behavioral observation
- **F_k = F * (1 - k)** is the effective fear
- **Phi** is the Self-Delusion Feedback Factor (Section 4)

### 3.2 Interpretation

**High U (approaching 1):** The subject is in a state of confident stability. They are ambitious but not desperate, have adequate status, and low pain. In market terms: they are unlikely to change vendors, adopt new solutions, or take risks. Sales efforts should focus on curiosity and status enhancement.

**Moderate U (0.3-0.7):** The subject is in a dynamic state. Some combination of pain, fear, and ambition is creating tension. This is the optimal zone for engagement — the subject is open to change but not yet desperate. Sales efforts should amplify pain awareness and present clear value.

**Low U (approaching 0):** The subject is approaching their critical threshold. Pain is high, status is threatened, fear is mounting. They are actively seeking solutions. This is the conversion window.

**U below U_critic:** Desperation threshold crossed. The Desperation Factor (Omega) activates. The subject will act — the question is whether they act toward your solution or a competitor's. Speed of engagement becomes the decisive factor.

### 3.3 Component Analysis

**Term 1: alpha * A * (1 - F_k)** — Ambition modulated by effective fear. High ambition with low fear produces expansive, risk-taking behavior. High ambition with high fear produces analysis paralysis.

**Term 2: -beta * F_k * (1 - S)** — Fear penalty, amplified by low status. A fearful person with high status can absorb anxiety. A fearful person with low status spirals. This term is always negative, dragging U down.

**Term 3: gamma * S * (1 - w) * Sigma** — Status benefit, reduced by pain and ecosystem instability. High status provides psychological buffer, but only if the current problem isn't too severe and the support system is intact.

**Term 4: delta * tau * kappa** — The hypocrisy-guilt interaction. Subjects with high tau (gap between stated values and behavior) and high kappa (susceptibility to guilt) are vulnerable to moral framing: "You say you value efficiency, but your team wastes 8 hours per week searching for files."

**Term 5: -epsilon * Phi** — Self-delusion penalty. The more detached from reality, the more unpredictable and fragile the decision-making process.

---

## 4. The Self-Delusion Feedback Factor (Phi)

### 4.1 Formulation

```
Phi = (E_external + E_internal) / (1 + |E_external - E_internal|)
```

Where:
- **E_external** = actual feedback received from the environment (0-1)
- **E_internal** = feedback the individual chooses to internalize (0-1)

### 4.2 Interpretation

When E_internal closely matches E_external, Phi remains stable — the person has an accurate self-model. When E_internal diverges from E_external (the person filters reality to maintain a preferred self-image), Phi increases rapidly.

**Critical case: E_internal = 1, E_external = 0.** The subject believes they are performing excellently while receiving no positive external signal. Phi approaches maximum. This is the narcissistic founder, the CMO who only reads positive metrics, the competitor who ignores market shifts.

### 4.3 Market Application

**Competitive analysis:** Estimate Phi for competing companies' leadership. High Phi organizations make predictably poor strategic decisions because their internal model diverges from market reality. They will underestimate threats and overestimate their position. Position to capture their clients when the inevitable correction occurs.

**Client qualification:** Prospects with moderate Phi (some self-awareness gaps) respond well to data-driven reality checks: "Your approval cycle takes 4.2 days. Industry average is 6 hours." The data punctures the self-delusion and creates urgency.

**Product design:** Build systems that provide honest, continuous E_external feedback. Dashboards that show real performance against benchmarks. This creates healthy Phi and increases platform trust.

---

## 5. The Shadow Coefficient (k)

### 5.1 Concept

The Shadow Coefficient is perhaps the most original contribution of PUT. It captures a phenomenon well-documented in clinical psychology but never mathematically formalized for market application: **the degree to which a person suppresses awareness of their own fear.**

The effective fear that influences conscious decisions is:

```
F_k = F * (1 - k)
```

A person with F = 0.9 (high fear) and k = 0.8 (heavy suppression) has F_k = 0.18 — they appear almost fearless. But the suppressed fear (F * k = 0.72) doesn't disappear. It manifests as:

- Overconfidence followed by sudden paralysis
- Aggressive dismissal of risk data
- Impulsive decisions when the suppression breaks
- Disproportionate reaction to minor threats (the suppressed fear finally finds an outlet)

### 5.2 Identification Signals

| k Level | Observable Behavior |
|---------|-------------------|
| k < 0.2 | Open about concerns. Asks questions. Seeks reassurance. |
| k = 0.3-0.5 | Acknowledges some risks but minimizes them. "We're fine for now." |
| k = 0.5-0.7 | Actively avoids risk discussions. Changes subject. Over-indexes on positive data. |
| k > 0.7 | Aggressive rejection of any suggestion of vulnerability. "We don't need that." |

### 5.3 Market Application

**The high-k prospect is the most valuable target.** They appear as a hard sell (dismissive, "not interested"), but their suppressed fear creates enormous potential energy. When a triggering event occurs (competitor launch, client loss, board pressure), the suppression breaks catastrophically. The prospect who said "we don't need that" last month sends an urgent inquiry today.

**Strategy:** With high-k prospects, do not push. Plant seeds. Send one valuable insight per month. When the break happens, you are already positioned as the trusted source. The key is to be present when suppression collapses, not to force the collapse.

---

## 6. The Identity Substitution Index (Psi)

### 6.1 Formulation

```
Psi = 1 - e^(-lambda * t)
```

Where:
- **lambda = (A_new - A_original)^2** — the squared distance between the current identity and the new archetype
- **t** = continuous exposure time to the new system/product (in hours)

### 6.2 Interpretation

Psi models how quickly a user's professional identity merges with a product. It follows a saturating exponential — rapid initial adoption that gradually plateaus.

- **Psi approaching 0:** The user sees the product as a tool. They could switch tomorrow. No lock-in.
- **Psi approaching 0.5:** The user has started incorporating the product into their workflow identity. "I use Bluewave for my assets." Switching is inconvenient.
- **Psi approaching 1:** The product IS part of how they define their professional capability. "I run creative operations on Bluewave." Switching feels like losing a skill. Maximum lock-in.

### 6.3 Lambda as Lock-in Predictor

Lambda (the squared distance between old and new archetype) determines the SPEED of identity substitution, not just the direction. A product that is marginally better than the current workflow has low lambda — slow adoption, easy switching. A product that fundamentally changes HOW someone works has high lambda — rapid adoption, painful switching.

**This is why Bluewave's autonomous agent architecture creates stronger lock-in than a traditional DAM tool.** A DAM tool is a marginal improvement (lambda is low). An AI agent that manages your entire creative operation is a fundamental identity shift (lambda is high). The user goes from "I manage assets" to "Wave manages assets for me." The archetype distance is large, so Psi grows fast, and the lock-in deepens quickly.

### 6.4 The Data Moat Interpretation

Psi explains why the data moat works. As Psi increases, the accumulated brand intelligence (learned tone, caption style, compliance rules) becomes PART of the user's identity. It's not just data they would lose — it's capability. The switching cost isn't measured in dollars; it's measured in Psi regression. Going back to Psi = 0 (starting over) is psychologically painful in proportion to how high Psi has climbed.

---

## 7. The Desperation Factor (Omega)

### 7.1 Formulation

```
Omega = 1 + exp(-k_omega * (U - U_critic))
```

Where:
- **k_omega** = sensitivity parameter (0.1-5.0, default 1.0)
- **U** = current Psychic Utility
- **U_critic** = individual critical threshold

### 7.2 The Sigmoid of Action

Omega is a sigmoid function centered on U_critic. When U is comfortably above U_critic, Omega approaches 1 (no desperation effect). As U drops toward U_critic, Omega begins to rise. When U crosses below U_critic, Omega explodes upward.

This models the empirical observation that human decision-making is not linearly proportional to discomfort. People tolerate increasing pain without acting — until a threshold is crossed, at which point they act suddenly and disproportionately. The "sudden decision" to switch vendors, fire an agency, or adopt a new platform is rarely sudden. It is Omega crossing its inflection point.

### 7.3 Temporal Dynamics

The full dynamic system:

```
dA/dt = lambda_1 * (S - S*) - lambda_2 * F_k + lambda_3 * Omega * trigger_narrative
dF/dt = mu_1 * (A - A_prev) - mu_2 * status_quo + mu_3 * Omega * external_threat + mu_4 * (1 - Sigma)
dS/dt = sigma_1 * positive_event - sigma_2 * negative_event
```

Where S* is the desired status (aspiration level) and trigger_narrative is the external narrative impulse — the primary control lever in marketing.

**The Ignition Condition** (the moment action becomes inevitable):

```
U - U_critic < 0 AND |dF/dt| > threshold AND trigger_narrative > minimum
```

When utility drops below critical AND fear is accelerating AND a compelling narrative is present, the subject WILL act. The only question is which solution captures the action.

### 7.4 Application: Sales Timing

Monitor these signals for prospects:
- **U declining:** Company losing market share, negative press, client churn
- **F accelerating (dF/dt high):** Competitor just launched, board meeting approaching, budget review
- **trigger_narrative available:** You have a case study, demo, or data point that frames the urgency

When all three converge, that is the exact moment to reach out. Not before (waste of effort, prospect is above U_critic), not after (competitor may capture the desperate action first).

---

## 8. The Fracture Potential Score (FP)

### 8.1 Formulation

```
FP = [(1 - R) * (kappa + tau + Phi)] / (U_critic - U + epsilon)
```

Where:
- **R** = Resilience factor (0-1)
- **kappa** = guilt transfer coefficient
- **tau** = hypocrisy index
- **Phi** = self-delusion factor
- **U_critic - U** = distance from critical threshold
- **epsilon** = small constant (10^-3) to prevent division by zero

### 8.2 Interpretation

FP quantifies how close a subject (prospect or competitor) is to their tipping point. Higher FP means:
- Low resilience (R close to 0)
- High vulnerability to guilt and moral framing (kappa, tau)
- High self-delusion (Phi)
- Close to or below critical utility threshold (small denominator)

### 8.3 Market Application

**Prospect prioritization:** Rank prospects by FP. Highest FP prospects are closest to their buying tipping point. Focus outreach resources on them.

**Competitive vulnerability:** Calculate FP for competing companies' market position. A competitor with high FP is about to make a strategic error, lose clients, or undergo internal disruption. Position to capture the fallout.

**Resource allocation:** Limited sales bandwidth should target highest-FP prospects first. This maximizes conversion per effort unit.

---

## 9. The Seven Decision Vectors

### 9.1 Theory

Every purchase decision is a vector sum of seven fundamental motivational forces. Understanding which vectors dominate for a given prospect determines the optimal sales angle.

### 9.2 The Vectors

| Vector | Symbol | Trigger Condition | Optimal Sales Angle |
|--------|--------|-------------------|-------------------|
| Fear of Loss | Fe | Competitor advancing, market shifting | Demonstrate cost of inaction. "Every week without automation, you fall further behind." |
| Ambition | Am | Growth plans, expansion, new markets | Show scale multiplier. "Same team, 10x output." |
| Status | St | Peer comparison, industry recognition | Social proof from similar companies. "Leading agencies use this." |
| Pain | Pa | Broken workflow, wasted time/money | Mirror exact pain. "8 hours/week searching for files? That ends today." |
| Curiosity | Cu | New technology, innovation appetite | Lead with demo. Let them experience the capability. |
| Convenience | Co | Tool fatigue, complexity overload | Consolidation story. "One platform replaces five tools." |
| Trust | Tr | Risk aversion, need for validation | Free tier, live demo, on-chain audit trail, case studies. Zero-risk entry. |

### 9.3 Vector Composition

No decision is driven by a single vector. Purchase decisions are vector sums:

- **Urgency buy:** Fe + Pa dominant. High fear of loss combined with acute pain. Respond with speed and clear ROI.
- **Strategic buy:** Am + St dominant. Ambition for growth combined with status aspiration. Respond with vision and social proof.
- **Cautious buy:** Tr + Co dominant. Trust-seeking combined with desire for simplicity. Respond with free trial and migration support.
- **Impulse buy:** Cu + Pa dominant. Curiosity about new technology combined with pain. Respond with interactive demo.

### 9.4 Detection Methods

| Vector | Observable Signals |
|--------|-------------------|
| Fe | Asking about competitor features. Monitoring competitor social. Urgency in inquiry. |
| Am | Discussing growth targets. Recently hired. Expanding to new markets. |
| St | Referencing what "other companies" do. Award-seeking behavior. |
| Pa | Describing current workflow frustrations. Quantifying time wasted. |
| Cu | Asking "how does it work" before "how much does it cost." |
| Co | Listing current tech stack complaints. "Too many tools." |
| Tr | Requesting references, case studies, security docs. Extended evaluation. |

---

## 10. The Ockham's Razor Decision Filter

### 10.1 Principle

For any strategic decision, assume the simplest explanation for market behavior until evidence proves otherwise. This is not intellectual laziness — it is operational discipline.

### 10.2 Process

1. **Hypothesis Triage:** List all plausible explanations for a prospect's behavior, competitor's move, or market signal.
2. **Complexity Weighting (CW):** Assign each hypothesis a weight based on the number of independent assumptions required.
3. **Primary Operational Hypothesis (POH):** The lowest-CW hypothesis becomes the working assumption.
4. **Action on POH:** Act immediately. Do not wait for perfect information. The POH provides a foundation for decisive action.
5. **Continuous Validation:** Process all incoming data against the POH. Does it confirm or contradict?
6. **Escalation Protocol:** If evidence contradicts the POH, discard it immediately. Elevate the next-lowest-CW hypothesis. No ego, no sunk cost, no attachment.

### 10.3 Value

This filter prevents two common strategic failures:
- **Over-attribution:** Assuming a competitor's move is a sophisticated strategy when it's actually reactive or accidental (most common).
- **Under-attribution:** Assuming a market signal is noise when it's actually a structural shift (more dangerous when it occurs).

Starting simple and escalating only on evidence is always more efficient than starting complex and trying to simplify.

---

## 11. The Internal Adversary Protocol

### 11.1 Concept

Before executing any strategy, assume the persona of your most intelligent possible adversary. Conduct a pre-mortem: assume the strategy has already failed. Identify:

1. The three most likely failure modes
2. The single most catastrophic failure mode
3. The competitor response that would neutralize your advantage
4. The market condition change that would invalidate your assumptions

### 11.2 Application

Only after this adversarial analysis is complete should the original strategy be finalized — now fortified against the predicted failures.

This protocol transforms every strategy from "what we hope will happen" to "what survives intelligent opposition." It is the mathematical equivalent of adding a negative term to every utility calculation: the strategy's expected value minus the worst-case adversarial response.

---

## 12. Implementation: Wave Autonomous Agent

### 12.1 Integration

PUT has been implemented as the strategic intelligence layer of Wave, an autonomous AI agent with 76 tools, 6 specialist sub-agents, and self-evolving capabilities.

Wave applies PUT in real-time:
- **Prospect qualification:** Estimates U, Omega, and dominant Decision Vectors from web research, social signals, and interaction patterns
- **Sales timing:** Monitors for Ignition Conditions across the prospect pipeline
- **Pricing:** Uses the Utility Function to estimate value perception and set optimal price points
- **Competitive analysis:** Calculates Phi and FP for competitor organizations
- **Content strategy:** Creates content targeting specific Decision Vectors in identified market segments
- **Behavioral lock-in:** Designs product interactions to maximize lambda in the Identity Substitution Index

### 12.2 Results

In initial deployment, Wave autonomously:
- Identified and qualified 5 prospects in the creative agency vertical
- Applied Fracture Potential scoring (top prospect: 95/100)
- Generated personalized outreach sequences targeting dominant Decision Vectors
- Timed outreach based on Desperation Factor signals (recent funding, hiring activity)

---

## 13. Limitations and Future Work

### 13.1 Measurement Challenge

The primary limitation of PUT is variable measurement. While A, S, and w can be estimated from observable market data, k (Shadow Coefficient) and tau (Hypocrisy Index) require inference from behavioral patterns, which introduces uncertainty.

Future work should develop standardized assessment instruments for each variable, potentially using natural language processing applied to public communications, social media behavior, and decision pattern analysis.

### 13.2 Individual Calibration

The weighting coefficients (alpha, beta, gamma, delta, epsilon) vary by individual. The current framework relies on qualitative estimation based on behavioral observation. A machine learning approach — training coefficient estimators on observed purchase decision outcomes — would significantly improve predictive accuracy.

### 13.3 Cultural Variation

PUT's current formulation assumes Western market psychology. The relative weights of status (S), fear (F), and ambition (A) vary significantly across cultures. Cross-cultural calibration studies are needed.

### 13.4 Dynamic Complexity

The temporal dynamics (Section 7.3) are presented as coupled differential equations, but real-world application requires numerical simulation rather than analytical solution. Integration with agent-based modeling frameworks would enable scenario planning at scale.

---

## 14. Conclusion

Psychometric Utility Theory provides the first unified mathematical framework for predicting market behavior by modeling the interaction between ambition, fear, status, psychological vulnerability, self-deception, and identity transformation.

Its key innovations — the Shadow Coefficient, the Self-Delusion Feedback Factor, the Identity Substitution Index, and the Desperation Factor — capture psychological phenomena that existing economic models ignore. The Seven Decision Vectors provide a practical, actionable taxonomy for sales strategy optimization.

Implemented in an autonomous AI agent, PUT transforms qualitative strategic intuition into computable, repeatable, optimizable market intelligence.

The framework's philosophical lineage — from Machiavelli through Greene to mathematical formalization — represents a new synthesis: Renaissance strategic philosophy expressed as behavioral mathematics, applied through autonomous AI.

---

## References

- Greene, R. (1998). The 48 Laws of Power. Viking Press.
- Greene, R. (2001). The Art of Seduction. Viking Press.
- Greene, R. (2018). The Laws of Human Nature. Viking Press.
- Kahneman, D. & Tversky, A. (1979). Prospect Theory: An Analysis of Decision under Risk. Econometrica, 47(2), 263-291.
- Cialdini, R. (1984). Influence: The Psychology of Persuasion. Harper Business.
- Thaler, R. & Sunstein, C. (2008). Nudge: Improving Decisions About Health, Wealth, and Happiness. Yale University Press.
- Simon, H. (1955). A Behavioral Model of Rational Choice. The Quarterly Journal of Economics, 69(1), 99-118.
- Machiavelli, N. (1532). The Prince. Antonio Blado d'Asola.

---

## Appendix A: Quick Reference Card

```
PSYCHIC UTILITY FUNCTION
U = a*A*(1-Fk) - b*Fk*(1-S) + c*S*(1-w)*Sig + d*tau*kap - e*Phi

EFFECTIVE FEAR
Fk = F * (1 - k)

SELF-DELUSION
Phi = (E_ext + E_int) / (1 + |E_ext - E_int|)

IDENTITY SUBSTITUTION
Psi = 1 - e^(-lambda*t), where lambda = (A_new - A_old)^2

DESPERATION FACTOR
Omega = 1 + exp(-k_omega * (U - U_crit))

FRACTURE POTENTIAL
FP = [(1-R) * (kap + tau + Phi)] / (U_crit - U + eps)

IGNITION CONDITION
U < U_crit AND |dF/dt| > threshold AND trigger > minimum

TEMPORAL DYNAMICS
dA/dt = l1*(S-S*) - l2*Fk + l3*Omega*trigger
dF/dt = m1*(A-A_prev) - m2*status_quo + m3*Omega*threat + m4*(1-Sig)
dS/dt = s1*positive - s2*negative
```

---

*Copyright 2026 Manuel Galmanus. All rights reserved.*
*Implemented in Wave, the autonomous creative operations agent at Bluewave.*
*Contact: m.galmanus@gmail.com*
