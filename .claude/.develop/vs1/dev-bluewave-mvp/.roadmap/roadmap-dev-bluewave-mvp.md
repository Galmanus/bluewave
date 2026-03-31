# Execution Plan — Bluewave MVP

> Strict chronological order. Each step depends on the previous one being complete.
> Estimated scope: 7 phases, meant to be executed sequentially to avoid integration conflicts.

---

## Step 1 — Docker Compose & Dev Environment

**Priority:** FIRST — everything else runs inside containers.

| # | Task | Output |
|---|------|--------|
| 1.1 | Create project root structure: `backend/`, `frontend/`, `docker/` | Folder skeleton |
| 1.2 | Write `backend/Dockerfile` (Python 3.11-slim, pip install, uvicorn) | Dockerfile |
| 1.3 | Write `frontend/Dockerfile` (Node 20-alpine, npm install, vite dev) | Dockerfile |
| 1.4 | Write `docker-compose.yml` with `postgres`, `backend`, `frontend` services | Compose file |
| 1.5 | Define `bluewave_network` bridge, ensure postgres is internal-only | Network config |
| 1.6 | Create `.env.example` with all required vars | Env template |
| 1.7 | **Checkpoint:** `docker compose up` — all 3 containers healthy | Green status |

---

## Step 2 — Database Models & Alembic Migrations

**Priority:** SECOND — backend routes need tables to exist.

| # | Task | Output |
|---|------|--------|
| 2.1 | Init FastAPI project structure (`main.py`, `core/`, `models/`, `routers/`, `schemas/`, `services/`) | Project scaffold |
| 2.2 | Configure SQLAlchemy async engine + session factory in `core/database.py` | DB config |
| 2.3 | Create `models/base.py` with `TenantMixin` (adds `tenant_id` UUID FK) | Base model |
| 2.4 | Create `models/tenant.py` — `tenants` table | Model |
| 2.5 | Create `models/user.py` — `users` table (with role enum) | Model |
| 2.6 | Create `models/asset.py` — `media_assets` table (with status enum) | Model |
| 2.7 | Init Alembic, generate initial migration | Migration file |
| 2.8 | **Checkpoint:** migration runs inside Docker, tables visible in psql | Verified schema |

---

## Step 3 — JWT Auth System (Backend)

**Priority:** THIRD — all subsequent routes require authentication.

| # | Task | Output |
|---|------|--------|
| 3.1 | `core/security.py` — JWT encode/decode (HS256), bcrypt password hash/verify | Security utils |
| 3.2 | `core/config.py` — Pydantic `Settings` class reading from env | Config |
| 3.3 | `schemas/auth.py` — `LoginRequest`, `RegisterRequest`, `TokenResponse` | Pydantic models |
| 3.4 | `routers/auth.py` — `POST /register` (creates tenant + admin user) | Route |
| 3.5 | `routers/auth.py` — `POST /login` (returns access token, sets refresh cookie) | Route |
| 3.6 | `routers/auth.py` — `POST /refresh`, `POST /logout` | Routes |
| 3.7 | `core/deps.py` — `get_current_user` dependency (decodes JWT, returns UserContext) | Dependency |
| 3.8 | `core/deps.py` — `require_role("admin")` dependency | Dependency |
| 3.9 | Tenant-scoped SQLAlchemy session event (auto-filter by `tenant_id`) | Middleware |
| 3.10 | **Checkpoint:** register → login → hit protected endpoint → success; wrong tenant → 403 | Verified auth |

---

## Step 4 — Core Business Routes (Backend)

**Priority:** FOURTH — depends on auth + models being ready.

| # | Task | Output |
|---|------|--------|
| 4.1 | `schemas/user.py`, `schemas/asset.py` — request/response Pydantic models | Schemas |
| 4.2 | `routers/users.py` — GET /users/me, GET /users, POST /users, PATCH, DELETE | CRUD routes |
| 4.3 | `routers/assets.py` — GET list (paginated + filtered), GET single, POST upload, PATCH, DELETE | CRUD routes |
| 4.4 | File upload logic: MIME validation, size check, save to `uploads/{tenant_id}/` | Upload handler |
| 4.5 | `services/ai_service.py` — stub `generate_caption()`, `generate_hashtags()` | AI stubs |
| 4.6 | Background task: after upload, auto-run AI stubs and update asset record | Background task |
| 4.7 | `routers/workflow.py` — POST submit, approve, reject with state machine validation | Workflow routes |
| 4.8 | **Checkpoint:** full API lifecycle via curl/httpie: upload → AI fills metadata → submit → approve | Verified API |

---

## Step 5 — Frontend Setup & Auth UI

**Priority:** FIFTH — depends on backend auth endpoints being stable.

