# Fase 10 — IA Real — Claude API com Vision 🟢

## Objetivo

Substituir os stubs de IA por integração real com a API do Claude (Anthropic), incluindo análise de imagens via vision, tracking de uso e billing por ação.

## Componentes

### AIServiceProtocol (interface)
- `generate_caption(filename, file_type, file_path?)` → str
- `generate_hashtags(filename, file_type, file_path?)` → str
- Interface async para ambas implementações

### ClaudeAIService (implementação real)
- Modelo: `claude-sonnet-4-20250514` com vision
- Imagens (JPEG, PNG, GIF, WebP até 20MB): base64-encoded → Claude Vision para análise visual
- Non-image media: fallback para inferência por filename
- Multi-language: geração de captions em idiomas diferentes
- Video: extração de frames → análise de keyframes

### StubAIService (fallback)
- Implementação determinística para dev/testing
- Usado quando `ANTHROPIC_API_KEY` não está configurado

### Auto-seleção
- Factory function verifica `ANTHROPIC_API_KEY` no startup
- Instancia `ClaudeAIService` ou `StubAIService` automaticamente
- Sem mudança de código para trocar entre real e stub

### Usage Tracking
- Modelo `AIUsageLog` — action type, token counts, custo em millicents, LangSmith run ID
- Toda ação AI logada automaticamente
- Admin endpoint `GET /ai/usage` — sumários de uso para billing

### Pricing por Ação

| Ação | Custo |
|------|-------|
| Caption | $0.05 |
| Hashtags | $0.05 |
| Brand Voice | $0.25 |
| Content Brief | $1.00 |

### Config
- `ANTHROPIC_API_KEY` — chave da API
- `AI_MODEL` — modelo (default: claude-sonnet-4-20250514)

### Migration
- Alembic migration para tabela `ai_usage_logs`
- Migration adicional para coluna `langsmith_run_id`

## Entregáveis

- [x] ClaudeAIService funcional com vision
- [x] StubAIService como fallback
- [x] Auto-seleção por env var
- [x] AIUsageLog com tracking completo
- [x] Endpoint admin de usage
- [x] Pricing table implementada
- [x] Vision para imagens (base64)
- [x] Fallback para filename em non-image

## Critérios de Conclusão

- Upload de imagem → Claude Vision gera caption contextual (não genérica)
- Upload sem API key → stub gera caption determinística
- `GET /ai/usage` retorna sumário correto de ações e custos
- Tokens e custos logados em `ai_usage_logs`
