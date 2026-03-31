# ADR-03 — Claude API com Vision como Provider de IA

> Status: Aceita
> Data: 2026-03-18

## Contexto

O Bluewave precisa gerar captions, hashtags, verificar compliance visual e analisar trends. A qualidade da IA é diferencial competitivo — precisa entender imagens, não apenas filenames.

## Decisão

Adotamos **Anthropic Claude API** (modelo `claude-sonnet-4-20250514`) com **vision support** como provider principal, atrás de um `AIServiceProtocol` que permite fallback para stubs em dev/testing.

### Implementação
- `AIServiceProtocol` — interface async: `generate_caption()`, `generate_hashtags()`
- `ClaudeAIService` — real: base64 image → Claude Vision → captions contextuais
- `StubAIService` — determinístico: para dev/testing sem API key
- Auto-seleção: factory verifica `ANTHROPIC_API_KEY` no startup
- Usage tracking: `AIUsageLog` com action type, tokens, custo millicents, LangSmith run ID
- Pricing: Caption $0.05, Hashtags $0.05, Brand Voice $0.25, Content Brief $1.00

## Alternativas Consideradas

| Provider | Prós | Contras | Veredicto |
|----------|------|---------|-----------|
| OpenAI GPT-4V | Popular, bom vision | Pricing mais caro, rate limits | Rejeitada |
| Google Gemini | Multimodal nativo | API menos madura | Rejeitada |
| Open source (LLaVA) | Sem custo API | Qualidade inferior, infra pesada | Rejeitada |
| **Claude Vision** | Melhor razão qualidade/preço, vision nativo | Vendor lock (mitigado por Protocol) | **Aceita** |

## Consequências

**Positivas:**
- Vision produz captions 10x mais ricos que filename-only
- Protocol pattern permite trocar provider sem alterar routers
- Stub permite desenvolvimento offline sem API key
- Usage tracking habilita billing por ação
- LangSmith integration nativa para observabilidade

**Negativas:**
- Dependência de API externa (mitigado por stub fallback + retry)
- Custo por chamada (mitigado por rate limiting + billing pass-through)
- Latência de 2-5s por chamada vision (mitigado por background tasks)
