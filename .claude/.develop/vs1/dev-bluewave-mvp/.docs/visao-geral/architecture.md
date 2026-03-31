# Architecture & Decisions — Bluewave MVP

## 1. Project Overview

Bluewave is a SaaS platform MVP targeting **marketing agencies**, **AV teams**, and **production companies**. It provides centralized media asset management with AI-powered caption/hashtag generation and an internal approval workflow.

---

## 2. Tech Stack Rationale

| Layer | Choice | Why |
|-------|--------|-----|
| **Backend** | Python 3.11 + FastAPI | Async-native, automatic OpenAPI docs, Pydantic validation built-in. Ideal for file uploads and I/O-bound AI calls without blocking. |
| **ORM / Migrations** | SQLAlchemy 2.0 + Alembic | Mature ecosystem, supports row-level tenant filtering via query events, Alembic gives version-controlled schema migrations. |
| **Database** | PostgreSQL | Row-level security support, JSONB for flexible metadata, battle-tested multi-tenant patterns. |
| **Frontend** | React 18 + TypeScript + Vite | Type safety catches integration bugs early. Vite gives sub-second HMR. React's ecosystem has the widest talent pool. |
| **Styling** | Tailwind CSS | Utility-first eliminates CSS specificity wars, consistent design tokens, small production bundle via purging. |
| **Server State** | TanStack React Query | Automatic cache invalidation, optimistic updates for approval workflows, built-in retry/refetch logic. |
| **Infrastructure** | Docker Compose | Single `docker compose up` for the full stack. Internal bridge network isolates services; only the reverse proxy is exposed. |

---

## 3. Multi-Tenant Strategy: Row-Level Isolation

### Why Row-Level (not Schema-per-Tenant or DB-per-Tenant)?

| Strategy | Pros | Cons |
|----------|------|------|
| **DB per tenant** | Strongest isolation | Expensive at scale, complex migrations |
| **Schema per tenant** | Good isolation | Migration nightmare with many tenants |
| **Row-level (`tenant_id`)** | Simple, scalable, single migration path | Requires discipline in every query |

**We chose row-level** because:

1. **MVP speed** — one set of tables, one migration pipeline, one connection pool.
2. **Scalability** — adding a tenant is an `INSERT`, not provisioning infrastructure.
3. **Query safety** — enforced via a SQLAlchemy session event that injects `WHERE tenant_id = :tid` on every `SELECT`, `UPDATE`, and `DELETE`. No developer can accidentally forget the filter.

### Implementation Outline

```
Request → JWT decoded → tenant_id extracted → stored in request.state
                                              ↓
                              SQLAlchemy session event reads request.state.tenant_id
                              and appends .filter(Model.tenant_id == tid) to all queries
```

- Every table that holds tenant data includes a **non-nullable `tenant_id` UUID column** with a foreign key to the `tenants` table.
- A **global `TenantMixin`** class provides this column so models inherit it consistently.
- Indexes: composite index `(tenant_id, id)` on high-traffic tables (`media_assets`, `users`).

---

## 4. Authentication & Authorization (JWT)

### Why JWT (not sessions)?

- **Stateless** — no server-side session store needed, horizontal scaling is trivial.
- **Payload carries context** — `tenant_id`, `user_id`, and `role` travel with every request, eliminating a DB lookup per request.
- **Docker-friendly** — no sticky sessions or shared Redis required for auth.

### Token Design

```json
{
  "sub": "user-uuid",
  "tenant_id": "tenant-uuid",
  "role": "admin | editor | viewer",
  "exp": 1700000000
}
```

| Parameter | Value | Reason |
|-----------|-------|--------|
| Algorithm | HS256 | Sufficient for single-issuer MVP; migrate to RS256 if third-party verification is needed later. |
| Access token TTL | 30 minutes | Short-lived to limit damage if leaked. |
| Refresh token TTL | 7 days | Stored in httpOnly cookie, rotated on use. |

### Auth Flow

```
POST /auth/login  →  validate credentials  →  return { access_token, refresh_token }
POST /auth/refresh →  validate refresh token  →  rotate & return new pair
```

### Authorization Middleware (FastAPI Dependency)

```
get_current_user(token) → decode JWT → verify exp → return UserContext(user_id, tenant_id, role)
```

- Injected as a FastAPI `Depends()` on all protected routes.
- Role-based access is enforced via a secondary dependency: `require_role("admin")`.

---

## 5. Media Upload Strategy

- **Storage (MVP):** Local volume mounted into the FastAPI container (`/app/uploads/{tenant_id}/`). Tenant-scoped directories prevent path-traversal across tenants.
- **Future:** Swap to S3-compatible storage (MinIO or AWS S3) by changing only the storage adapter — the API contract stays the same.
- **File validation:** Pydantic model validates MIME type (`image/*`, `video/*`) and enforces a 50 MB limit.
- **Async processing:** Upload endpoint returns `202 Accepted` immediately; background task (FastAPI `BackgroundTasks`) runs the simulated AI captioning.

---

## 6. Simulated AI Integration

AI features are powered by **Anthropic's Claude API** with vision support, behind an `AIServiceProtocol` interface:

- `ClaudeAIService` — Real implementation using `claude-sonnet-4-20250514` with vision. Sends base64-encoded images to Claude for analysis, generates context-aware captions and hashtags. Falls back to filename inference for non-image media.
- `StubAIService` — Deterministic fallback used when no `ANTHROPIC_API_KEY` is configured (development/testing).

**Auto-selection:** The factory function checks for `ANTHROPIC_API_KEY` at startup and instantiates the appropriate service. No code changes needed to switch between real and stub.

