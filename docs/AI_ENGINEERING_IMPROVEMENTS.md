# AI Engineering Improvements — Bluewave v2

Date: 2026-03-19

## Summary

11 AI engineering improvements implemented across security, resilience, performance, observability, and architecture. All changes are backwards-compatible.

---

## 1. Sandbox `create_skill` (CRITICAL — Security)

**File:** `openclaw-skill/skills/self_evolve.py`

Wave can create Python skills at runtime. Previously, generated code ran with full system access. Now:

- **AST validation**: All generated code is parsed and checked against an import allowlist (`httpx`, `json`, `re`, `bs4`, `asyncio`, etc.) and a forbidden call blocklist (`os.environ`, `subprocess`, `eval`, `exec`, `open`, `__import__`)
- **Sandboxed execution**: Validation runs in a subprocess with restricted environment variables (no API keys leaked)
- **Protected skills**: Core skill files cannot be overwritten
- **Audit logging**: All skill creations/deletions are logged with security gate results

**Allowed imports:** httpx, json, re, bs4, asyncio, datetime, math, hashlib, base64, urllib.parse, collections, duckduckgo_search
**Blocked:** os.environ, subprocess, eval, exec, open(), \_\_import\_\_, getattr, setattr

---

## 2. Prompt Injection Defenses (HIGH — Security)

**Files:** `backend/app/core/prompt_safety.py` (new), all AI service files

- **`sanitize_for_prompt()`**: Strips XML tags, control characters, and truncates to max length
- **`wrap_user_input()`**: Wraps untrusted data in XML delimiters (`<filename>...</filename>`) so Claude treats it as data, not instructions
- **`strip_markdown_codeblock()`**: Robust extraction of JSON from Claude responses

Applied to:
- `ai_service.py` — filename/file_type now wrapped in XML tags
- `compliance_service.py` — custom_rules sanitized before prompt inclusion
- `brief_service.py` — user prompt wrapped in `<user_prompt>` tags (highest risk)
- `trend_service.py` — tenant_niche and existing_hashtags wrapped in XML tags
- `BrandPage.tsx` — brandName sanitized client-side, XML-delimited

---

## 3. Rate Limiting Enforcement (HIGH — Cost Control)

**File:** `backend/app/routers/ai.py`

`check_ai_limit` dependency from `plan_limits.py` now applied to all AI endpoints:
- `POST /ai/caption/{id}` — requires plan quota
- `POST /ai/hashtags/{id}` — requires plan quota
- `POST /ai/caption/{id}/translate` — requires plan quota + language validation

Free tier: 50 AI actions/month. Pro/Business/Enterprise: unlimited.
Returns HTTP 402 when limit exceeded.

Also added language code validation for translate endpoint (whitelist of 18 language codes).

---

## 4. Universal Retry with Exponential Backoff (HIGH — Resilience)

**Files:** `backend/app/services/ai_service.py`, `brief_service.py`

- **`ai_service.py`**: New `_call_claude()` method with `@retry(max_retries=3, base_delay=1.0)` for `RateLimitError`, `InternalServerError`, `APIConnectionError`
- **`brief_service.py`**: Added `_call_claude_for_brief()` with same retry decorator
- **`trend_service.py`**: Already had retry on fetchers; now AI analysis call has tracing

Retry handles: 429 (rate limit), 500 (server error), connection failures.
Exponential backoff with ±20% jitter prevents thundering herd.

---

## 5. Streaming SSE (MEDIUM — UX)

**Files:** `openclaw-skill/api.py`, `orchestrator.py`, `frontend/src/pages/WaveAgentPage.tsx`

**Backend:**
- `POST /chat/stream` — SSE endpoint that emits events: `chunk`, `tool_start`, `tool_end`, `done`, `error`
- `Orchestrator.chat_streaming()` — new method with callback hooks for progressive UI
- Falls back to regular `/chat` if streaming unavailable

**Frontend:**
- WaveAgentPage tries `/chat/stream` first with `ReadableStream` reader
- Progressively updates assistant message as chunks arrive
- Falls back to regular POST on failure
- Session ID now uses `crypto.randomUUID()` instead of `Date.now()`

---

## 6. Rolling Context Window (MEDIUM — Stability)

**File:** `openclaw-skill/context_manager.py` (new)

Prevents token budget exhaustion in long conversations:
- **Token estimation**: chars/4 heuristic per message
- **Threshold**: Triggers at 75% of 120K token limit (configurable)
- **Summarization**: Older messages compressed into a summary; recent 10 kept verbatim
- **Cost tracking**: Cumulative input/output tokens tracked per session

Integrated into `Orchestrator._call_claude()` — runs `prepare_messages()` before every Claude call.

---

## 7. LangSmith Tracing in Wave Orchestrator (MEDIUM — Observability)

**File:** `openclaw-skill/orchestrator.py`

- Every `chat()` call traces: intent category, complexity, model, tools count, estimated tokens, context stats
- Every delegation traces: from/to agent, task, response preview, duration
- Token usage tracked per-response via `context_manager.track_usage()`
- Uses existing `skills/tracing.py` module (LangSmith)

