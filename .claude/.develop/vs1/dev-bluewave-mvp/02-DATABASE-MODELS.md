# Fase 02 — Database Models & Alembic Migrations 🟢

## Objetivo

Criar todos os modelos de dados do Bluewave com SQLAlchemy 2.0 async e versionamento de schema via Alembic, incluindo o padrão multi-tenant por row-level isolation.

## Componentes

### Base (`models/base.py`)
- `TenantMixin` — adiciona `tenant_id` UUID FK non-nullable a todos os modelos tenant-scoped
- `TimestampMixin` — `created_at`, `updated_at` automáticos
- `Base` — classe declarativa SQLAlchemy

### 19 Modelos

| Modelo | Tabela | Descrição |
|--------|--------|-----------|
| `Tenant` | `tenants` | Container multi-tenant com storage region |
| `User` | `users` | Usuários com roles (admin/editor/viewer) |
| `MediaAsset` | `media_assets` | Assets com status, caption, hashtags, compliance_score, search_vector |
| `AssetVariant` | `asset_variants` | Variantes redimensionadas (8 formatos sociais) |
| `AssetVersion` | `asset_versions` | Histórico de versões com restore |
| `Comment` | `comments` | Threads de comentários com resolução |
| `APIKey` | `api_keys` | Acesso programático com scoping |
| `Webhook` | `webhooks` | Subscrições de eventos (7 tipos) |
| `BrandGuideline` | `brand_guidelines` | Regras de marca (cores, tom, dos/don'ts) |
| `TenantSubscription` | `subscriptions` | Plano + Stripe integration |
| `AIUsageLog` | `ai_usage_logs` | Metering: action type, tokens, custo, LangSmith run ID |
| `Automation` | `automations` | Triggers, condições, ações, logs |
| `ClientPortal` | `client_portals` | Portais white-label (slug, logo, settings) |
| `PortalCollection` | `portal_collections` | Coleções dentro de portais |
| `PortalCollectionAsset` | `portal_collection_assets` | Assets nas coleções |
| `Permission` | `permissions` | RBAC granular per-resource |
| `TrendEntry` | `trend_entries` | Trends com campos AI (relevance, suggestion, caption draft) |
| `AuditLog` | `audit_logs` | Compliance logging (quem fez o quê quando) |
| `ContentBrief` | `content_briefs` | Briefs gerados por IA |
| `ScheduledPost` | `scheduled_posts` | Agendamento de publicação social |

### Database Config (`core/database.py`)
- Engine async com asyncpg (pool: 20 connections, pre_ping, recycle=3600)
- Session factory async

### Migrations (Alembic)
- 16 migrations versionadas em `alembic/versions/`
- Inclui: tabelas iniciais, webhooks/API keys, brand guidelines, trends, thumbnails, portals, full-text search (tsvector + GIN), subscriptions, performance indexes, variants/versions/comments/briefs, audit logs, scheduled posts, LangSmith run ID

## Entregáveis

- [x] Todos os 19 modelos criados e funcionais
- [x] TenantMixin aplicado consistentemente
- [x] 16 migrations Alembic executáveis em sequência
- [x] Índices compostos `(tenant_id, id)` em tabelas de alto tráfego
- [x] Full-text search com tsvector + GIN index
- [x] Schema visível via psql após migration

## Critérios de Conclusão

- `alembic upgrade head` executa sem erros dentro do container
- Todas as tabelas visíveis com `\dt` no psql
- Foreign keys e constraints validados
- TenantMixin presente em todos os modelos tenant-scoped