| # | Task | Output |
|---|------|--------|
| 5.1 | Init Vite + React + TypeScript project in `frontend/` | Scaffold |
| 5.2 | Install & configure Tailwind CSS | Styling |
| 5.3 | `lib/api.ts` — Axios instance with base URL, JWT interceptor, refresh logic | API client |
| 5.4 | `contexts/AuthContext.tsx` — stores token, exposes login/logout/user | Auth state |
| 5.5 | `pages/LoginPage.tsx` — email + password form | Page |
| 5.6 | `pages/RegisterPage.tsx` — tenant name + admin user form | Page |
| 5.7 | `components/AuthGuard.tsx` — redirects unauthenticated users to /login | Guard |
| 5.8 | `components/RoleGuard.tsx` — redirects insufficient roles to / | Guard |
| 5.9 | Wire up React Router with guards (see routing doc) | Router config |
| 5.10 | **Checkpoint:** register → login → see empty dashboard shell → logout → redirect | Verified auth UI |

---

## Step 6 — Frontend Dashboard & Asset Management

**Priority:** SIXTH — depends on frontend auth + backend CRUD being stable.

| # | Task | Output |
|---|------|--------|
| 6.1 | `components/AppLayout.tsx` — sidebar nav + header (tenant name, user, logout) | Layout |
| 6.2 | `hooks/useAssets.ts` — React Query hooks for asset CRUD | Hooks |
| 6.3 | `pages/AssetListPage.tsx` — grid view + status filter tabs | Page |
| 6.4 | `pages/AssetDetailPage.tsx` — preview, caption/hashtags edit, approval buttons | Page |
| 6.5 | `pages/UploadPage.tsx` — drag-and-drop zone + progress bar | Page |
| 6.6 | Approval action buttons with role-based visibility (submit/approve/reject) | UI logic |
| 6.7 | `pages/TeamPage.tsx` — user list + invite form (admin only) | Page |
| 6.8 | **Checkpoint:** full E2E flow through the browser UI | Verified UI |

---

## Step 7 — Polish & Integration

**Priority:** LAST — everything functional, now make it solid.

| # | Task | Output |
|---|------|--------|
| 7.1 | Toast notifications for API errors (react-hot-toast or similar) | UX |
| 7.2 | Frontend retry with exponential backoff in Axios interceptor (3 retries, 500ms base, ±20% jitter, retryable: 408/429/5xx + network errors) + automatic 401 token refresh | Resilience |
| 7.3 | Backend `@retry` decorator (`app/core/retry.py`) — exponential backoff with jitter, sync/async auto-detection, configurable retryable exceptions, `RetryExhausted` exception | Resilience |
| 7.4 | Apply `@retry(max_retries=3, base_delay=1.0)` to `_run_ai_stubs()` background task | Resilience |
| 7.5 | Unit tests for retry module (`tests/test_retry.py` — 15 tests covering async/sync, exhaustion, jitter bounds, non-retryable passthrough) | Tests |
| 7.6 | Skeleton loaders on data-fetching pages | UX |
| 7.7 | Responsive check (desktop-first, tablet not broken) | QA |
| 7.8 | Docker Compose healthchecks for all services | DevOps |
| 7.9 | Full E2E manual test: register → upload → AI → submit → approve | Final QA |
| 7.10 | `README.md` with setup instructions | Docs |
| 7.11 | **Checkpoint:** demo-ready MVP | Done |

---

## Step 8 — UX/UI Premium Redesign

**Priority:** After MVP functional completion — elevate to international premium standards.

**Design Reference:** Linear, Vercel Dashboard, Notion, Stripe Dashboard, Figma.

| # | Task | Output |
|---|------|--------|
| 8.1 | ~~Extend `tailwind.config.js` with full design token system~~ | ✅ Done |
| 8.2 | ~~Install Radix UI, Framer Motion, Lucide React, cmdk, react-dropzone, sonner~~ | ✅ Done |
| 8.3 | ~~Build reusable component library in `src/components/ui/` (13/13: Button, Input, Select, Badge, Card, Dialog, Avatar, Tabs, Table, Tooltip, CommandPalette, DropZone)~~ | ✅ Done |
| 8.4 | ~~Implement dark mode via CSS variables + `data-theme` + localStorage + `prefers-color-scheme`~~ | ✅ Done |
| 8.5 | ~~Redesign LoginPage + RegisterPage (gradient bg, logo, password strength bar)~~ | ✅ Done |
| 8.6 | ~~Redesign AppLayout (collapsible sidebar 240→64px, Lucide icons, theme toggle, user avatar)~~ | ✅ Done |
| 8.7 | ~~Redesign AssetListPage (display typography, count badges, animated tab indicator, stagger fade-in)~~ | ✅ Done |
| 8.8 | ~~Redesign AssetDetailPage (2-panel 60/40, Framer Motion animations, Radix Dialog for delete)~~ | ✅ Done |
| 8.9 | ~~Redesign UploadPage (react-dropzone, 60vh drop zone, animated states, success checkmark)~~ | ✅ Done |
| 8.10 | ~~Redesign TeamPage (initials avatars, slide-down invite panel, Radix Dialog for delete)~~ | ✅ Done |
| 8.11 | ~~Framer Motion animation layer (page transitions, card hover, tab slide, modal)~~ | ✅ Done |
| 8.12 | ~~Focus rings, aria-labels, semantic color tokens for contrast~~ | ✅ Done |
| 8.13 | ~~Replace native `confirm()` with custom Radix Dialog component~~ | ✅ Done |
| 8.14 | ~~Replace react-hot-toast with sonner (bottom-right, rich colors)~~ | ✅ Done |
| 8.15 | ~~Responsive QA — grids scale at all breakpoints, `prefers-reduced-motion` global override~~ | ✅ Done |
| 8.16 | **Checkpoint:** premium UI in light + dark mode, 13/13 components, animations, accessible, ⌘K palette | ✅ Done |

