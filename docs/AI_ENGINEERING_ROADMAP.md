# Bluewave AI Engineering Roadmap

Last updated: 2026-03-19

## Completed Sprints

### Sprint 5: Code Quality, Security & Token Optimization (34 improvements)

Full codebase audit + token usage optimization from API log analysis.

**Part A: Code Quality & Security (26 fixes)**

| # | Fix | Category |
|---|---|---|
| 1 | Undefined `vision_message`/`tmp` in telegram_bridge.py | Critical Bug |
| 2 | Double API prefix in SelectionToolbar.tsx | Critical Bug |
| 3 | CORS wildcard fallback in production | Security |
| 4 | Missing `secure` flag on auth cookies | Security |
| 5 | Dedicated `reset` token type (was reusing `access`) | Security |
| 6 | Consistent password validation in reset flow | Security |
| 7 | Health check info disclosure in production | Security |
| 8 | Error message leak in wave_proxy responses | Security |
| 9 | Filename path traversal sanitization | Security |
| 10 | Token removed from URL query params | Security |
| 11 | Hardcoded server IP removed from frontend | Security |
| 12 | PIX key hardcoded fallback removed | Security |
| 13 | CONTEXT_PROMPT.md added to .gitignore | Security |
| 14 | brand_suite `_call()` sync→async | Performance |
| 15 | Silent exception swallowing → logged | Observability |
| 16 | Bare `except:` → `except Exception:` | Error Handling |
| 17 | Input validation on 8 brand suite endpoints | Reliability |
| 18 | Color regex fixed (hex validation) | Correctness |
| 19 | Axios timeout (30s) added | Reliability |
| 20 | Dockerfile runs as non-root user | Security |
| 21 | Resource limits in docker-compose.prod | Stability |
| 22 | Hedera defaults to testnet | Safety |
| 23 | .gitignore expanded (secrets, IDE, certs) | Security |
| 24 | Wave API CORS configurable via env | Security |
| 25 | brand_suite callers updated to `await` | Correctness |
| 26 | Wave API brand suite code cleaned up (PEP 8) | Maintainability |

**Part B: Token Optimization (8 improvements)**

Based on analysis of 95+ API calls showing 97% Sonnet, 3% Haiku split.

| # | Optimization | Expected Savings |
|---|---|---|
| 27 | Expanded chat patterns (+15 words, +50 char threshold) | +10-15% calls → Haiku |
| 28 | Simple question routing (status, identity, help) | +5% calls → Haiku |
| 29 | Moltbook read vs write split (feed/home → Haiku) | -14K tokens per read |
| 30 | Default fallback: 4 clusters → 2 (delegate + memory) | -40% tools on unknown intents |
| 31 | Autonomous reflect bypasses orchestrator (direct Haiku) | -14K tokens per reflect |
| 32 | Autonomous observe prefixed with moltbook hint | Routes to Haiku + moltbook tools |
| 33 | Prompt caching on soul JSON in deliberation | -90% input cost after 1st call |
| 34 | Pre-cached orchestrator tools (skip copy per call) | Reduced CPU + allocation |

**Expected impact**: Haiku % from 3% → 30-40%, -30-40% tokens per interactive session, -50% tokens on autonomous cycles.

---

### Sprint 1: Security & Resilience (11 improvements)
**Docs:** [AI_ENGINEERING_IMPROVEMENTS.md](AI_ENGINEERING_IMPROVEMENTS.md)

| # | Improvement | Category |
|---|---|---|
| 1 | Sandbox create_skill (AST validation + subprocess) | Security |
| 2 | Prompt injection defenses (XML delimiters) | Security |
| 3 | Rate limiting enforcement | Cost control |
| 4 | Universal retry with exponential backoff | Resilience |
| 5 | Streaming SSE | UX |
| 6 | Rolling context window | Stability |
| 7 | LangSmith tracing in Wave | Observability |
| 8 | Prompt templates | Maintainability |
| 9 | Structured output via tool_use | Reliability |
| 10 | Vector memory (pgvector) | Intelligence |
| 11 | Embedding-based intent routing | Accuracy |

### Sprint 2: Token Optimization (7 improvements)
**Docs:** [TOKEN_OPTIMIZATION.md](TOKEN_OPTIMIZATION.md)

| # | Improvement | Savings |
|---|---|---|
| 1 | Tool result compression | -25% tokens |
| 2 | Brand voice + guidelines cache | -6% tokens |
| 3 | Lazy-load PUT framework | -14% tokens |
| 4 | Tool pruning per intent | -12% tokens |
| 5 | Ghost agent removal | -3% tokens |
| 6 | Old tool result summarization | -15% in long sessions |
| 7 | Prompt tiering (3 levels) | -10% average |

**Overall: ~45% token reduction per session**

### Sprint 3: Cognitive Architecture (5 layers)
**Docs:** [COGNITIVE_ARCHITECTURE.md](COGNITIVE_ARCHITECTURE.md)