**Vision support:** For image uploads (JPEG, PNG, GIF, WebP up to 20MB), the actual image is sent to Claude for visual analysis. This produces significantly richer captions and more relevant hashtags than filename-only inference.

**Usage tracking:** Every AI action is logged to `ai_usage_logs` table with action type, token counts, and cost in millicents. Admin endpoint `GET /ai/usage` provides usage summaries for billing.

**Pricing per action:** Caption $0.05, Hashtags $0.05, Brand Voice $0.25, Content Brief $1.00.

---

## 7. Retry & Resilience Strategy

Both frontend and backend implement **exponential backoff with jitter** to handle transient failures gracefully, preventing cascading errors and thundering herd effects.

### Frontend — Axios Interceptor (`lib/api.ts`)

The centralized Axios instance retries failed requests transparently:

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Max retries | 3 | Enough for transient blips without delaying user feedback too long. |
| Base delay | 500ms | Backoff sequence: 500ms → 1s → 2s. |
| Jitter | ±20% | Prevents synchronized retries from multiple browser tabs. |
| Retryable status | 408, 429, 500, 502, 503, 504 | Transient server/gateway errors + rate limits. |
| Network errors | Retried | Timeout, DNS, connection refused. |

Additionally, **401 responses** trigger automatic token refresh via the `/auth/refresh` endpoint before retrying the original request.

### Backend — `@retry` Decorator (`app/core/retry.py`)

A self-contained decorator that works with both sync and async callables:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_retries` | 3 | Total attempts (first call + retries). |
| `base_delay` | 0.5s | Initial wait before first retry. |
| `max_delay` | 30s | Ceiling — delay never exceeds this. |
| `jitter_factor` | 0.2 | Random ±20% applied to each delay. |
| `retryable` | `(Exception,)` | Tuple of exception types that trigger a retry. |

**Backoff formula:** `min(base_delay × 2^(attempt−1), max_delay) ± jitter`

```
Attempt 1 fails  →  wait ~0.5s  →  retry
Attempt 2 fails  →  wait ~1.0s  →  retry
Attempt 3 fails  →  raise RetryExhausted (wraps original exception)
```

**Key design decisions:**
- **Auto-detection**: uses `asyncio.sleep` for coroutines, `time.sleep` for sync functions.
- **`RetryExhausted` exception**: raised when all attempts fail, exposes `.attempts` count and chains the original exception via `__cause__`.
- **Logging**: each retry attempt is logged at WARNING level via `logging.getLogger("bluewave.retry")`.
- **No external dependencies**: pure stdlib (asyncio, time, random, functools, logging, dataclasses).

### Current Integration Points

| Location | Decorator Config | Protects Against |
|----------|-----------------|------------------|
| `_run_ai_stubs()` background task | `@retry(max_retries=3, base_delay=1.0)` | Transient failures during AI generation + DB commit after upload. |

### Future Integration (when real AI provider replaces stubs)

```python
class OpenAIService:
    @retry(max_retries=3, base_delay=1.0, retryable=(httpx.TransportError, httpx.HTTPStatusError))
    async def generate_caption(self, filename: str, file_type: str) -> str:
        ...
```

The retry lives in the service implementation, not in the protocol — this keeps `AIServiceProtocol` clean and lets different providers choose different retry strategies.

---

## 8. Docker Network Topology

```
┌─────────────────────────────────────────────┐
│              bluewave_network (bridge)       │
│                                              │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│   │ frontend │  │ backend  │  │ postgres │  │
│   │ :5173    │  │ :8000    │  │ :5432    │  │
│   └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│        │              │              │        │
│        └──────────────┴──────────────┘        │
└─────────────────────────────────────────────┘
         ↑ exposed            ↑ exposed
       :5173                :8000
```

- PostgreSQL is **not exposed** to the host — only the backend container can reach it via the internal network.
- Frontend dev server proxies `/api/*` to the backend container.
- In production, a single Nginx container would reverse-proxy both and terminate TLS.

---

## 9. UX/UI Design Standards

The frontend must meet **international premium SaaS standards** (Linear, Vercel, Notion, Stripe Dashboard tier).

### Design System
- **Color tokens**: Semantic CSS variables for light/dark mode (background, surface, border, text-primary/secondary/tertiary, accent, success, warning, danger).
- **Typography**: Inter font family. Scale: display (28px), heading (20px), subheading (16px), body (14px), caption (12px), mono (13px).
- **Spacing**: 4px base grid. Tokens from `space-xs` (4px) to `space-3xl` (48px).
- **Elevation**: 4-level shadow system (`shadow-xs` through `shadow-lg`) + dedicated `shadow-focus` for accessibility.
- **Border radius**: 5-level system from `radius-sm` (6px) to `radius-full` (pill).

### Component Architecture
- **Base components** in `src/components/ui/`: Button, Input, Select, Badge, Card, Dialog, Toast, Avatar, Tabs, DropZone, Table, Tooltip, CommandPalette.
- Built on **Radix UI Primitives** for accessibility. Styled with **Tailwind CSS** design tokens.
- **Framer Motion** for all animations (page transitions, card hover, modal open/close).

### Key Requirements
- Dark mode support (CSS variables + `data-theme` attribute + localStorage persistence).
- WCAG 2.1 AA accessibility compliance (contrast ratios, focus rings, keyboard navigation, screen reader labels).
- Responsive design: mobile-first with breakpoints at 640/768/1024/1280/1536px.
- Motion respects `prefers-reduced-motion`.
- Custom confirmation dialogs (no native `confirm()`).
- Command palette (⌘K) for quick navigation.

### Full specification: `docs/ux_ui_design_brief.md`
