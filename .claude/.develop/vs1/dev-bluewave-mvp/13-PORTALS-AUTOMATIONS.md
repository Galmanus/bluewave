# Fase 13 — White-Label Client Portals & Workflow Automations 🟢

## Objetivo

Permitir que agências criem portais white-label para clientes externos visualizarem assets, e automatizar ações de workflow com triggers configuráveis.

## Componentes

### Client Portals

#### Modelos
- `ClientPortal` — tenant, slug (único), name, logo, settings (JSON), is_active
- `PortalCollection` — portal, name, description
- `PortalCollectionAsset` — collection, asset (many-to-many)

#### Router (`routers/portals.py`)
- `GET /portals` — listar portais do tenant (admin)
- `POST /portals` — criar portal (admin)
- `PATCH /portals/{id}` — atualizar settings (admin)
- `DELETE /portals/{id}` — desativar portal (admin)
- `POST /portals/{id}/collections` — criar coleção
- `POST /portals/{id}/collections/{cid}/assets` — adicionar assets
- `GET /p/{slug}` — **endpoint público** — visualização white-label sem login

#### Experiência do Cliente
- Acessa `app.bluewave.com/p/minha-agencia`
- Vê assets curados em coleções
- Download permitido conforme settings do portal
- Sem sidebar, sem auth — experiência limpa e branded

### Workflow Automations

#### Modelo
- `Automation` — tenant, name, trigger, conditions (JSON), actions (JSON), is_active, execution_count, last_executed_at
- Triggers: `asset_uploaded`, `asset_submitted`, `asset_approved`, `asset_rejected`, `compliance_checked`

#### Engine (`services/automation_engine.py`)
- `evaluate_and_execute(trigger, context)` — busca automações ativas matching
- Avalia condições (ex: `compliance_score > 80`)
- Executa ações (ex: auto-approve, notify, tag)
- Log de execução para auditoria

#### Router (`routers/automations.py`)
- `GET /automations` — listar (admin)
- `POST /automations` — criar (admin)
- `PATCH /automations/{id}` — atualizar (admin)
- `POST /automations/{id}/toggle` — ativar/desativar
- `GET /automations/{id}/logs` — histórico de execuções

### Migration
- Alembic migration para `client_portals`, `portal_collections`, `portal_collection_assets`, `automations`

## Entregáveis

- [x] Portal CRUD com slug único
- [x] Coleções de assets dentro de portais
- [x] Endpoint público `/p/{slug}` sem auth
- [x] Automation model com 5 trigger types
- [x] Engine de execução com avaliação de condições
- [x] Toggle ativar/desativar automações
- [x] Logs de execução queryáveis

## Critérios de Conclusão

- Criar portal → adicionar assets a coleção → acessar `/p/slug` sem login → ver assets
- Criar automação "auto-approve se compliance > 80" → upload asset com score 85 → aprovado automaticamente
- Logs mostram execução da automação com timestamp e resultado
