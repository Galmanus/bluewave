# Fase 4 — Intent Router

## Objetivo
Classificação de intent por heurística + routing para modelo e toolset mínimo.

## Componentes
- intent_router.py: classify_intent() + get_tools_for_intent() + get_prompt_for_intent()
- 15 categorias de intent (chat, brand, assets, workflow, research, sales, moltbook, etc)
- 14 tool clusters para lazy loading
- 3 tiers de prompt (light/medium/full)
- Model routing: Haiku para simple/medium, Sonnet para complex

## Entregáveis
- [x] Classificação heurística zero-token
- [x] "oi" = 0.5k tokens (era 28k) — 56x redução
- [x] "brand DNA" = 1k tokens — 28x redução
- [x] Tempo de resposta: 3.4s (era 15s)

## Critérios de Conclusão
Queries simples custam <1k tokens. Queries complexas usam Sonnet com tools completas.
