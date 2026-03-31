# Fase 11 — OpenClaw Integration + Webhooks + API Keys 🟢

## Objetivo

Habilitar integrações externas via webhooks com assinatura HMAC, API keys para acesso programático e skill package OpenClaw para automação via agentes.

## Componentes

### Webhooks
- Modelo `Webhook` — name, url, secret, events[], is_active
- `webhook_service.py` — HMAC-SHA256 signing + retry delivery
- `emit_event()` — dispara para webhooks matching em mudanças de estado
- 7 event types: `asset.uploaded`, `asset.submitted`, `asset.approved`, `asset.rejected`, `ai.completed`, `user.invited`, `user.removed`
- Router `webhooks.py` — CRUD + event registration (admin only)

### API Keys
- Modelo `APIKey` — name, key_hash, prefix, created_by, scopes
- Hash comparison (plaintext nunca armazenado)
- `api_key_auth.py` — validação do header `X-API-Key`
- Dual auth em `get_current_user`: JWT Bearer OU X-API-Key
- Router `api_keys.py` — geração + management (admin only)

### Frontend
- `IntegrationsPage.tsx`:
  - API key create/revoke com exibição única da key completa
  - Webhook create/toggle/delete com seleção de eventos

### OpenClaw Skill Package
- `SKILL.md` — definição da skill com frontmatter
- `openclaw-config-example.json5` — template de configuração
- `README.md` — documentação do skill

### Migration
- Alembic migration para tabelas `webhooks` + `api_keys`
- Recriação com timezone-aware columns

## Entregáveis

- [x] Webhook CRUD com HMAC-SHA256 signing
- [x] Eventos disparam automaticamente em mudanças de workflow
- [x] API Key geração + revogação
- [x] Dual auth funcional (JWT + API Key)
- [x] IntegrationsPage com UI completa
- [x] OpenClaw skill package pronto
- [x] Migrations executáveis

## Critérios de Conclusão

- Criar webhook → aprovar asset → webhook recebe POST com HMAC válido
- API key gerada → `curl -H "X-API-Key: ..."` acessa endpoints protegidos
- Revogar API key → requests subsequentes retornam 401
- OpenClaw config example validável
