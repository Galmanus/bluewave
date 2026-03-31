# Fase 3 — Cognitive Architecture

## Objetivo
Maximizar qualidade de raciocínio do agente via prompt engineering estrutural.

## Componentes (5 camadas)
1. Cognitive Scaffold — ORIENT→DECIDE→ACT→VERIFY (`cognitive_protocol.md`)
2. Domain Protocols — Guardian 8-dim, Strategist analytical, Orchestrator routing
3. Verification Gates — 5 checks heurísticos em `_verify_specialist_result()`
4. Error Recovery Hints — `_get_recovery_hint()` com orientação contextual
5. Adversarial Self-Critique — 3 níveis (base, guardian, strategist)

## Entregáveis
- [x] `prompts/cognitive_protocol.md`
- [x] `prompts/cognitive_guardian.md`
- [x] `prompts/cognitive_strategist.md`
- [x] `prompts/cognitive_orchestrator.md`
- [x] `enhance_prompt_with_cognition()` em `agent_runtime.py`
- [x] `_verify_specialist_result()` em `orchestrator.py`
- [x] `_get_recovery_hint()` em `agent_runtime.py`

## Critérios de Conclusão
- [x] ~120 tokens overhead por resposta (invisível ao user)
- [x] Compliance: 8 dimensões obrigatórias
- [x] Self-critique em todos os agentes
- [x] Documentado em `docs/COGNITIVE_ARCHITECTURE.md`
