# Bluewave — AI Creative Operations Agent

> O agente de IA que enxerga sua mídia, escreve seu copy, reforça sua marca e distribui seu conteúdo — no piloto automático.

Uma plataforma de operações criativas AI-native para agências de marketing, equipes audiovisuais e produtoras. Combina DAM + geração de conteúdo com IA (Claude Vision) + compliance de marca + workflows de aprovação + calendário de conteúdo + publicação social + integrações via webhook em um único agente que aprende sua marca ao longo do tempo.

## Stack Tecnológica

| Camada | Tecnologia |
|--------|------------|
| Backend | Python 3.11 + FastAPI 0.110 + SQLAlchemy 2.0 (async) + Alembic |
| Frontend | React 18 + TypeScript 5.5 + Vite 5.4 + Tailwind CSS 3.4 + React Query |
| IA | Anthropic Claude API (claude-sonnet-4-20250514) com Vision + multi-language |
| Banco de Dados | PostgreSQL 16 (multi-tenant por linha + tsvector full-text search + pgvector) |
| Cache | Redis 7 (hiredis) |
| Observabilidade | Structlog (JSON) + Sentry + Request Tracing + LangSmith (AI traces) |
| Billing | Stripe (Checkout, Portal, Webhooks, Metering) |
| Storage | Local filesystem (Docker volume) / S3-compatible (AWS, Cloudflare R2, MinIO) |
| Social | Twitter/X API v2 + LinkedIn API (+ Buffer proxy para Instagram) |
| Email | Resend (transactional emails) |
| CI/CD | GitHub Actions (lint + test + build + deploy) |
| Infraestrutura | Docker Compose (dev/staging/prod) + Nginx (TLS + rate limiting) |

## Início Rápido

```bash
# 1. Clone e entre no projeto
cd bluewave

# 2. Copie as variáveis de ambiente
cp .env.example .env

# 3. Adicione sua chave API da Anthropic (opcional — usa stubs sem ela)
# Edite .env → ANTHROPIC_API_KEY=sk-ant-...

# 4. (Opcional) Configure integrações
# LangSmith: LANGSMITH_API_KEY=lsv2_...
# Email: RESEND_API_KEY=re_...
# Social: TWITTER_API_KEY=..., LINKEDIN_CLIENT_ID=...
# CDN: STORAGE_BACKEND=s3, S3_ENDPOINT_URL=..., S3_ACCESS_KEY_ID=...

# 5. Inicie tudo (migrations são executadas automaticamente via entrypoint.sh)
docker compose up -d --build
```

O app estará disponível em:
- **Landing Page:** http://localhost:5174
- **Dashboard:** http://localhost:5174/assets (após login)
- **API do Backend:** http://localhost:8300
- **Docs da API (Swagger):** http://localhost:8300/docs

## Funcionalidades

### Plataforma Core
- **SaaS Multi-tenant** — Isolamento por linha, cada tenant vê apenas seus dados
- **Controle de acesso por roles** — Admin, Editor, Viewer + RBAC granular por recurso
- **Gestão de assets** — Upload, organização, busca full-text (tsvector), thumbnails automáticos
- **Workflow de aprovação** — Draft → Pending Approval → Approved com comentários de rejeição
- **Asset versioning** — Upload de novas versões com histórico e possibilidade de restaurar
- **Comentários colaborativos** — Threads de discussão por asset com respostas e resolução
- **Export em bulk** — Seleção múltipla + download ZIP com arquivos + metadata CSV

### Agente de IA (Claude Vision)
- **Captions inteligentes** — Claude Vision analisa imagens enviadas e escreve captions contextuais
- **Auto-hashtags** — IA gera hashtags relevantes baseadas no conteúdo real da imagem
- **Captions multi-idioma** — Geração simultânea em até 50+ idiomas via Claude
- **AI Content Briefs** — Briefs criativos completos gerados pela IA ($1.00/brief)
- **Análise de vídeo** — Extração de keyframes + análise multi-frame com Claude Vision
- **Auto-resize inteligente** — 8 formatos sociais (Instagram, Facebook, Twitter, LinkedIn, YouTube, Pinterest, TikTok) com smart crop
- **Modo fallback** — Stubs determinísticos quando nenhuma chave API está configurada
- **Rastreamento de uso** — Cada ação de IA logada para billing metrificado ($0.05/ação)
- **Observabilidade LangSmith** — Traces completos de cada chamada AI (prompts, respostas, tokens, latência, custos)
- **Prompt versioning** — Prompts centralizados com versionamento e suporte a A/B testing
- **Evaluators automáticos** — Validação rule-based de formato (captions, hashtags, compliance JSON)
- **Feedback loop** — Aprovação/rejeição de assets alimenta LangSmith como sinal de qualidade

