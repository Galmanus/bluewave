# Fase 6 — Production Fixes

## Objetivo
Corrigir bugs que impediam o funcionamento real em produção.

## Bugs Corrigidos
1. **Timezone mismatch** — `datetime.now(timezone.utc)` vs coluna naive em `rate_limit.py` e `plan_limits.py` → fix: `datetime.utcnow()`
2. **LangSmith 0.7.20 async generator bug** — `RunTree.end()` causava "generator didn't stop after athrow" no Python 3.11 → fix: tracing NoOp no backend Docker
3. **LogRecord conflict** — `extra={"filename": ...}` conflitava com campo reservado → fix: `asset_filename`
4. **Background task pipeline** — `trace_llm_call` wrapper crashava a background task de caption → fix: removido wrapper, AI service tem tracing próprio
5. **Moltbook API key** — não estava no `.env` → adicionada

## Entregáveis
- [x] `backend/app/core/rate_limit.py` — timezone fix
- [x] `backend/app/core/plan_limits.py` — timezone fix
- [x] `backend/app/core/tracing.py` — NoOp bypass
- [x] `backend/app/services/ai_service.py` — LogRecord fix
- [x] `backend/app/routers/assets.py` — background task fix
- [x] `.env` — MOLTBOOK_API_KEY adicionada

## Critérios de Conclusão
- [x] Caption + hashtags gerados automaticamente no upload
- [x] Rate limiting funcional sem crash de timezone
- [x] Wave Autonomous rodando com Moltbook access
