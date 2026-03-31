# Fase 12 — Brand Compliance Engine 🟢

## Objetivo

Implementar sistema de verificação de conformidade de marca usando Claude Vision, com guidelines configuráveis, scoring automático e auditoria de compliance.

## Componentes

### Modelo
- `BrandGuideline` — tenant-scoped: colors[], tone (formal/casual/playful), dos[], don'ts[], logo_url, additional_rules
- Campo `compliance_score` adicionado ao `MediaAsset`
- `AuditLog` — registro de quem fez o quê quando (compliance tracking)

### Compliance Service (`compliance_service.py`)
- Recebe asset + brand guidelines do tenant
- Envia imagem (base64) + guidelines para Claude Vision
- Claude analisa: uso de cores, tom do caption, aderência às regras
- Retorna: score (0-100) + lista de violações + sugestões
- Cache de guidelines em Redis para performance

### Brand Router (`routers/brand.py`)
- `GET /brand/guidelines` — retorna guidelines do tenant
- `POST /brand/guidelines` — cria/atualiza guidelines (admin)
- `PATCH /brand/guidelines` — update parcial (admin)
- `POST /brand/check` — roda compliance check em um asset

### Integração com Workflow
- Compliance check roda antes/durante aprovação
- Score visível no `AssetDetailPage`
- Admin pode rejeitar baseado em baixo compliance score

### Auditoria (`routers/audit.py`)
- `AuditLog` registra: user, action, resource, timestamp, details
- `audit_service.py` — logging centralizado
- Endpoint admin para query de logs

### Frontend
- `BrandPage.tsx` — editor visual de guidelines:
  - Color picker para cores da marca
  - Seletor de tom (formal/casual/playful)
  - Listas editáveis de dos/don'ts
- Compliance score badge no `AssetDetailPage`

## Entregáveis

- [x] BrandGuideline model com CRUD
- [x] Claude Vision compliance checking
- [x] Score 0-100 com violações detalhadas
- [x] Integração com workflow de aprovação
- [x] Audit logging funcional
- [x] BrandPage com editor de guidelines
- [x] Redis cache para guidelines
- [x] Endpoint admin de audit logs

## Critérios de Conclusão

- Criar guidelines → upload asset → compliance check retorna score + violações
- Score visível no detail do asset
- Audit log registra todas as ações de compliance
- Guidelines cacheadas em Redis (não hit DB a cada check)
