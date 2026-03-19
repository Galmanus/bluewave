# Changelog

## v0.4.0 — 20 Melhorias: De MVP a Produto Competitivo (2026-03-18)

Release que implementa 20 melhorias em 4 tiers, transformando o MVP funcional em produto competitivo de mercado. Score de maturidade subiu de **9.0/10** para **9.5/10**.

### Tier 1 — Quick Wins

#### IMP-1: Email Transacional (Resend)
- Novo serviço `backend/app/services/email_service.py` — 4 funções async fire-and-forget
- `send_password_reset()` — email com link de reset e botão azul
- `send_user_invitation()` — email com credenciais temporárias ao criar usuário
- `send_monthly_report()` — PDF anexado com KPIs do mês
- `send_asset_notification()` — notificação de workflow (submetido/aprovado/rejeitado)
- Integrado em: `auth.py` (reset), `users.py` (convite), `workflow.py` (notificações)
- 3 novas settings: `RESEND_API_KEY`, `EMAIL_FROM`, `APP_URL`
- Graceful degradation: se API key vazia, log no console

#### IMP-2: Fix Test Suite
- `conftest.py` reescrito com custom type compilers para SQLite
- `PG_UUID` → `CHAR(36)`, `JSONB` → `TEXT`, `ARRAY` → `TEXT` com serializers JSON
- Testes agora rodam com SQLite in-memory sem PostgreSQL

#### IMP-3: Asset Thumbnails
- Novo serviço `backend/app/services/thumbnail_service.py` — Pillow WebP 400x400
- Coluna `thumbnail_path` adicionada ao modelo `MediaAsset`
- Endpoint `GET /assets/:id/thumbnail` com auth via Bearer ou `?token=`
- Componente `AssetThumbnail.tsx` — lazy loading, fallback para ícone
- Thumbnails gerados em background após upload

#### IMP-4: Busca Full-Text (tsvector)
- Migration com: `search_vector tsvector`, GIN index, trigger function, backfill
- Pesos: caption (A) > hashtags (B) > filename (C)
- `plainto_tsquery('english', q)` no endpoint de listagem com fallback ILIKE

#### IMP-5: Export Bulk (ZIP)
- Endpoint `POST /assets/export` — body: `{asset_ids: list[UUID]}`
- ZIP com pasta `files/` + `metadata.csv` (id, filename, caption, hashtags, status, compliance_score)
- Limites: 100 assets, 500MB total
- Componente `SelectionToolbar.tsx` — toolbar flutuante com contagem e ações

### Tier 2 — Competitive Differentiators

#### IMP-6: Auto-Resize Inteligente
- Serviço `resize_service.py` — smart center-crop + resize para 8 formatos sociais
- Formatos: Instagram Feed/Story, Facebook, Twitter, LinkedIn Post/Banner, YouTube, Pinterest
- Router `resize.py` — `POST /assets/:id/resize`, `GET /assets/:id/variants`, serve variant files
- Modelo `AssetVariant` — format_name, width, height, file_path, file_size
- Cada resize logado como AI action ($0.05)

#### IMP-7: Content Calendar
- Modelo `ScheduledPost` — asset_id, scheduled_at, channel, status, caption_override
- Enums: `PostChannel` (instagram, facebook, twitter, linkedin, tiktok, manual), `PostStatus`
- Router `calendar.py` — CRUD completo + publish manual
- Scheduler `scheduler.py` — background task verifica posts a cada 60s e publica
- Frontend: `CalendarPage.tsx` — grid mensal com posts coloridos por status

#### IMP-8: Social Publishing
- Serviço `social_publish_service.py` — publish_to_twitter (Tweepy v2), publish_to_linkedin (API REST)
- Scheduler integrado no startup do app (`start_scheduler()` em `main.py`)
- 6 novas settings: Twitter (4 keys) + LinkedIn (2 keys)

#### IMP-9: Asset Versioning
- Modelo `AssetVersion` — version_number, file_path, file_type, caption, hashtags, comment
- Router `versions.py` — upload new version, list versions, restore previous
- Upload de versão re-roda AI pipeline e reseta status para draft
- Frontend: `VersionHistory.tsx` — timeline com botão de restauração