**Full design spec:** `docs/ux_ui_design_brief.md`

---

## Step 9 — Landing Page (Marketing Site)

**Priority:** After premium UI — the public face of the product.

**Market research:** `docs/market_research.md`
**Full implementation spec:** `docs/landing_page_prompt.md`

| # | Task | Output |
|---|------|--------|
| 9.1 | ~~Create `LandingPage.tsx` and 10 landing section components in `components/landing/`~~ | ✅ Done |
| 9.2 | ~~Hero section — animated gradient, headline, dual CTAs, app mockup~~ | ✅ Done |
| 9.3 | ~~Pain Points section — 3 cards with validated market stats~~ | ✅ Done |
| 9.4 | ~~Product Showcase — 4 alternating feature sections with scroll-triggered Framer Motion~~ | ✅ Done |
| 9.5 | ~~Social Proof — metrics count-up animation + 3 testimonial cards~~ | ✅ Done |
| 9.6 | ~~Pricing — 3-tier transparent pricing (Free/$12/Enterprise) with monthly/annual toggle~~ | ✅ Done |
| 9.7 | ~~How It Works — 4-step horizontal flow (Create → Upload → Submit → Ship)~~ | ✅ Done |
| 9.8 | ~~Comparison table — Bluewave vs. Bynder, Air.inc, Frame.io, Google Drive~~ | ✅ Done |
| 9.9 | ~~FAQ — Radix Accordion, 6 questions covering objections~~ | ✅ Done |
| 9.10 | ~~Final CTA + Footer — dark section, strong CTA, 4-column footer~~ | ✅ Done |
| 9.11 | ~~SEO meta tags (title, OG, Twitter), non-blocking font load, preconnect~~ | ✅ Done |
| 9.12 | ~~Update routing: `/` → LandingPage (public)~~ | ✅ Done |
| 9.13 | ~~Mobile responsive — grids scale, comparison table scrolls, pricing stacks~~ | ✅ Done |
| 9.14 | **Checkpoint:** landing page live, all 10 sections, SEO meta tags, responsive | ✅ Done |

---

## Step 10 — Real AI Integration (Claude API) ✅

**Priority:** First 10x feature — unlocks usage-based revenue immediately.

| # | Task | Output |
|---|------|--------|
| 10.1 | ~~Add `anthropic==0.43.0` to requirements.txt~~ | ✅ Done |
| 10.2 | ~~Add `ANTHROPIC_API_KEY` + `AI_MODEL` to Settings, .env, docker-compose.yml~~ | ✅ Done |
| 10.3 | ~~Implement `ClaudeAIService` with vision (base64 image → Claude API)~~ | ✅ Done |
| 10.4 | ~~Make `AIServiceProtocol` async~~ | ✅ Done |
| 10.5 | ~~Auto-select Claude vs. Stub based on API key presence~~ | ✅ Done |
| 10.6 | ~~Create `AIUsageLog` model + `ai_usage_logs` table~~ | ✅ Done |
| 10.7 | ~~Create Alembic migration for `ai_usage_logs`~~ | ✅ Done |
| 10.8 | ~~Create `ai_usage.py` helper with cost table~~ | ✅ Done |
| 10.9 | ~~Update assets router: async AI, pass `file_path` for vision, log usage~~ | ✅ Done |
| 10.10 | ~~Update AI router: async calls, log usage on regenerate~~ | ✅ Done |
| 10.11 | ~~Add `GET /ai/usage` endpoint — admin-only usage summary~~ | ✅ Done |
| 10.12 | **Checkpoint:** real Claude vision captions + usage tracking | ✅ Done |

---

## Step 10.5 — OpenClaw Integration + Webhooks + API Keys ✅

**Priority:** Enable external integrations — connects Bluewave to OpenClaw, Zapier, and custom workflows.

