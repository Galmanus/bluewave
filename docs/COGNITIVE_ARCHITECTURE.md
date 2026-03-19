# Cognitive Architecture — Bluewave Wave Agent

Date: 2026-03-19

## The Problem

The Wave agent system was **reactive**: message → tool call → response. No deliberation, no self-critique, no verification. Claude's natural reasoning ability was underutilized because the system structure didn't demand rigorous thinking.

## The Solution: 5-Layer Cognitive Architecture

Zero extra API calls. All improvements are structural — prompt engineering + runtime gates.

```
┌─────────────────────────────────────────────┐
│            USER MESSAGE                      │
├─────────────────────────────────────────────┤
│  Layer 1: COGNITIVE SCAFFOLD                 │
│  (think → decide → act → verify)             │
│  Injected into every agent's system prompt   │
├─────────────────────────────────────────────┤
│  Layer 2: DOMAIN-SPECIFIC PROTOCOLS          │
│  Guardian: 8-dimensional analysis pipeline   │
│  Strategist: multi-source + adversary check  │
│  Orchestrator: routing + coordination logic  │
├─────────────────────────────────────────────┤
│  Layer 3: VERIFICATION GATES                 │
│  Check specialist outputs before delivery:   │
│  - Non-empty? Non-error? Used tools?         │
│  - Hit turn limit? Actually addresses task?  │
├─────────────────────────────────────────────┤
│  Layer 4: ERROR RECOVERY HINTS               │
│  When tools fail, inject reasoning guidance: │
│  "Resource not found → search by name"       │
│  "Permission denied → inform about role"     │
├─────────────────────────────────────────────┤
│  Layer 5: ADVERSARIAL SELF-CRITIQUE          │
│  "What would a skeptic say?"                 │
│  "Am I ignoring contradicting evidence?"     │
│  "Is there a simpler explanation?"           │
└─────────────────────────────────────────────┘
```

---

## Layer 1: Cognitive Scaffold

**File:** `prompts/cognitive_protocol.md`

Injected into ALL agents via `enhance_prompt_with_cognition()` in `agent_runtime.py`.

Four mandatory phases executed internally (not verbalized to user):

| Phase | Purpose | Token cost |
|---|---|---|
| **ORIENT** | What does the user really need? What do I know/lack? | ~50 tokens |
| **DECIDE** | Strategy: direct answer, tool call, decompose, or delegate? | ~40 tokens |
| **ACT** | Execute one step at a time, evaluate before next | 0 tokens |
| **VERIFY** | Did I answer the real question? Would a critic find flaws? | ~30 tokens |

**Total overhead: ~120 tokens per response** (invisible to user, massive quality gain).

## Layer 2: Domain-Specific Protocols

### Guardian (`prompts/cognitive_guardian.md`)
5-step compliance analysis pipeline:
1. **COLETA** — load guidelines + analyze image/text
2. **ANÁLISE DIMENSIONAL** — 8 mandatory dimensions with factual observation → reference → delta → severity
3. **SCORING** — weighted average across dimensions
4. **ADVERSÁRIO INTERNO** — "If I were the designer, how would I contest this?"
5. **RECOMENDAÇÕES** — specific values (hex codes, font names), prioritized tiers

### Strategist (`prompts/cognitive_strategist.md`)
5-step analytical protocol:
1. **ENQUADRAMENTO** — What decision needs this data? What biases could I introduce?
2. **COLETA MULTI-FONTE** — Internal + external data, cross-validate
3. **ANÁLISE** — Separate vanity from value metrics, Ockham's Razor
4. **ADVERSÁRIO INTERNO** — "What would the most skeptical analyst say?"
5. **ENTREGA** — Inverted pyramid: conclusion → evidence → details

### Orchestrator (`prompts/cognitive_orchestrator.md`)
4 decision protocols:
1. **ROTEAMENTO** — Can I solve this? Which specialist is BEST (not first)?
2. **COORDENAÇÃO** — Dependency sequencing for multi-specialist tasks
3. **VALIDAÇÃO** — Does specialist result answer the original question?
4. **ANTI-OVER-ENGINEERING** — Simple question → simple answer

