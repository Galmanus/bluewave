# Fase 1 — Backend Core

## Objetivo
Setup FastAPI com autenticação JWT, multi-tenancy row-level, e estrutura de routers.

## Componentes
- FastAPI 0.110 + SQLAlchemy 2.0 async + asyncpg
- JWT HS256 via python-jose + bcrypt via passlib
- 23 routers REST (assets, workflow, AI, brand, analytics, portals, automations, etc)
- TenantMixin para isolamento row-level
- API key authentication alternativa

## Entregáveis
- [x] FastAPI app com 23 routers
- [x] JWT auth + API key auth
- [x] Multi-tenant row-level isolation
- [x] CORS configurável
- [x] Structured logging

## Critérios de Conclusão
Backend responde em todas as rotas, autenticação funciona, tenants isolados.
