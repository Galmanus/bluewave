# Wave Agent — Sistema Multi-Agente Autônomo

## Fases

| # | Fase | Descrição | Dependências | Prioridade |
|---|------|-----------|--------------|------------|
| 1 | Orchestrator | Wave orquestrador + delegação para especialistas | dev-start | Critica |
| 2 | Specialists | 9 agentes especialistas com prompts dedicados | Fase 1 | Critica |
| 3 | Skills | 80+ tools em 18 módulos (web, social, sales, vision, etc) | Fase 1 | Critica |
| 4 | Intent Router | Classificação de intent + model routing (Haiku/Sonnet) | Fases 1-3 | Alta |
| 5 | Self-Evolution | Agente cria skills em runtime (create_skill) | Fase 3 | Alta |
| 6 | Prompts | System prompts com PUT + Intelligence Theory + Strategic Philosophy | Fase 2 | Alta |
| 7 | Autonomous | Daemon autônomo com 5 estratégias rotativas | Fases 1-6 | Alta |
| 8 | API Server | FastAPI server (port 18790) + proxy via backend | Fase 1 | Critica |