## Layer 3: Verification Gates

**File:** `orchestrator.py` → `_verify_specialist_result()`

5 heuristic checks applied to every specialist response, zero API calls:

| Check | Detects | Action |
|---|---|---|
| Response length < 20 chars | Empty/failed response | Flag as incomplete |
| `result.error` set | Specialist error | Flag with error context |
| Turns ≥ MAX_TURNS - 1 | Hit limit, may be truncated | Flag as potentially incomplete |
| Error keywords + 0 tool calls | Specialist gave up without trying | Flag as untried |
| 0 tool calls for action tasks | Hallucinated data instead of fetching | Flag as suspicious |

When verification fails, a `verification_warning` field is injected into the delegation result. The orchestrator (guided by cognitive_orchestrator.md) can then re-query or inform the user.

## Layer 4: Error Recovery Hints

**File:** `agent_runtime.py` → `_get_recovery_hint()`

When a tool fails, the error message now includes a `recovery_hint` field that guides Claude's next reasoning step:

| Error Pattern | Recovery Hint |
|---|---|
| "not found" / 404 | "Verify ID or search by name" |
| "connect" / "timeout" | "Service unavailable, answer from context" |
| "permission" / 403 | "Requires different role, inform user" |
| "limit" / 402 | "Plan limit reached, suggest upgrade" |
| "500" / "internal" | "Do NOT retry same call, try alternative" |
| "empty" / "no data" | "Data doesn't exist yet, guide user to create" |

**Before:** Tool fails → Claude sees `{"success": false, "message": "..."}` → retries blindly or gives up.
**After:** Tool fails → Claude sees `{"success": false, "message": "...", "recovery_hint": "..."}` → adapts strategy.

## Layer 5: Adversarial Self-Critique

Embedded in domain protocols (Layers 1 + 2). Three levels:

1. **Base (all agents):** "Would a critic find flaws? If yes, fix before delivering." (cognitive_protocol.md, Phase 4)

2. **Guardian:** "If I were the designer who created this, how would I contest this analysis? Is there a legitimate creative justification?" (cognitive_guardian.md, Step 4)

3. **Strategist:** "What would the most skeptical analyst say? Am I ignoring contradicting data? If I invert the hypothesis, do the data still support?" (cognitive_strategist.md, Step 4)

---

## Impact on Reasoning Quality

### Before (reactive)
```
User: "Is this image on-brand?"
Guardian: [calls check_compliance tool] → returns score
```

### After (deliberative)
```
User: "Is this image on-brand?"
Guardian:
  ORIENT: User needs brand compliance assessment. I have brand guidelines loaded.
  DECIDE: Need to analyze image across 8 dimensions. Will use vision + guidelines.
  ACT: [analyze image] → [compare each dimension] → [score]
  VERIFY: Did I check all 8 dimensions? Is my Delta-E calculation reasonable?
  ADVERSARY: "If I were the designer, I'd argue the pink is 'creative expression'
              — but Delta-E of 42 is objectively outside the approved palette.
              No legitimate justification at this deviation level."
  → Deliver structured 8-dimensional report with adversarial consideration noted.
```

### Concrete quality gains:
- **Compliance checks:** 8-dimensional analysis is now mandatory (was ad-hoc)
- **Analytics:** Multi-source + adversarial check prevents cherry-picking
- **Delegation:** Structured briefs instead of freeform task strings
- **Error handling:** Agents adapt strategy instead of retrying blindly
- **Edge cases:** Adversarial thinking catches false positives/negatives

---

## Files

### New (5)
- `prompts/cognitive_protocol.md` — base cognitive scaffold
- `prompts/cognitive_guardian.md` — 8-dimensional compliance protocol
- `prompts/cognitive_strategist.md` — analytical reasoning protocol
- `prompts/cognitive_orchestrator.md` — orchestration decision protocol
- `docs/COGNITIVE_ARCHITECTURE.md` — this document

### Modified (2)
- `agent_runtime.py` — `enhance_prompt_with_cognition()`, `_get_recovery_hint()`, cognitive protocol loading
- `orchestrator.py` — `_verify_specialist_result()`, cognitive enhancement, import