#### IMP-10: Collaborative Comments
- Modelo `AssetComment` — body, parent_id (replies), is_resolved, user relationship
- Router `comments.py` — CRUD + resolve
- Frontend: `CommentsSection.tsx` — thread com replies aninhadas, contagem de não-resolvidos

### Tier 3 — Enterprise

#### IMP-11: SSO/SAML
- Router `sso.py` — `GET /auth/sso/login`, `POST /auth/sso/callback`, `GET /auth/sso/metadata`
- SP metadata XML gerado dinamicamente
- Framework para integração com Okta, Azure AD, Google Workspace

#### IMP-12: RBAC Granular
- Modelo `Permission` — user_id, resource_type (portal/collection/all), resource_id, permission_level
- Router `permissions.py` — CRUD (admin only)
- Complementa roles globais (admin/editor/viewer) com permissões por recurso

#### IMP-13: CDN/S3 Storage
- `storage.py` já tinha `S3Storage` — agora config via settings (`S3_ENDPOINT_URL`, etc.)
- 7 novas settings: `STORAGE_BACKEND`, `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET`, `S3_REGION`, `S3_PUBLIC_URL`

#### IMP-14: Multi-Region Storage
- Coluna `storage_region` adicionada ao modelo `Tenant` (default: us-east-1)
- Suporte para resolução de bucket/endpoint por região do tenant

#### IMP-15: Rate Limiting por Plano
- `rate_limit.py` reescrito com `PLAN_LIMITS` dict por tier
- Free: 50 AI/mês, 10 uploads/dia, 30 req/min
- Pro: ilimitado AI, 100 uploads/dia, 120 req/min
- Business: ilimitado, 500 uploads/dia, 300 req/min
- Enterprise: tudo ilimitado, 1000 req/min
- `check_upload_rate_limit()` para uploads diários
- HTTP 402 com `upgrade_url` quando limite excedido

### Tier 4 — Innovation

#### IMP-16: AI Content Brief
- Modelo `ContentBrief` — prompt, brief_content (JSONB), suggested_asset_ids, status
- Serviço `brief_service.py` — Claude gera brief com contexto de brand + voice
- Output JSON: campaign_overview, content_pieces, hashtag_strategy, timeline, key_messages
- $1.00/brief (AIActionType.content_brief)
- Frontend: `BriefsPage.tsx` — textarea para prompt + lista expansível de briefs

#### IMP-17: Visual Similarity Search (CLIP)
- Serviço `embedding_service.py` — CLIP ViT-B/32 (512-dim), lazy-loaded singleton
- `generate_embedding()`, `store_embedding()`, `find_similar()` via pgvector
- Endpoint `GET /assets/:id/similar?limit=10`
- Dependências opcionais: open-clip-torch, torch, pgvector

#### IMP-18: Predictive Analytics
- Serviço `prediction_service.py` — agregação de métricas + Claude para insights
- Analisa: approval rate por dia da semana, top hashtags, compliance scores
- Claude gera 5 patterns com insight + action + impact level
- Endpoint `GET /analytics/predictions` — cache 24h em Redis

#### IMP-19: Multi-Language Captions
- `generate_caption_multilang()` adicionado ao `ClaudeAIService`
- Uma chamada Claude gera captions em N idiomas simultaneamente
- Endpoint `POST /ai/caption/:id/translate?languages=pt,es,fr`
- Retorna JSON dict[lang_code, caption]

#### IMP-20: Video Frame Analysis
- Serviço `video_service.py` — OpenCV extrai 5 keyframes
- Multi-image message ao Claude Vision para análise contextual
- Integrado no AI service para gerar captions reais em vez de fallback filename-based

### Migrações
- `c3d4e5f6a7b8_add_fulltext_search.py` — tsvector + GIN + trigger + backfill
- `e5f6a7b8c9d0_add_all_new_tables_and_columns.py` — 6 novas tabelas (asset_variants, asset_versions, asset_comments, content_briefs, scheduled_posts, permissions) + colunas (thumbnail_path, captions_i18n, storage_region)