| # | Task | Output |
|---|------|--------|
| 10.5.1 | ~~Create `Webhook` model + `webhooks` table (name, url, secret, events, is_active)~~ | ✅ Done |
| 10.5.2 | ~~Create `APIKey` model + `api_keys` table (name, key_hash, prefix, created_by)~~ | ✅ Done |
| 10.5.3 | ~~Webhook delivery service with HMAC-SHA256 signing + retry~~ | ✅ Done |
| 10.5.4 | ~~`emit_event()` dispatches to matching webhooks on state changes~~ | ✅ Done |
| 10.5.5 | ~~Update `get_current_user` to support JWT Bearer + `X-API-Key` dual auth~~ | ✅ Done |
| 10.5.6 | ~~CRUD endpoints for webhooks + API keys (admin only)~~ | ✅ Done |
| 10.5.7 | ~~OpenClaw skill package: SKILL.md + config example + README~~ | ✅ Done |
| 10.5.8 | ~~IntegrationsPage.tsx: API key create/revoke + webhook create/toggle/delete~~ | ✅ Done |
| 10.5.9 | ~~Alembic migration for webhooks + api_keys tables~~ | ✅ Done |
| 10.5.10 | **Checkpoint:** API key auth on all endpoints, webhooks fire on workflow, OpenClaw skill ready | ✅ Done |

**OpenClaw skill:** `openclaw-skill/` directory with SKILL.md, config example, README.

---

## Step 18 — Trend Intelligence Agent ✅

**Priority:** AI-powered content timing — know what to create and when to publish.

| # | Task | Output |
|---|------|--------|
| 18.1 | ~~`TrendEntry` model + `trend_entries` table (keyword, source, volume, sentiment, AI fields, expiry)~~ | ✅ Done |
| 18.2 | ~~`trend_service.py` — Google Trends fetcher (pytrends) + X/Twitter fetcher (API v2) + combined pipeline~~ | ✅ Done |
| 18.3 | ~~`analyze_trends_with_ai()` — Claude scores relevance, generates suggestion + caption draft + hashtags~~ | ✅ Done |
| 18.4 | ~~`trends` router: POST /discover, GET /trends, GET /trends/{id}, DELETE /trends/expired~~ | ✅ Done |
| 18.5 | ~~`X_BEARER_TOKEN` config + pytrends dependency~~ | ✅ Done |
| 18.6 | ~~`TrendsPage.tsx` — discover form, trend cards with relevance bars, copy-to-clipboard~~ | ✅ Done |
| 18.7 | ~~Alembic migration for `trend_entries` table~~ | ✅ Done |
| 18.8 | **Checkpoint:** discover triggers fetch → AI analysis → cards with suggestions + captions + hashtags | ✅ Done |

---

## Steps 11–17 — 10x Platform Features (Planned)

**Strategy:** `docs/10x_strategy.md`
**Implementation spec:** `docs/10x_implementation_prompt.json`

| Step | Feature | Est. Time | Revenue Unlock | Status |
|------|---------|-----------|----------------|--------|
| 11 | Brand Compliance Engine | 3 weeks | Pro tier $29/user | ✅ Done |
| 12 | White-Label Client Portals | 3 weeks | $29/portal add-on | Planned |
| 13 | Analytics & ROI Dashboard | 2 weeks | Retention ×1.5 | Planned |
| 14 | Multi-Channel Distribution | 4 weeks | Business tier $49/user | Planned |
| 15 | Workflow Automation Builder | 4 weeks | Enterprise $149/user | Planned |
| 16 | Brand Voice AI Training | 3 weeks | $0.25/gen (data moat) | Planned |
| 17 | Content Calendar & Scheduling | 2 weeks | Platform completeness | Planned |

---

## Dependency Graph

```
Step 1 (Docker)
  └──► Step 2 (DB Models)
         └──► Step 3 (Auth Backend)
                ├──► Step 4 (Business Routes)
                │      └──────────┐
                └──► Step 5 (Auth UI)
                       └──► Step 6 (Dashboard UI)
                               └──► Step 7 (Polish)
                                       └──► Step 8 (UX/UI Premium Redesign)
                                               └──► Step 9 (Landing Page)
                                                       └──► Step 10 (Real AI — Claude API)
                                                               └──► Step 10.5 (OpenClaw + Webhooks + API Keys)
                                                                       └──► Step 18 (Trend Intelligence Agent)
                                                                               └──► Step 11 (Brand Compliance Engine) ← CURRENT
                                                               └──► Step 11 (Brand Compliance)
                                                                       └──► Step 12 (Client Portals)
                                                                               └──► Step 13 (Analytics)
                                                                                       ├──► Step 14 (Distribution)
                                                                                       │       └──► Step 17 (Calendar)
                                                                                       └──► Step 15 (Automations)
                                                                                               └──► Step 16 (Brand Voice AI)
```