| Layer | What | Impact |
|---|---|---|
| 1 | Think-before-act scaffold (ORIENT → DECIDE → ACT → VERIFY) | Deliberative reasoning |
| 2 | Domain protocols (Guardian 8-dim, Strategist analytical, Orchestrator routing) | Structured expertise |
| 3 | Verification gates (5 heuristic checks on specialist outputs) | Error detection |
| 4 | Error recovery hints (contextual guidance on tool failures) | Adaptive behavior |
| 5 | Adversarial self-critique (3 levels of internal challenge) | Quality assurance |

### Sprint 4: API-Level Efficiency (6 optimizations)
**Docs:** [AI_EFFICIENCY_FINAL.md](AI_EFFICIENCY_FINAL.md)

| # | Improvement | Impact |
|---|---|---|
| 1 | Prompt caching (cache_control) | -67% input cost |
| 2 | Extended thinking | +Quality on complex tasks |
| 3 | Parallel tool execution | -50% latency |
| 4 | Response prefill | Format consistency |
| 5 | Batch API | -50% cost for bulk ops |
| 6 | Eval framework | Measurable quality |

---

## Cumulative Impact

### Cost
| Before | After Sprint 1-2 | After Sprint 3-4 | After Sprint 5 | Total |
|---|---|---|---|---|
| $1.00/session | $0.55/session | $0.18/session | $0.11/session | **-89%** |

### Quality
| Metric | Before | After |
|---|---|---|
| Compliance analysis depth | Ad-hoc | 8 mandatory dimensions |
| Self-critique | None | 3-level adversarial checking |
| Error recovery | Blind retry | Contextual hints |
| Specialist verification | None | 5 heuristic gates |
| Intent accuracy | ~80% (keywords) | ~95% (embeddings + keywords) |

### Performance
| Metric | Before | After |
|---|---|---|
| Greeting response | ~2.5s | ~0.8s |
| Multi-tool turn | ~1.5s | ~0.6s |
| 5-turn session tokens | ~35K | ~12K |
| Compliance check latency | ~4s | ~3s |

---

## Architecture Summary

```
User Message
    │
    ▼
┌─ Intent Router (embedding + keyword, ~5ms) ─────────────┐
│  Assigns: model, tools, prompt tier, thinking budget     │
└──────────────────────────────────────────────────────────┘
    │
    ▼
┌─ Orchestrator ───────────────────────────────────────────┐
│  Cognitive Protocol: ORIENT → DECIDE → ACT → VERIFY      │
│  Prompt Caching: system + tools cached at 90% discount    │
│  Extended Thinking: 2K-5K budget for complex intents      │
│  Context Manager: rolling window + old result compression │
│  Tool Optimizer: compress results before appending        │
├──────────────────────────────────────────────────────────┤
│  ┌─ Specialist (parallel execution) ────────────────┐    │
│  │  Cognitive Protocol (domain-specific)             │    │
│  │  Prompt Caching on system + tools                 │    │
│  │  Parallel tool execution via asyncio.gather       │    │
│  │  Error recovery hints on tool failures            │    │
│  └──────────────────────────────────────────────────┘    │
│  ┌─ Verification Gate ──────────────────────────────┐    │
│  │  5 heuristic checks before accepting result       │    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
    │
    ▼
┌─ Response ───────────────────────────────────────────────┐
│  Prefill (compliance reports)                             │
│  SSE Streaming (progressive UI)                           │
│  Token tracking (cumulative per session)                  │
└──────────────────────────────────────────────────────────┘
```

---

## Future Opportunities

| Opportunity | Impact | Effort | Notes |
|---|---|---|---|
| Fine-tuned classification model | Replace embedding router with 99%+ accuracy classifier | Medium | Requires training data from eval framework |
| Multi-modal caching | Cache image analysis results | Medium | Avoid re-analyzing same image across sessions |
| Speculative prefetch | Pre-load likely-needed data based on intent | Low | e.g., auto-load guidelines when brand intent detected |
| Agent memory consolidation | Periodic summarization of JSONL/vector memories | Low | Prevent unbounded memory growth |
| Cost alerting | Real-time Slack/Telegram alert when daily spend > threshold | Low | Use tracing data |
| A/B prompt testing | Compare prompt variants via eval framework | Medium | Requires sufficient traffic volume |

---

## File Index

| Doc | Content |
|---|---|
| [AI_ENGINEERING_IMPROVEMENTS.md](AI_ENGINEERING_IMPROVEMENTS.md) | Sprint 1: Security, resilience, architecture |
| [TOKEN_OPTIMIZATION.md](TOKEN_OPTIMIZATION.md) | Sprint 2: Token efficiency |
| [COGNITIVE_ARCHITECTURE.md](COGNITIVE_ARCHITECTURE.md) | Sprint 3: Reasoning quality |
| [AI_EFFICIENCY_FINAL.md](AI_EFFICIENCY_FINAL.md) | Sprint 4: API-level optimizations |
| [AI_ENGINEERING_ROADMAP.md](AI_ENGINEERING_ROADMAP.md) | This file — consolidated roadmap |