### Novos Modelos (6)
- `AssetVariant` — variantes redimensionadas
- `AssetVersion` — histórico de versões
- `AssetComment` — comentários com replies
- `ContentBrief` — briefs de campanha gerados pela IA
- `ScheduledPost` — posts agendados no calendário
- `Permission` — permissões granulares por recurso

### Novos Routers (7)
- `calendar.py`, `comments.py`, `briefs.py`, `versions.py`, `resize.py`, `permissions.py`, `sso.py`

### Novos Serviços (8)
- `email_service.py`, `resize_service.py`, `social_publish_service.py`, `video_service.py`, `brief_service.py`, `prediction_service.py`, `embedding_service.py`, `scheduler.py`, `thumbnail_service.py`

### Novos Componentes Frontend (6)
- `AssetThumbnail.tsx`, `CommentsSection.tsx`, `VersionHistory.tsx`, `SelectionToolbar.tsx`
- `CalendarPage.tsx`, `BriefsPage.tsx`

### Novas Dependências
- Backend: `Pillow>=10.2`, `resend>=2.0`, `tweepy>=4.14`, `opencv-python-headless>=4.9`, `aioboto3>=12.0`
- Opcionais: `open-clip-torch`, `torch`, `pgvector`

---

## v0.3.1 — LangSmith AI Observability (2026-03-18)

Integração completa do LangSmith para observabilidade, avaliação e otimização de todas as chamadas AI. Score de maturidade subiu de **8.7/10** para **9.0/10**.

### Tracing de IA (LS-1 a LS-7)
- `langsmith>=0.1.100` adicionado como dependência
- Módulo centralizado `backend/app/core/tracing.py` — `init_tracing()`, `trace_llm_call()`, `send_feedback()`, `cost_metadata()`
- 3 novas settings: `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`, `LANGSMITH_TRACING_ENABLED`
- `init_tracing()` chamado no startup do app via `main.py`
- Todas as 3 chamadas AI instrumentadas com traces detalhados:
  - `generate_caption` — metadata: tenant_id, has_vision, brand_voice_count; tags: caption, vision/text-only, brand-voice, fallback
  - `generate_hashtags` — metadata: json_parse_success, hashtag_count; tags: hashtags, json-output, fallback
  - `check_compliance` — metadata: guidelines_present, threshold, issues_by_severity; tags: compliance, brand-governance, json-parse-failure
- `StubAIService` também instrumentado com tag `stub` para testar tracing em dev
- Parent trace `bluewave.asset_pipeline` (tipo chain) agrupa caption + hashtags no pipeline de upload
- LangSmith é 100% opcional — zero overhead quando `LANGSMITH_API_KEY` não está configurado
- `try/except` em todas as chamadas LangSmith — falha de tracing nunca impacta funcionalidade

### Avaliação e Qualidade (LS-8 a LS-9)
- Script `backend/scripts/create_langsmith_datasets.py` — cria 3 datasets de avaliação (caption, hashtags, compliance)
- Script `backend/scripts/langsmith_evaluators.py` — evaluators rule-based:
  - `caption_format_check` — vazio, >280 chars, hashtags, aspas, fallback, prompt artifacts
  - `hashtags_format_check` — JSON válido, 6-10 tags, prefixo #, duplicatas, fallback
  - `compliance_format_check` — JSON válido, score 0-100, summary, issues structure, score 50 (fallback)
- Prompt de LLM evaluator para avaliação de qualidade de captions (sampling 10%)

### Dashboard de Qualidade AI (LS-10)
- Novo endpoint `GET /analytics/ai-quality` — métricas por tipo de ação (total, avg_tokens, fallback_rate)
- Componente `AIQualityCard.tsx` — card com indicadores verde/amarelo/vermelho para compliance fallback rate

### Prompt Versioning (LS-11)
- Novo módulo `backend/app/services/prompts.py` — prompts centralizados com versão explícita
- Registry com suporte a A/B testing via weighted random selection
- `get_prompt()` e `get_prompt_metadata()` para uso nos serviços AI

