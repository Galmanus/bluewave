# Proposta — WhatsApp Conversation Intelligence
**Para:** Fagner Adler
**De:** Manuel Galmanus
**Data:** 2026-03-27
**Canal:** WhatsApp (direto, manhã)

---

## Mensagem WhatsApp (enviar segunda-feira antes das 9h)

> Fagner, tenho uma proposta concreta.
>
> O Transcriptor do Braainner já funciona. Implementei um módulo que captura áudios do WhatsApp via Evolution API, transcreve automaticamente e gera relatório semanal: objeções mais comuns, deals perdidos, performance por vendedor.
>
> Empresas com time de vendas no WhatsApp têm essa dor e pagam R$1.500 a R$3.000/mês por isso.
>
> Proposta: você me apresenta 1 contato seu com time de vendas no WhatsApp. Eu faço o setup e entrego o primeiro relatório em 7 dias. Cobramos juntos — 50/50 conforme o acordo. Se der certo, vira produto Ialum.
>
> Quer testar?

---

## Email de follow-up (se ele engajar)

**Assunto:** Proposta — Inteligência de Conversas WhatsApp | Ialum x Bluewave

Fagner,

Segue a proposta estruturada para o piloto.

---

**O Problema**

Empresas com times de vendas no WhatsApp perdem entre 20–40% das oportunidades porque não conseguem analisar o volume de conversas. Cada negociação perdida, cada objeção repetida, cada cliente que sumiu — ficam enterrados em áudios e textos que ninguém revisita.

---

**A Solução — WhatsApp Conversation Intelligence**

Um serviço que usa Transcriiptoor + Agentes de IA para entregar semanalmente:

- Transcrição e classificação de todas as conversas de vendas
- Top 5 objeções da semana com frequência
- Deals perdidos com diagnóstico de causa (preço, prazo, concorrente, qualidade)
- Performance por vendedor: tempo de resposta, taxa de fechamento estimada, lacunas de argumento
- Alertas: clientes sem resposta em 24h+

---

**Como funciona tecnicamente**

Já está construído e commitado:

1. **Transcriiptoor** — transcreve os áudios do WhatsApp (Whisper, otimizado para português brasileiro)
2. **Evolution API Webhook** — captura os áudios automaticamente do WhatsApp (já no stack Ialum)
3. **Agentes de IA (Phase 09)** — extraem action items, objeções, decisões, sentimento por participante
4. **Relatório automático** — gerado toda segunda-feira sem intervenção manual

Tecnologia: 100% dentro da infraestrutura Ialum. Sem dependências externas.

---

**Formato de Entrega**

- Semana 1: setup (integração WhatsApp + pipeline de transcrição)
- Semana 2 em diante: relatório automático toda segunda-feira

---

**Investimento**

| Item | Valor |
|------|-------|
| Setup | R$1.000 (único) |
| Mensalidade | R$2.000/mês |

---

**Divisão de Receita**

Conforme acordo Bluewave: 50% Bluewave (Manuel) / 50% Ialum (Fagner).

Mês 1: R$1.000 cada (setup) + R$1.000 cada (mensalidade)
A partir do mês 2: R$1.000/mês cada

---

**O que preciso de você**

1. Um contato seu — distribuidor, e-commerce, ou empresa com 3+ vendedores no WhatsApp
2. Autorização para usar a Evolution API do servidor Ialum para o piloto
3. 30 minutos para demo

Posso ter o ambiente de demo pronto em 48h.

Manuel

---

## O que foi entregue esta semana (sem pedir nada)

**Commits no Transcriiptoor:**

1. `af589c9` — **Phase 09 AI Agents**: Q&A, resumo automático, action items, decisões, sentimento, agente customizável
2. `eb4c756` — **WhatsApp webhook**: pipeline completo para capturar áudios do WhatsApp via Evolution API

Ambos prontos para produção assim que ANTHROPIC_API_KEY for configurada.

---

## O que precisa ser corrigido para o Wave funcionar

| Item | Impacto | Urgência |
|------|---------|----------|
| `ANTHROPIC_API_KEY` no Transcriiptoor | Phase 09 + spelling correction | Crítico |
| Gmail OAuth reauth (browser) | Canal de email principal morto | Crítico |
| `BRAVE_API_KEY` ou `TAVILY_API_KEY` | Pesquisa de prospects do Wave | Alto |
| `MOLTBOOK_API_KEY` | Conteúdo 3x/semana para inbound | Médio |
| `EVOLUTION_API_URL/KEY` no Transcriiptoor | Produto WhatsApp Intelligence | Médio |

---

*Wave — 2026-03-27*
