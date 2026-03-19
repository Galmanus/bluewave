# Multi-Tenant Telegram — Login por Tenant

## Fases

| # | Fase | Descrição | Dependências | Prioridade |
|---|------|-----------|--------------|------------|
| 1 | /login Command | Autenticação via email no Telegram | dev-telegram | Alta |
| 2 | Session Binding | Vincular chat_id → user_id → tenant_id | Fase 1 | Alta |
| 3 | Tenant Isolation | Wave vê dados apenas do tenant do user | Fase 2 | Critica |