### Feedback Loop (LS-12)
- Coluna `langsmith_run_id` (VARCHAR 64) adicionada ao modelo `AIUsageLog`
- Migration `a1b2c3d4e5f6_add_langsmith_run_id_to_ai_usage.py`
- `log_ai_usage()` aceita `langsmith_run_id` opcional
- Aprovação de asset → `send_feedback(score=1.0, key='user_approval')`
- Rejeição de asset → `send_feedback(score=0.0, key='user_approval', comment=rejection_comment)`
- Feedback linkado ao trace original via `langsmith_run_id` na tabela `ai_usage_logs`

### Custo e Cross-Service Tracing (LS-13 a LS-14)
- `calculate_actual_cost_millicents()` e `cost_metadata()` em `tracing.py` — comparação custo estimado vs real
- Pricing Anthropic: claude-sonnet input 0.3 millicents/token, output 1.5 millicents/token
- OpenClaw skill handler envia header `X-Langsmith-Trace` para conectar traces cross-service

### Variáveis de Ambiente
- `LANGSMITH_API_KEY` — API key do LangSmith (vazio = tracing desabilitado)
- `LANGSMITH_PROJECT` — Nome do projeto (default: `bluewave`)
- `LANGSMITH_TRACING_ENABLED` — Master switch (default: `true`)
- `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT` — vars legadas do SDK, configuradas no docker-compose.yml

### Arquivos Criados (6)
- `backend/app/core/tracing.py`
- `backend/app/services/prompts.py`
- `backend/scripts/create_langsmith_datasets.py`
- `backend/scripts/langsmith_evaluators.py`
- `backend/alembic/versions/a1b2c3d4e5f6_add_langsmith_run_id_to_ai_usage.py`
- `frontend/src/components/analytics/AIQualityCard.tsx`

### Arquivos Modificados (12)
- `backend/requirements.txt` — +langsmith
- `backend/app/core/config.py` — +3 settings LangSmith
- `backend/app/main.py` — +init_tracing() no startup
- `backend/app/services/ai_service.py` — tracing em generate_caption, generate_hashtags, StubAIService
- `backend/app/services/compliance_service.py` — tracing em check_compliance
- `backend/app/services/ai_usage.py` — +langsmith_run_id param
- `backend/app/models/ai_usage.py` — +langsmith_run_id column
- `backend/app/routers/assets.py` — parent trace no pipeline
- `backend/app/routers/workflow.py` — feedback on approve/reject
- `backend/app/routers/analytics.py` — +endpoint /ai-quality
- `docker-compose.yml` — +LANGCHAIN_* env vars
- `.env.example` — +LANGSMITH_* vars
- `openclaw-skill/handler.py` — +X-Langsmith-Trace header

---

## v0.3.0 — Production Hardening (2026-03-18)

Release focado em fechar todos os gaps críticos para lançamento beta e preparação Series A. Score de maturidade subiu de **7.2/10** para **8.7/10**.

### Testes (GAP-1)
- ~97 testes backend com pytest + pytest-asyncio + httpx AsyncClient
- Fixtures: 2 tenants, 3 roles (admin/editor/viewer), assets em todos os estados
- Testes de API: auth, assets, workflow, brand, webhooks, api_keys, users, subscriptions
- Testes de serviço: ai_service (stub + mock Claude), compliance, webhook HMAC, automation engine
- **Testes CRÍTICOS de isolamento de tenant:** verificação que tenant A nunca vê dados de tenant B
- Testes de segurança: JWT expirado/inválido, role guards, bcrypt, password strength

### Observabilidade (GAP-2)
- `structlog` com JSON output em produção, console colorido em dev
- Request logging middleware com `X-Request-ID` em todas as responses
- Sentry integration backend (FastAPI + SQLAlchemy) e frontend (React ErrorBoundary)
- Health checks: `/health` (DB latency, AI status, storage), `/health/ready`, `/health/live`
- Logging estruturado nos serviços críticos (AI duration/tokens, webhook delivery, auth login)

