# Brand DNA from PDF — Extração Automática

## Fases

| # | Fase | Descrição | Dependências | Prioridade |
|---|------|-----------|--------------|------------|
| 1 | PDF Upload | Endpoint para upload de brand guide PDF | dev-brand-guardian | Alta |
| 2 | Extraction | Claude Sonnet extrai DNA estruturado | Fase 1 | Critica |
| 3 | Review + Save | Usuário revisa e salva no banco | Fase 2 | Alta |