---

## 8. Prompt Templates (MEDIUM — Maintainability)

**Files:** `backend/app/prompts/` (new directory)

Prompts extracted from inline Python strings to versioned `.txt` files:
- `caption_system.txt` — caption generation system prompt
- `hashtags_system.txt` — hashtag generation system prompt
- `brief_system.txt` — content brief system prompt
- `compliance_check.txt` — compliance analysis prompt
- `trend_analysis.txt` — trend analysis prompt

Loader: `app/prompts/__init__.py` with `load_prompt()` function, LRU cache, and `reload_prompts()` for hot-reload.

---

## 9. Structured Output via tool_use (MEDIUM — Reliability)

**File:** `backend/app/services/compliance_service.py`

Compliance check now uses Claude's `tool_use` with `tool_choice={"type": "tool", "name": "compliance_result"}` to force structured JSON output.

**Before:** Asked Claude to return raw JSON, then parsed with fragile regex
**After:** Claude must call the `compliance_result` tool with typed schema — score (int), summary (string), issues (array of objects with severity enum)

Eliminates JSON parsing failures entirely.

---

## 10. Vector Memory (pgvector) (LOW — Intelligence)

**File:** `openclaw-skill/vector_memory.py` (new)

Replaces JSONL flat-file memory with PostgreSQL + pgvector:
- **Semantic search**: Find memories by meaning using MiniLM-L6 embeddings (384-dim)
- **Deduplication**: Cosine similarity > 0.85 = duplicate, skip save
- **Graceful fallback**: If database/pgvector unavailable, falls back to JSONL
- **Same tool API**: `save_learning`, `recall_learnings`, `save_strategy`, etc.

Table: `agent_memories` with columns: content, topic, source, importance, memory_type, embedding (vector(384)), metadata (JSONB).

Registered in `skills_handler.py` — vector_memory takes priority over JSONL learning module when available.

---

## 11. Embedding-based Intent Routing (LOW — Accuracy)

**File:** `openclaw-skill/intent_router.py`

**Before:** Keyword matching (`any(w in msg_lower for w in ["brand", ...]`))
**After:** Cosine similarity against precomputed category embeddings

- 12 intent categories with 5-10 example phrases each
- MiniLM-L6 embeddings precomputed at startup (~50ms)
- Classification: ~5ms per message (no API call, no tokens)
- Confidence threshold: 0.4 minimum for embedding result
- Fallback: keyword heuristics for low-confidence matches
- Configurable: `OPENCLAW_EMBEDDING_ROUTER=false` to disable

Fixes: "help with my brand new asset" no longer misclassifies as "brand" — the full sentence embedding matches "assets" category more closely.

---

## New Dependencies

### Backend (pip)
- No new dependencies — all existing packages used

### Openclaw-skill (pip)
- `sentence-transformers` — for MiniLM-L6 embeddings (optional, graceful fallback)
- `asyncpg` — for vector memory PostgreSQL access (optional, falls back to JSONL)
- `numpy` — for embedding cosine similarity (already available via sentence-transformers)

### Frontend (npm)
- No new dependencies

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENCLAW_MAX_CONTEXT_TOKENS` | 120000 | Max tokens before context compression |
| `OPENCLAW_KEEP_RECENT` | 10 | Messages to keep after compression |
| `OPENCLAW_EMBEDDING_ROUTER` | true | Enable embedding-based intent routing |
| `BLUEWAVE_DATABASE_URL` | — | PostgreSQL URL for vector memory |

---

## Files Changed

### New Files
- `backend/app/core/prompt_safety.py`
- `backend/app/prompts/__init__.py`
- `backend/app/prompts/caption_system.txt`
- `backend/app/prompts/hashtags_system.txt`
- `backend/app/prompts/brief_system.txt`
- `backend/app/prompts/compliance_check.txt`
- `backend/app/prompts/trend_analysis.txt`
- `openclaw-skill/context_manager.py`
- `openclaw-skill/vector_memory.py`

### Modified Files
- `openclaw-skill/skills/self_evolve.py` — sandbox + AST validation
- `openclaw-skill/orchestrator.py` — context mgmt + tracing + streaming
- `openclaw-skill/intent_router.py` — embedding classification
- `openclaw-skill/api.py` — SSE streaming endpoint
- `openclaw-skill/skills_handler.py` — vector memory registration
- `backend/app/services/ai_service.py` — prompt templates + retry + XML tags
- `backend/app/services/compliance_service.py` — tool_use + prompt safety
- `backend/app/services/brief_service.py` — retry + prompt safety + templates
- `backend/app/services/trend_service.py` — tracing + prompt safety
- `backend/app/routers/ai.py` — rate limiting + language validation
- `frontend/src/pages/WaveAgentPage.tsx` — SSE streaming + crypto.randomUUID
- `frontend/src/pages/BrandPage.tsx` — prompt injection fix