### Gestão de Marca
- **Brand guidelines** — Upload e gestão de regras de marca (cores, tom, dos/don'ts)
- **Verificação de compliance** — IA pontua assets contra brand guidelines antes da aprovação
- **Aprendizado de brand voice** — Agente melhora ao longo do tempo a partir de padrões de conteúdo aprovado

### Content Calendar & Social Publishing
- **Calendário mensal** — Visualização de calendário com posts agendados por dia
- **Agendamento** — Arraste assets aprovados para datas futuras (Instagram, Facebook, Twitter, LinkedIn, TikTok)
- **Publicação automática** — Scheduler background publica posts quando o horário chega
- **Publicação manual** — One-click publish para canais conectados
- **Social publishing** — Publicação direta no Twitter/X e LinkedIn (Instagram via Buffer)

### Integrações & API
- **Webhooks** — Notificações de eventos em tempo real (asset.uploaded, asset.approved, etc.)
- **API keys** — Acesso programático com chaves API com escopo definido
- **Inteligência de tendências** — Acompanhe tendências da indústria e redes sociais
- **SSO/SAML** — Endpoints para integração com Okta, Azure AD, Google Workspace (enterprise)

### Automação
- **Automação de workflow** — Automações baseadas em gatilhos (ex: auto-submit de assets em compliance)
- **Portais de clientes** — Portais white-label para clientes de agências

### Billing & Subscriptions
- **Integração Stripe** — Checkout, Customer Portal, webhooks de pagamento, invoices
- **Tiers de plano** — Free / Pro / Business / Enterprise com limites enforced (402 quando excedido)
- **Rate limiting por plano** — AI actions/mês, uploads/dia, API requests/min diferenciados por tier
- **Metering de IA** — Uso de AI reportado ao Stripe para billing automático baseado em consumo
- **Página de billing** — Plano atual, uso (AI/storage/users), upgrade, histórico de faturas

### Analytics & Relatórios
- **Dashboard de analytics** — KPIs, tendências semanais, produtividade por membro, uso de IA, ROI estimado
- **Relatório executivo mensal** — PDF auto-gerado com KPIs, tabelas, ROI, atividade da equipe
- **Cálculo de ROI** — Economia estimada baseada em benchmarks da indústria ($45/hora, 15min manual vs 30s IA)
- **Qualidade de IA** — Endpoint `/analytics/ai-quality` com métricas de fallback rate, tokens médios e taxa de parse success
- **Predictive analytics** — Padrões de conteúdo + recomendações geradas por IA (cache diário)

### Busca Avançada
- **Full-text search** — PostgreSQL tsvector com pesos (caption > hashtags > filename) + GIN index
- **Busca visual** — Similaridade por embeddings CLIP (pgvector) — encontre fotos parecidas

### Storage
- **Local filesystem** — Docker volume (default para dev)
- **S3-compatible** — AWS S3, Cloudflare R2, MinIO, DigitalOcean Spaces
- **Multi-region** — Storage por região do tenant (us-east-1, eu-west-1, etc.) para compliance GDPR
- **Thumbnails automáticos** — WebP 400x400 gerados em background após upload

### Email Transacional
- **Password reset** — Email com link de reset (via Resend)
- **Convite de usuários** — Email com credenciais temporárias
- **Notificações de workflow** — Asset submetido/aprovado/rejeitado
- **Relatório mensal** — PDF anexado com KPIs principais
- **Graceful degradation** — Se Resend não configurado, log no console (dev mode)

### Observabilidade
- **Logging estruturado JSON** — Structlog com request_id por request, contexto de tenant/user
- **Error tracking** — Sentry no backend (FastAPI + SQLAlchemy) e frontend (React ErrorBoundary)
- **Health checks** — `/health` (detalhado), `/health/ready` (DB), `/health/live` (k8s probes)
- **Request tracing** — Header `X-Request-ID` em todas as responses
- **LangSmith AI tracing** — Traces detalhados de cada chamada LLM com parent traces, evaluators, feedback loop, prompt versioning

### Segurança
- **CORS dinâmico** — Configurável via env var, validação obrigatória em produção
- **Secrets seguros** — JWT_SECRET obrigatório sem default inseguro, validação no startup
- **Rate limiting** — Por IP (nginx) + por rota (middleware) + por plano (AI actions)
- **RBAC granular** — Permissões por recurso (portal, collection) além de roles globais
- **Input validation** — Whitelist de extensões, validação de MIME, força de senha, headers de segurança
- **Audit logging** — Tabela de audit_logs com endpoint admin paginado e filtrável
- **Nginx reverse proxy** — TLS, HSTS, CSP, X-Frame-Options, gzip, rate limiting
- **SSO/SAML** — Framework para SSO enterprise (Okta, Azure AD)

### CI/CD
- **GitHub Actions CI** — Lint (ruff + eslint) + testes backend (pytest + PostgreSQL) + testes frontend (vitest) + Docker build
- **GitHub Actions CD** — Build + push GHCR + deploy staging via SSH + smoke test
- **Staging environment** — Docker Compose com imagens do registry, resource limits, nginx, Redis
- **Branch protection** — PR template com checklist, CODEOWNERS para code review obrigatório

### Performance
- **Redis caching** — Cache de guidelines (5min), billing (1min), asset counts (30s), predictions (24h)
- **Connection pool** — asyncpg pool_size=20, max_overflow=10, pool_pre_ping, pool_recycle=3600
- **Indexes otimizados** — Compostos em (tenant_id, status), GIN para tsvector, IVFFlat para pgvector
- **Otimização de queries** — Window function COUNT(*) OVER() elimina segunda query na listagem de assets
- **Frontend code splitting** — React.lazy() + Suspense para todas as páginas (bundle inicial reduzido)

### Testes
- **~97 testes backend** — pytest + pytest-asyncio + httpx AsyncClient + SQLite in-memory
- **Compatibilidade SQLite** — Custom type compilers para UUID, JSONB, ARRAY em SQLite
- **Cobertura** — API tests (auth, assets, workflow, brand, webhooks, api_keys, users, subscriptions)
- **Segurança** — JWT expirado/inválido, role guards, bcrypt, tenant isolation
- **Isolamento de tenant** — Testes CRÍTICOS verificando que tenant A nunca vê dados de tenant B

### Frontend
- **UI/UX premium** — Design tier Linear/Vercel/Notion com Radix UI + Framer Motion
- **Modo escuro** — Tema claro/escuro completo com detecção de preferência do sistema
- **Command palette** — Navegação rápida via ⌘K
- **Acessibilidade** — Compatível com WCAG 2.1 AA, navegação por teclado, suporte a leitores de tela
- **Landing page** — Site de marketing completo com preços, features, FAQ, social proof
- **Calendário de conteúdo** — Visualização mensal com posts agendados e status coloridos
- **Content briefs** — Interface para criar e visualizar briefs de campanha gerados pela IA
- **Comentários** — Thread de comentários com respostas e resolução em cada asset
- **Seleção em massa** — Toolbar flutuante para export ZIP e ações em lote
- **Thumbnails reais** — Preview de imagens na listagem com fallback para ícone
- **Histórico de versões** — Timeline de versões com botão de restauração

## Arquitetura

### Estratégia Multi-Tenant
Isolamento por linha usando coluna `tenant_id` UUID em todas as tabelas com escopo de tenant. Um evento de sessão do SQLAlchemy injeta automaticamente `WHERE tenant_id = :tid` em cada query.

### Autenticação
Baseada em JWT (HS256). Access tokens (30 min) no header Authorization, refresh tokens (7 dias) em cookies httpOnly.

**Payload do JWT:** `{ sub: user_id, tenant_id, role, exp, type }`

**Roles:** `admin` | `editor` | `viewer` + permissões granulares por recurso

### Arquitetura do Serviço de IA
Design baseado em Protocol permite trocar implementações de IA sem alterar rotas:
- `ClaudeAIService` — API real da Anthropic Claude com vision, multi-language, video analysis
- `StubAIService` — Fallback determinístico para desenvolvimento/testes

Todos os métodos de IA são async. Cada ação é logada em `ai_usage_logs` para billing.

**Observabilidade AI (LangSmith):** Cada chamada LLM é instrumentada com `trace_llm_call()` do módulo `core/tracing.py`. Traces capturam: prompt completo, resposta, tokens (input + output), latência, modelo usado, metadata customizado (tenant_id, asset_id, has_vision, brand_voice_count), e tags por tipo de ação. O pipeline de upload gera um parent trace (`bluewave.asset_pipeline`) com children traces para caption e hashtags. Aprovações/rejeições enviam feedback ao LangSmith linkado ao trace original. Tudo é opcional — se `LANGSMITH_API_KEY` não está configurado, zero overhead.

### Workflow de Aprovação

```
         submit()            approve()
DRAFT  ──────────►  PENDING  ──────────►  APPROVED
       ◄──────────  APPROVAL
         reject()
```

### Pipeline de Upload
```
Upload → Thumbnail generation → AI caption → AI hashtags → Compliance check (se guidelines)
         (background)          (background)  (background)   (background)
                               ↓              ↓              ↓
                         LangSmith trace  LangSmith trace  LangSmith trace
                               └──────── Parent trace (bluewave.asset_pipeline) ────────┘
```

## Endpoints da API

Todas as rotas com prefixo `/api/v1`.

| Grupo | Endpoints |
|-------|-----------|
| Auth | `POST /auth/register`, `/login`, `/refresh`, `/logout`, `/reset-password-request`, `/reset-password` |
| SSO | `GET /auth/sso/login`, `POST /auth/sso/callback`, `GET /auth/sso/metadata` |
| Users | `GET /users/me`, `GET /users`, `POST /users`, `PATCH /users/:id`, `DELETE /users/:id` |
| Assets | `GET /assets`, `GET /assets/counts`, `GET /assets/:id`, `GET /assets/:id/file`, `GET /assets/:id/thumbnail`, `POST /assets`, `PATCH /assets/:id`, `DELETE /assets/:id`, `POST /assets/export`, `GET /assets/:id/similar` |
| Versions | `GET /assets/:id/versions`, `POST /assets/:id/versions`, `POST /assets/:id/versions/:vid/restore` |
| Comments | `GET /assets/:id/comments`, `POST /assets/:id/comments`, `PATCH /assets/:id/comments/:cid`, `DELETE /assets/:id/comments/:cid`, `POST /assets/:id/comments/:cid/resolve` |
| Resize | `POST /assets/:id/resize`, `GET /assets/:id/variants`, `GET /assets/:id/variants/:fmt/file`, `GET /assets/:id/formats` |
| Workflow | `POST /assets/:id/submit`, `/approve`, `/reject` |
| IA | `POST /ai/caption/:id`, `/ai/hashtags/:id`, `POST /ai/caption/:id/translate`, `GET /ai/usage` |
| Briefs | `GET /briefs`, `GET /briefs/:id`, `POST /briefs` |
| Brand | `GET /brand/guidelines`, `PUT /brand/guidelines`, `POST /brand/check/:id` |
| Calendar | `GET /calendar`, `POST /calendar`, `PATCH /calendar/:id`, `DELETE /calendar/:id`, `POST /calendar/:id/publish` |
| Webhooks | `GET /webhooks`, `POST /webhooks`, `PATCH /webhooks/:id`, `DELETE /webhooks/:id` |
| API Keys | `GET /api-keys`, `POST /api-keys`, `DELETE /api-keys/:id` |
| Permissions | `GET /permissions`, `POST /permissions`, `DELETE /permissions/:id` |
| Portals | `GET /portals`, `POST /portals`, `PATCH /portals/:id`, `DELETE /portals/:id`, `GET /p/:slug` (público) |
| Automations | `GET /automations`, `POST /automations`, `PATCH /automations/:id`, `DELETE /automations/:id`, `POST /automations/:id/toggle` |
| Billing | `GET /billing/plan`, `/billing/usage`, `POST /billing/checkout`, `/billing/portal`, `GET /billing/invoices`, `POST /billing/webhooks/stripe` |
| Analytics | `GET /analytics/overview`, `/trends`, `/team`, `/ai`, `/roi`, `/ai-quality`, `/predictions`, `/report` |
| Audit | `GET /audit-logs` |
| Health | `GET /health`, `/health/ready`, `/health/live` |
| Trends | `GET /trends`, `POST /trends/discover` |

## Estrutura do Projeto

```
bluewave/
├── docker-compose.yml          # Dev environment (postgres, backend, frontend, redis)
├── docker-compose.prod.yml     # Production (+ nginx TLS)
├── docker-compose.staging.yml  # Staging (registry images, resource limits)
├── .env / .env.example / .env.production.example / .env.staging.example
├── workflow.json               # Fonte de verdade — arquitetura, fases, progresso
├── nginx/
│   ├── nginx.conf              # Reverse proxy + TLS + rate limiting + security headers
│   └── Dockerfile
├── .github/
│   ├── workflows/ci.yml        # CI: lint + test-backend + test-frontend + docker build
│   ├── workflows/deploy.yml    # CD: build + push GHCR + deploy staging + smoke test
│   ├── pull_request_template.md
│   └── CODEOWNERS
├── docs/
│   ├── CHANGELOG.md            # Histórico de releases
│   ├── production_hardening_status.md
│   ├── 10x_strategy.md         # Estratégia de receita & 5 movimentos de alto impacto
│   ├── market_research.md
│   ├── ux_ui_design_brief.md
│   └── whitepaper.md           # Whitepaper técnico do produto
├── backend/
│   ├── Dockerfile              # Multi-stage com entrypoint.sh (auto-migration)
│   ├── entrypoint.sh           # Aguarda PostgreSQL + alembic upgrade head + uvicorn
│   ├── requirements.txt        # 35+ deps (fastapi, langsmith, pillow, tweepy, resend...)
│   ├── pytest.ini              # asyncio_mode=auto, --cov=app
│   ├── alembic/                # 13 migrations (initial → LangSmith → fulltext → variants/versions/comments/briefs/calendar/permissions)
│   ├── tests/                  # ~97 testes (auth, assets, workflow, brand, webhooks, security, tenant isolation...)
│   ├── scripts/                # LangSmith datasets + evaluators
│   └── app/
│       ├── main.py             # FastAPI + middleware stack + 20 routers + scheduler startup
│       ├── core/
│       │   ├── config.py       # Pydantic settings (30+ vars: DB, JWT, AI, LangSmith, Resend, Twitter, LinkedIn, S3, Stripe, Sentry, Redis)
│       │   ├── database.py     # asyncpg pool tuned (20 connections, pre_ping, recycle)
│       │   ├── security.py     # JWT + bcrypt
│       │   ├── deps.py         # Auth dependencies (JWT + API Key)
│       │   ├── tenant.py       # Row-level tenant isolation via ContextVar
│       │   ├── rate_limit.py   # AI rate limiting por plano (free: 50/month, pro: unlimited)
│       │   ├── tracing.py      # LangSmith AI tracing (init, trace_llm_call, feedback, cost)
│       │   ├── cache.py        # Redis async client
│       │   └── ...             # middleware, sentry, logging, retry, plan_limits
│       ├── models/             # 19 modelos (tenant, user, asset, ai_usage, webhook, api_key, brand, portal, automation, subscription, trend, audit_log, asset_variant, asset_version, comment, content_brief, scheduled_post, permission)
│       ├── schemas/            # Pydantic request/response
│       ├── routers/            # 20 routers (auth, sso, users, assets, versions, comments, resize, workflow, ai, briefs, brand, calendar, webhooks, api_keys, permissions, portals, automations, subscriptions, audit, analytics)
│       └── services/           # AI, compliance, webhooks, automations, ai_usage, stripe, reports, storage, email, resize, video, brief, prediction, scheduler, embedding, social_publish, prompts, thumbnail
└── frontend/
    ├── Dockerfile
    ├── package.json
    └── src/
        ├── App.tsx             # Lazy-loaded routes + Suspense (15+ pages)
        ├── main.tsx            # Entry point + Sentry init
        ├── lib/
        │   ├── api.ts          # Axios com JWT interceptor + retry + refresh
        │   └── sentry.ts
        ├── contexts/           # AuthContext, ThemeContext
        ├── hooks/              # React Query hooks (assets, users, brand, integrations, trends, calendar, comments, briefs, versions)
        ├── components/
        │   ├── ui/             # Design system
        │   ├── landing/        # Landing page sections
        │   ├── analytics/      # StatCard, TeamTable, ROICard, AIQualityCard
        │   ├── AssetThumbnail.tsx
        │   ├── CommentsSection.tsx
        │   ├── VersionHistory.tsx
        │   └── SelectionToolbar.tsx
        └── pages/              # 15+ pages (Login, Register, Landing, Assets, Upload, Team, Brand, Integrations, Trends, Billing, Analytics, Calendar, Briefs)
```

## Modelo de Preços

```
Free:       $0    (3 usuários, 5GB, 50 ações de IA/mês, 10 uploads/dia)
Pro:        $29/usuário/mês  (IA ilimitada, workflows, compliance, 100GB, 100 uploads/dia)
Business:   $49/usuário/mês  (+ portais de clientes, distribuição, automação, 500GB, 500 uploads/dia)
Enterprise: $149/usuário/mês (+ Brand Voice, SSO, API, SLA, uploads ilimitados, multi-region)

Uso de IA (add-on):
  $0.05  por ação de IA (caption, tag, compliance check, resize)
  $0.25  por geração de Brand Voice
  $1.00  por AI content brief
```

## Desenvolvimento

```bash
# Ver logs
docker compose logs -f

# Rodar testes backend
docker compose exec backend python -m pytest --cov=app -v

# Executar uma migration após mudanças nos models
docker compose exec backend alembic revision --autogenerate -m "description"
docker compose exec backend alembic upgrade head

# Acessar o banco de dados
docker compose exec postgres psql -U bluewave -d bluewave

# Verificação de tipos TypeScript
docker compose exec frontend npx tsc --noEmit

# Deploy para staging
docker compose -f docker-compose.staging.yml pull && docker compose -f docker-compose.staging.yml up -d

# Deploy para produção
docker compose -f docker-compose.prod.yml up -d
```

## Roadmap

Veja [docs/10x_strategy.md](docs/10x_strategy.md) para a estratégia completa de receita e [workflow.json](workflow.json) para acompanhamento detalhado de fases.

| Fase | Feature | Status |
|------|---------|--------|
| 1–8 | MVP Core (DAM + Auth + Workflows + UI/UX) | **Concluído** |
| 9 | Landing Page + Webhooks + API Keys | **Concluído** |
| 10 | Integração Real de IA (Claude Vision + Rastreamento de Uso) | **Concluído** |
| 10.5 | Inteligência de Tendências + Brand Guidelines + Compliance | **Concluído** |
| 11 | Hardening de Produção (Testes, Segurança, Observabilidade, CI/CD, Performance) | **Concluído** |
| 12 | Integração Stripe (Checkout, Portal, Webhooks, Metering, Limites por Tier) | **Concluído** |
| 13 | Analytics & Dashboard de ROI + Relatório Executivo PDF | **Concluído** |
| 13.5 | Observabilidade AI com LangSmith (Tracing, Evaluators, Feedback Loop, Prompt Versioning) | **Concluído** |
| 14 | 20 Melhorias: Email, Thumbnails, Full-text Search, Bulk Export, Auto-resize | **Concluído** |
| 14.1 | Content Calendar + Social Publishing + Comments + Versioning | **Concluído** |
| 14.2 | SSO/SAML + RBAC Granular + CDN/S3 + Multi-region Storage | **Concluído** |
| 14.3 | AI Content Briefs + Multi-language + Video Analysis + Rate Limits por Plano | **Concluído** |
| 14.4 | Visual Similarity Search (CLIP) + Predictive Analytics | **Concluído** |
| 15 | Builder de Automação de Workflow (UI avançada) | Planejado |
| 16 | Treinamento de Brand Voice com IA (fine-tuning) | Planejado |
| 17 | Mobile App (React Native) | Planejado |

### Score de Maturidade: 9.5/10 (era 9.0)

| Dimensão | v0.3.1 | v0.4.0 |
|----------|--------|--------|
| Funcionalidades | 80% | **95%** (20 melhorias implementadas) |
| Testes | ~97 testes | ~97 testes + test suite fix (SQLite compat) |
| Observabilidade | Structlog + Sentry + LangSmith | + predictions analytics |
| Segurança | CORS + secrets + rate limiting | + SSO/SAML + RBAC granular + plan-based rate limits |
| Billing | Stripe integrado | + rate limiting diferenciado por plano |
| Busca | ILIKE básico | **Full-text search tsvector + visual similarity CLIP** |
| Storage | Local only | **S3-compatible + multi-region + thumbnails + auto-resize** |
| Social | Zero | **Calendar + scheduling + auto-publish (Twitter, LinkedIn)** |
| Email | Zero | **Resend (password reset, convites, notificações, relatórios)** |
| AI | Caption + hashtags + compliance | **+ multi-language + video analysis + content briefs + predictions** |
| Frontend | 13 pages | **15+ pages + comments + versioning + calendar + briefs + selection toolbar** |