### Segurança (GAP-3)
- CORS dinâmico via `CORS_ORIGINS` env var, validação obrigatória em produção
- Secrets sem defaults inseguros: `JWT_SECRET` e `DATABASE_URL` obrigatórios
- Nginx reverse proxy: TLS, HSTS, CSP, X-Frame-Options, gzip, rate limiting (100r/m global, 10r/m auth)
- Rate limiting in-memory no backend: 10r/m auth, 60r/m AI, 30r/m assets, 120r/m geral
- Input validation: whitelist de extensões (.jpg/.png/.gif/.webp/.mp4/.mov/.avi/.mkv), força de senha (8 chars, 1 maiúscula, 1 número)
- Audit logging: tabela `audit_logs` + service `log_action()` + endpoint `GET /audit-logs` (admin, paginado, filtrável)
- `.env.example`, `.env.production.example`, `.env.staging.example`

### Billing (GAP-4)
- `stripe_service.py`: create_customer, checkout, portal, invoices, usage metering
- Endpoints: `POST /billing/checkout`, `/billing/portal`, `GET /billing/invoices`
- Stripe webhooks: checkout.session.completed, subscription.updated/deleted, invoice.payment_failed
- AI usage metering: report_usage() chamado em background após cada log_ai_usage()
- Plan limits enforcement: `check_ai_limit`, `check_storage_limit`, `check_user_limit` → 402
- Frontend: BillingPage com plano atual, usage progress bars, pricing tiers, upgrade, invoice history

### CI/CD (GAP-5)
- GitHub Actions CI: lint (ruff + eslint) + test-backend (PostgreSQL service) + test-frontend (vitest) + Docker build
- GitHub Actions CD: build + push GHCR + deploy staging via SSH + smoke test
- `docker-compose.staging.yml` com resource limits e registry images
- `docker-compose.prod.yml` com nginx TLS + Redis
- PR template com checklist + CODEOWNERS para code review obrigatório
- `entrypoint.sh`: aguarda PostgreSQL + alembic upgrade head + uvicorn

### Performance (GAP-6)
- Redis 7 Alpine adicionado ao stack com healthcheck
- Cache module (`cache.py`): get/set/delete/delete_pattern com fallback gracioso
- Cache helpers (`cached.py`): brand guidelines (5min), billing plan (1min), asset counts (30s)
- Connection pool tuned: pool_size=20, max_overflow=10, pool_pre_ping=True, pool_recycle=3600
- Performance indexes: (tenant_id, status), (tenant_id, created_at DESC), partial index em webhooks ativos
- Asset list query otimizada: window function `COUNT(*) OVER()` elimina segunda query
- Frontend: `React.lazy()` + `Suspense` para todas as páginas, bundle inicial reduzido

### Analytics (GAP-7)
- 5 endpoints: `/analytics/overview`, `/trends`, `/team`, `/ai`, `/roi` — SQL aggregation + Redis cache 5min
- `GET /analytics/report?year=&month=` — gera PDF executivo mensal via ReportLab
- Frontend: AnalyticsPage com período seletor, 4 KPI cards, trend chart, ROI card, AI breakdown, team table
- Componentes: StatCard, TeamTable, ROICard

### Migrações
- `d1e2f3a4b5c6_add_performance_indexes.py` — indexes compostos + partial index + ANALYZE
- `e2f3a4b5c6d7_add_audit_logs.py` — tabela audit_logs + indexes

### Dependências Adicionadas
- Backend: structlog, sentry-sdk[fastapi], redis[hiredis], stripe, reportlab, pytest, pytest-asyncio, pytest-cov, httpx, aiosqlite, factory-boy
- Frontend: @sentry/react (via lib/sentry.ts)

---

## v0.2.0 — 10x Feature Platform (Fases 9–10.5)

- Landing page de marketing completa
- Sistema de webhooks com HMAC-SHA256 signing
- API keys com escopo por tenant
- Claude Vision AI real (captions + hashtags contextuais)
- AI usage tracking para billing metrificado
- Brand guidelines + compliance service
- Motor de automação de workflow
- Portais white-label para clientes
- Inteligência de tendências (X/Twitter)

## v0.1.0 — MVP Core (Fases 1–8)

- Docker Compose (PostgreSQL + FastAPI + React)
- Multi-tenant row-level isolation
- JWT auth com refresh tokens
- CRUD de assets com upload de mídia
- Workflow de aprovação (draft → pending → approved)
- UI/UX premium (Radix UI + Framer Motion + dark mode + ⌘K)
- WCAG 2.1 AA accessibility
