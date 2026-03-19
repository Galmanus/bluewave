# Fase 2 — Especialistas

## Objetivo
9 agentes PhD-level com personalidade, domain knowledge, e toolset filtrado.

## Componentes
| Agente | Domínio | Tools |
|--------|---------|-------|
| Curator | Gestão de assets digitais | 10 |
| Director | Workflow de aprovação | 9 |
| Guardian | Brand compliance | 6 |
| Strategist | Analytics + PUT framework | 6 |
| Creative | Conteúdo + PUT | 10 |
| Admin | Plataforma, equipe, billing | 10 |
| Legal | Compliance, IP, contratos | 5 |
| Security | OWASP, MITRE ATT&CK | 5 |
| Blockchain | Smart contracts, Hedera, Foundry | 9 |

## Entregáveis
- [x] 9 prompts dedicados em /prompts/
- [x] Tool filtering por especialista em agents.json
- [x] Cada especialista roda loop agentico independente
- [x] Specialist runtimes lazy-loaded

## Critérios de Conclusão
Cada especialista responde com domain knowledge e usa apenas seus tools.
