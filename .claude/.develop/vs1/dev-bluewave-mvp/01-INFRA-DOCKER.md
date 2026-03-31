# Fase 01 — Infraestrutura Docker & Ambiente de Desenvolvimento 🟢

## Objetivo

Configurar o ambiente de desenvolvimento completo via Docker Compose, com todos os serviços necessários para rodar o Bluewave localmente com um único comando.

## Componentes

### Docker Compose (desenvolvimento)
- `docker-compose.yml` — orquestração principal
  - **postgres:16-alpine** — banco de dados com healthcheck
  - **backend** — FastAPI container com `entrypoint.sh` (auto-migration + uvicorn)
  - **redis:7-alpine** — cache layer
  - **frontend** — Vite dev server com hot reload
- `bluewave_network` — bridge network interna (PostgreSQL não exposto ao host)
- Portas: Backend `:8300`, Frontend `:5174`

### Docker Compose (ambientes adicionais)
- `docker-compose.prod.yml` — Nginx reverse proxy + TLS
- `docker-compose.staging.yml` — Imagens GHCR + resource limits
- `docker-compose.openclaw.yml` — Skill server `:18790`

### Dockerfiles
- `backend/Dockerfile` — Python 3.11-slim, pip install, uvicorn
- `frontend/Dockerfile` — Node 20-alpine, npm install, vite dev (dev) / nginx serve (prod)

### Nginx
- `nginx/` — Reverse proxy, TLS termination, rate limiting, security headers (HSTS, CSP, X-Frame-Options), gzip

### Configuração
- `.env.example` — 73 variáveis de ambiente (DB, JWT, AI, LangSmith, Email, Social, Storage, Billing, Observability)
- `.env.production.example`, `.env.staging.example`
- `docker/entrypoint.sh` — aguarda DB + roda migrations automaticamente

## Entregáveis

- [x] `docker compose up` sobe 4 containers saudáveis
- [x] PostgreSQL acessível apenas pela rede interna
- [x] Frontend proxeia `/api/*` para backend
- [x] Hot reload funcional (backend + frontend)
- [x] `.env.example` com todas as variáveis documentadas
- [x] Compose para prod, staging e openclaw

## Critérios de Conclusão

- Todos os containers iniciam sem erro e passam healthcheck
- `curl http://localhost:8300/api/v1/health` retorna 200
- Frontend acessível em `http://localhost:5174`
- Migrations rodam automaticamente no boot do backend
