# Fase 8 — API Server

## Objetivo
FastAPI server para Wave com proxy via backend Docker.

## Componentes
- api.py: FastAPI na porta 18790 com endpoints chat, compliance-check, generate-content, brand suite
- wave_proxy.py: proxy no backend Docker (porta 8300) para frontend acessar
- CORS configurado
- Session management

## Entregáveis
- [x] /chat endpoint com streaming
- [x] /compliance-check endpoint direto (bypassa orchestrator)
- [x] /generate-content endpoint
- [x] 8 endpoints de Brand Suite
- [x] Proxy funcional via backend Docker

## Critérios de Conclusão
Frontend e Telegram acessam Wave via API sem problemas.
