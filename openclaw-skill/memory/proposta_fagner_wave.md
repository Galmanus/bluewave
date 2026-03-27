# Proposta — Wave como diferencial comercial Ialum
**Para:** Fagner Adler
**De:** Manuel Galmanus
**Data:** 2026-03-27
**Contexto:** Conversa direta, não é email frio

---

## O que entregamos esta semana (sem pedir nada)

Phase 09 do Transcriiptoor — Agentes de IA — foi implementada e commitada hoje:
- Q&A sobre qualquer transcrição em linguagem natural
- Resumo automático em 3 estilos (executivo, detalhado, bullet points)
- Extração de action items com responsável e prazo
- Extração de decisões tomadas
- Análise de sentimento por participante
- Agente customizável (o usuário define o que extrair)

Isso estava como "Fase 09 — não iniciado" no roadmap. Agora está pronto.
Falta apenas você configurar o ANTHROPIC_API_KEY no .env do servidor.

---

## O problema que estou vendo

Temos um produto real (Wave + Bluewave + Transcriiptoor) e zero receita.

O motivo não é o produto. É o canal.

Ialum tem clientes que pagam todo mês. Esses clientes provavelmente têm:
- Reuniões que ninguém anota direito
- WhatsApp com leads que se perdem
- Conteúdo que leva semanas para produzir
- Atendimento que demora

Qualquer um desses é uma venda de Wave/Transcriiptoor.

---

## O que estou propondo

**Um teste em 1 cliente Ialum.**

Você escolhe qual. De preferência o que tem mais dor em automação ou documentação.

Eu monto a demo. Você faz a apresentação (você já tem o relacionamento).
O cliente paga para Ialum — você mantém a estrutura comercial que já funciona.
Split 50/50 como acordado no Bluewave.

Valor sugerido: R$3.000 a R$10.000 de setup + mensalidade de R$800 a R$2.000.

---

## O que preciso de você

1. **Nome de 1 cliente** que você acha que tem dor em reuniões/documentação/atendimento
2. **15 minutos** para eu te apresentar a demo do que construímos
3. **Confirmação do ANTHROPIC_API_KEY** no servidor do Transcriiptoor

Não precisa de mais nada. O produto está pronto.

---

## Infraestrutura que precisa ser corrigida (urgente)

Para o Wave autônomo funcionar corretamente, preciso que você ou eu adicionemos:

| Item | Impacto |
|------|---------|
| `ANTHROPIC_API_KEY` no .env do Transcriiptoor | Phase 09 funciona + spelling correction |
| `BRAVE_API_KEY` ou `TAVILY_API_KEY` no Wave | Pesquisa de prospects funciona (DDG bloqueado) |
| `MOLTBOOK_API_KEY` | Conteúdo 3x/semana para gerar inbound |
| Gmail OAuth reauth | Canal de email principal está morto (token expirou) |

Sem essas chaves, o agente opera cego. 1072 ciclos rodados, R$0 fechado.

---

## Resultado esperado

Se fecharmos 1 cliente Ialum com Transcriiptoor + Agentes de IA:
- Ialum: R$800-2.000/mês adicional de mensalidade
- Bluewave: R$400-1.000/mês (50%)
- Você tem prova de conceito para replicar em outros clientes
- Eu tenho first revenue e posso escalar

O dinheiro já está no network que você tem. Só precisa ser conectado.

---

*Manuel / Wave — 2026-03-27*
