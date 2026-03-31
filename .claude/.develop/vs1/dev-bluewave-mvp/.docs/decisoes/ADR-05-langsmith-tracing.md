# ADR-05 — LangSmith para Observabilidade de IA

> Status: Aceita
> Data: 2026-03-18

## Contexto

Com IA real em produção (Claude Vision), precisamos de observabilidade: entender latência, custo, qualidade das respostas, e rastrear problemas end-to-end — do chat no OpenClaw até a chamada Claude.

## Decisão

Adotamos **LangSmith** para AI observability, com tracing, evaluators, feedback loop e prompt versioning.

### Implementação
- `core/tracing.py` — tracing centralizado com parent/child relationships
- `services/prompts.py` — prompt versioning com A/B testing
- Run ID persistido em `ai_usage_logs.langsmith_run_id`
- Header `X-Langsmith-Trace` propagado do OpenClaw skill → Bluewave backend → Claude
- Feedback loop: approve/reject/edit do usuário vinculados ao trace
- Cost tracking: tokens × preço por trace
- Evaluators: rule-based (comprimento, formato) + LLM (qualidade semântica)
- Datasets de avaliação para benchmark de qualidade

## Alternativas Consideradas

| Ferramenta | Prós | Contras | Veredicto |
|------------|------|---------|-----------|
| Custom logging | Controle total, sem custo | Sem UI, sem evaluators, manutenção | Rejeitada — reinventar a roda |
| Weights & Biases | Bom para ML | Focado em training, não inference | Rejeitada — caso de uso diferente |
| Helicone | Simples, bom proxy | Menos features de evaluation | Rejeitada — limitado |
| **LangSmith** | Nativo Anthropic, traces, evaluators, A/B | Vendor-specific | **Aceita** |

## Consequências

**Positivas:**
- End-to-end tracing: OpenClaw chat → skill → API → Claude em uma view
- A/B testing de prompts com métricas de qualidade por versão
- Feedback loop conecta ações do usuário à qualidade do modelo
- Evaluators automatizados para CI/CD de prompts
- Cost tracking granular por trace

**Negativas:**
- Dependência de serviço externo (LangSmith Cloud)
- Custo de LangSmith em alto volume (mitigado por sampling)
- Complexidade de setup inicial (mitigado por scripts de bootstrap)
- Se LangSmith down, tracing falha silenciosamente (graceful degradation implementado)
