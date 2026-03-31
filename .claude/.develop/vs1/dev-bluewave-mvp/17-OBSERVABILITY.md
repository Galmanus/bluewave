# Fase 17 — Observabilidade (LangSmith + Sentry + Structlog) 🟢

## Objetivo

Implementar observabilidade completa: tracing de chamadas AI com LangSmith, error tracking com Sentry, logging estruturado com Structlog e versionamento de prompts com A/B testing.

## Componentes

### LangSmith AI Tracing (`core/tracing.py`)
- Parent/child trace relationships para chamadas multi-step
- Cost tracking por trace (tokens × preço)
- Feedback loop: ações do usuário (approve/reject/edit) vinculadas ao trace
- Header `X-Langsmith-Trace` propagado do OpenClaw skill para end-to-end tracing
- Run ID persistido em `ai_usage_logs.langsmith_run_id`

### Prompt Versioning (`services/prompts.py`)
- Prompts centralizados com versionamento
- A/B testing: múltiplas versões ativas com distribuição configurável
- Tracking de qual versão gerou qual resultado
- Métricas de qualidade por versão

### Sentry (`core/sentry.py`)
- Error tracking com context enrichment
- `X-Request-ID` correlation em todos os requests
- Release tracking vinculado ao deploy

### Structlog (`core/logging_config.py`)
- JSON structured logging
- `X-Request-ID` em todo log entry
- Request/response logging via middleware
- Níveis configuráveis por módulo

### Middleware (`core/middleware.py`)
- Gera `X-Request-ID` único por request
- Log de request (method, path, user_id, tenant_id)
- Log de response (status, duration)
- Propagação do request ID para Sentry e Structlog

### Scripts de Avaliação
- `scripts/create_langsmith_datasets.py` — setup de datasets de avaliação
- `scripts/langsmith_evaluators.py` — evaluators rule-based + LLM prompt

### Frontend
- `AIQualityCard.tsx` — card de qualidade AI no analytics dashboard

### Migration
- Alembic migration para `langsmith_run_id` na tabela `ai_usage_logs`

## Entregáveis

- [x] LangSmith traces para todas as chamadas AI
- [x] Parent/child relationships em multi-step
- [x] Feedback loop (user actions → trace)
- [x] Prompt versioning com A/B testing
- [x] Sentry error tracking com request correlation
- [x] Structlog JSON logging
- [x] X-Request-ID propagation completa
- [x] Evaluators (rule-based + LLM)

## Critérios de Conclusão

- Caption generation → trace visível no LangSmith com tokens e custo
- Erro de API → aparece no Sentry com request ID correlacionado
- Logs em JSON com X-Request-ID, user_id, tenant_id
- A/B test de prompts rastreável por versão
