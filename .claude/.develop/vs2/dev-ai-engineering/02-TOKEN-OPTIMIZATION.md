# Fase 2 — Token Optimization

## Objetivo
Reduzir consumo de tokens em ~45% por sessão sem perda de qualidade.

## Componentes (7 otimizações)
1. Tool result compression — `token_optimizer.py` (80% redução em listas)
2. Brand voice + guidelines cache — TTL 5min por tenant
3. PUT framework lazy-load — só para sales/philosophy/research intents
4. Tool pruning por intent — orchestrator de 40→7 skill tools
5. Ghost agent removal — enum de 9→6 agentes (legal/security/blockchain removidos)
6. Old tool result summarization — turnos antigos truncados a 400 chars
7. Prompt tiering — 3 níveis (light 30tok, medium 90tok, full 750tok)

## Entregáveis
- [x] `openclaw-skill/token_optimizer.py`
- [x] `openclaw-skill/prompts/put_framework.md`
- [x] Brand voice cache em `ai_service.py`
- [x] Guidelines cache em `compliance_service.py`
- [x] Prompts compactos em `intent_router.py`

## Critérios de Conclusão
- [x] Greeting: 2500→500 tokens (-80%)
- [x] Brand check: 12000→5500 tokens (-54%)
- [x] 5-turn session: 35000→18000 tokens (-49%)
- [x] Documentado em `docs/TOKEN_OPTIMIZATION.md`
