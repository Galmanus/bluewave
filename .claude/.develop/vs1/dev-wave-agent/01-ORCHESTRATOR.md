# Fase 1 — Orchestrator

## Objetivo
Wave como orquestrador central que classifica intenção e delega para especialistas.

## Componentes
- orchestrator.py: classe Orchestrator com chat(), _delegate_to_specialist()
- agent_runtime.py: AgentRuntime para loop agentico de cada agente
- agents.json: configuração de todos os agentes (ID, tools, prompt file)
- DELEGATE_TOOL: tool especial para delegação

## Entregáveis
- [x] Orchestrator funcional com routing por intenção
- [x] Delegação para 9 especialistas
- [x] Fallback Haiku quando Sonnet dá rate limit
- [x] Session management (múltiplas conversas simultâneas)

## Critérios de Conclusão
Mensagem do usuário é roteada para o especialista correto e resposta consolidada retorna.
