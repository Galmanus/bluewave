# Bluewave — Setup Inicial e Arquitetura

## Fases

| # | Fase | Descrição | Dependências | Prioridade |
|---|------|-----------|--------------|------------|
| 1 | Backend Core | FastAPI + SQLAlchemy + PostgreSQL + JWT auth | — | Critica |
| 2 | Frontend Core | React 18 + TypeScript + Vite + Tailwind | — | Critica |
| 3 | Database | PostgreSQL 16 + Alembic migrations + multi-tenant | Fase 1 | Critica |
| 4 | Docker | Docker Compose (postgres, backend, frontend) | Fases 1-3 | Critica |
| 5 | CI/CD | GitHub Actions workflows | Fase 4 | Media |
