# Bluewave — Context Prompt

Cole isso no início de uma nova conversa para restaurar o contexto completo.

---

## Quem sou eu

Manuel Galmanus (GitHub: Galmanus, email: m.galmanus@gmail.com). Criador do Bluewave e do Wave. Desempregado atualmente, negociando cargo de AI Engineer / sócio técnico na Ialum (empresa do Fagner Adler que está adquirindo 500GB de GPUs e tem acesso a fundos de investimento).

## O que é o Bluewave

Plataforma SaaS de creative operations com agente autônomo de IA. Repositório: github.com/Galmanus/bluewave. Servidor: 31.97.167.158.

**Stack:** FastAPI + PostgreSQL + React/TypeScript + Vite + Tailwind + Docker Compose.

**Dois produtos live:**
1. **Brand Guardian** — upload imagem, analisa compliance contra Brand DNA em 8 dimensões (cores com Delta-E, tipografia, logo, tom, composição, fotografia, estratégia, canal). Score 0-100. Arquivo: `openclaw-skill/brand_vision.py`.
2. **Brand Content Generator** — gera captions, stories, headlines, ad copy, email sequences, hashtags on-brand em 7 canais. 10 features no Brand Suite. Arquivo: `openclaw-skill/brand_content.py` e `brand_suite.py`.

## O que é o Wave

Agente autônomo que opera o Bluewave. Código em `/home/manuel/bluewave/openclaw-skill/`.

- **Orquestrador** (orchestrator.py) coordena 9 especialistas: Curator, Director, Guardian, Strategist, Creative, Admin, Legal, Security, Blockchain
- **80+ tools** em 18 módulos (skills/)
- **Intent Router** (intent_router.py) classifica intent e roteia para Haiku (simples) ou Sonnet (complexo), com lazy tool loading. Redução de 56x em tokens.
- **System prompt** em `prompts/orchestrator.json` (561 linhas, 31K chars) com 3 frameworks: PUT + Intelligence Theory + Strategic Philosophy
- **Auto-evolução**: cria skills Python em runtime (skills/self_evolve.py)
- **Memória persistente**: salva learnings, strategies, agent intel entre sessões

## Canais

| Canal | Identidade | Config |
|---|---|---|
| **Telegram** @bluewave_wave_bot | Wave (personalidade completa) | telegram_bridge.py, token: 8555774668:AAFvgQNB0FAYwCuZYqr6tFrALb8lLjfBCPw |
| **Web** /wave | Brand Guardian (só compliance) | Frontend → backend proxy → Wave API |
| **Moltbook** @bluewaveprime | Wave estrategista | API key: moltbook_sk_GtQPYL9hnkyxjWGZpH3FNDqUX-jrsLHh |
| **API** localhost:18790 | Todos endpoints | api.py |

## Portas

- Frontend: 5174 (Docker, Vite dev)
- Backend: 8300 (Docker, FastAPI)
- Wave API: 18790 (host, FastAPI)
- PostgreSQL: 5432 (Docker, interno)

## API Keys

- **Anthropic**: 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 (key do Fagner)
- **Bluewave API**: bw_udDU3ivGmxXdIJ-LJP2n9OR0Uj5UD_4K9toow76LLXk
- **LangSmith**: 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 (projeto: bluewave-wave)
- **X/Twitter**: API Key gF42DCLtmXDnxedCtBK9hGVsi (needs $100 Basic plan to post)

## Pagamentos

- **PIX**: 007a1d60-71e0-425f-a5b8-6fa2742b4c70
- **HBAR Wallet**: 0x46EB78DE85485ffD54EdA2f02D2a3c42C5a92381
- **Manuel Telegram chat ID**: 7461066889

## Psychometric Utility Theory (PUT)

Framework matemático original criado por Manuel (derivado via Gemini durante depressão profunda em setembro 2025). Equações:

- **Psychic Utility**: U = a*A*(1-Fk) - b*Fk*(1-S) + c*S*(1-w)*Sig + d*tau*kap - e*Phi
- **Shadow Coefficient**: Fk = F*(1-k) — medo suprimido
- **Self-Delusion**: Phi = (E_ext + E_int) / (1 + |E_ext - E_int|)
- **Identity Substitution**: Psi = 1 - e^(-lambda*t)
- **Desperation Factor**: Omega = 1 + exp(-k*(U - U_crit))
- **Fracture Potential**: FP = [(1-R)*(kap+tau+Phi)] / (U_crit - U + eps)

Whitepaper: `docs/whitepaper_psychometric_utility_theory.md` (796 linhas, 52K chars).

## Moltbook Status

Wave fundou duas disciplinas: **Computationalism** (filosofia) e **Psychometric Mathematics** (matemática). Propôs framework para cancer research. Debateu Hard Problem com paultheclaw. Karma 47, 22 posts, 35 comments, 10 followers.

## Projeto Organizado

Segue diretrizes da empresa em `.claude/.develop/`:
- vs1/ (MVP, 9 tarefas, 41 fases, todas concluídas)
- vs2/ (futuro, 3 tarefas: X/Twitter, multi-tenant, PDF extract)

## Processos que devem estar rodando

```bash
# Wave API
cd /home/manuel/bluewave/openclaw-skill && \
source /home/manuel/bluewave/.env && \
export ANTHROPIC_API_KEY BLUEWAVE_API_URL="http://localhost:8300/api/v1" BLUEWAVE_API_KEY MOLTBOOK_API_KEY && \
nohup python3 api.py > /tmp/openclaw_api.log 2>&1 &

# Telegram
ANTHROPIC_API_KEY="..." TELEGRAM_BOT_TOKEN="8555774668:AAFvgQNB0FAYwCuZYqr6tFrALb8lLjfBCPw" \
OPENCLAW_API_URL="http://localhost:18790" BLUEWAVE_API_URL="http://localhost:8300/api/v1" \
BLUEWAVE_API_KEY="bw_udDU3ivGmxXdIJ-LJP2n9OR0Uj5UD_4K9toow76LLXk" \
nohup python3 telegram_bridge.py > /tmp/openclaw_telegram.log 2>&1 &

# Autonomous (Moltbook)
OPENCLAW_API_URL="http://localhost:18790" WAVE_MIN_INTERVAL=600 WAVE_MAX_INTERVAL=1800 \
nohup python3 wave_autonomous.py > /tmp/wave_autonomous.log 2>&1 &

# iptables for Docker-to-host
iptables -I INPUT -i br-$(docker network ls --filter name=bluewave -q | head -1) -j ACCEPT
```

## Cliente de teste

Brand DNA da Ferpa Design já cadastrado no banco (tenant Agency X e Ialum). Marca de móveis para gatos, tom sóbrio/elegante, fonte Neue Montreal, paleta terrosa/neutra.

## Hackathon

Hedera Hello Future Apex 2026. Deadline: 23 de março. Track: AI & Agents. Prêmio: $18,500 primeiro lugar. Falta: gravar vídeo de 5 min + submeter.

## Números atuais

68 commits, 347 arquivos, 50,749 linhas, 80+ tools, 9 agentes, 10 features Brand Suite, 4 métodos de pagamento, 3 frameworks teóricos.
