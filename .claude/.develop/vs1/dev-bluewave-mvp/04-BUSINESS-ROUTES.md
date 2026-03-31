# Fase 04 — Rotas de Negócio (Backend) 🟢

## Objetivo

Implementar todas as rotas REST da API, serviços de negócio e lógica de workflow, incluindo upload de arquivos, processamento AI em background e máquina de estados de aprovação.

## Componentes

### 20 Routers (`routers/`, prefixo `/api/v1`)

| Router | Endpoints principais | Role mínimo |
|--------|---------------------|-------------|
| `auth.py` | register, login, refresh, logout, password-reset, sso-callback | Público/Auth |
| `sso.py` | SAML/SSO integration | Auth |
| `users.py` | GET /me, list, create, update, delete | Admin (exceto /me) |
| `assets.py` | CRUD, upload multipart, download, thumbnail, similarity search | Editor+ (upload) |
| `workflow.py` | submit, approve, reject com compliance check | Editor+/Admin |
| `ai.py` | caption, hashtags, translate (multi-language) | Editor+ |
| `versions.py` | histórico + restore | Any |
| `comments.py` | threads com resolve | Any |
| `resize.py` | resize on-demand, listar variantes, formatos | Editor+ |
| `briefs.py` | content brief CRUD + geração AI | Editor+ |
| `brand.py` | guidelines CRUD + compliance check | Admin (CRUD) |
| `calendar.py` | schedule, list, publish on-demand | Editor+ |
| `webhooks.py` | CRUD + event registration | Admin |
| `api_keys.py` | geração + management | Admin |
| `permissions.py` | RBAC granular per-resource | Admin |
| `portals.py` | portal CRUD + /p/:slug público | Admin |
| `automations.py` | CRUD + toggle + logs | Admin |
| `subscriptions.py` | plano, usage, checkout, portal, invoices, stripe webhooks | Admin |
| `analytics.py` | overview, trends, team, ai_quality, roi, predictions, PDF | Admin |
| `audit.py` | query audit logs | Admin |
| `trends.py` | discover, list, detail, cleanup | Editor+ |
| `health.py` | detailed, ready, live (k8s) | Público |

### 21 Services (`services/`)

| Service | Responsabilidade |
|---------|-----------------|
| `ai_service.py` | ClaudeAIService (vision) + StubAIService (fallback) |
| `ai_usage.py` | Usage tracking + billing metering |
| `audit_service.py` | Audit logging |
| `automation_engine.py` | Execução de automações por trigger |
| `brief_service.py` | Geração de content briefs via Claude |
| `compliance_service.py` | Compliance check via Claude Vision |
| `email_service.py` | Email transacional (Resend) — reset, convite, relatório, notificação |
| `embedding_service.py` | CLIP embeddings para busca visual por similaridade |
| `prediction_service.py` | Analytics preditivo com cache Redis |
| `report_service.py` | Geração PDF (ReportLab) |
| `resize_service.py` | Smart crop + resize para 8 formatos sociais |
| `scheduler.py` | Background scheduling (APScheduler) |
| `social_publish_service.py` | Twitter/X + LinkedIn publishing |
| `storage.py` | Local filesystem ou S3-compatible |
| `stripe_service.py` | Billing: checkout, portal, webhooks, metering |
| `thumbnail_service.py` | WebP 400x400 auto-generation |
| `trend_service.py` | Twitter/X trend intelligence |
| `video_service.py` | Extração de frames + keyframe analysis |
| `webhook_service.py` | HMAC-SHA256 event delivery com retry |
| `prompts.py` | Prompt versioning + A/B testing |
| `retry.py` (core) | Decorator @retry com exponential backoff |

### Schemas (`schemas/`)
- `asset.py` — AssetIn, AssetOut, AssetListResponse (paginação)
- `auth.py` — Register, Login, Token, PasswordReset
- `brand.py` — BrandGuidelineIn/Out
- `user.py` — UserIn, UserOut, UserListResponse

### Workflow — Máquina de Estados
```
DRAFT → (submit) → PENDING_APPROVAL → (approve) → APPROVED
                  ↙ (reject + comentário)
              DRAFT
```

### Upload Flow
```
Upload file → validate MIME/size → save to disk → INSERT media_assets (draft)
           → background task: generate_caption + generate_hashtags (com @retry)
           → return 202 { asset_id, status: "processing" }
```

## Entregáveis

- [x] 20 routers registrados no FastAPI app
- [x] 21 services funcionais
- [x] Upload com validação MIME + size limit (50MB)
- [x] AI background tasks com retry exponencial
- [x] Workflow state machine com validação de transição
- [x] Full-text search (tsvector + GIN)
- [x] Paginação em listagens
- [x] Tenant-scoped em todas as queries

## Critérios de Conclusão

- Upload → AI preenche metadata → submit → approve: ciclo completo via curl
- Paginação funcional com filtros de status
- Tenant isolation verificado em todos os endpoints
- OpenAPI docs acessíveis em `/docs`
