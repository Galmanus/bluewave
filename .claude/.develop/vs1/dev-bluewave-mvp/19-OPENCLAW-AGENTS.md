# Fase 19 — OpenClaw Multi-Agent System 🟢

## Objetivo

Construir sistema multi-agente completo para OpenClaw com 7 agentes especializados, 35 tools MCP-style, orquestrador inteligente e integração end-to-end com o Bluewave backend.

## Componentes

### Arquitetura
```
OpenClaw Gateway → Skill Server (:18790) → Bluewave Backend (:8300) → Claude API
    ↓ (POST /execute)        ↓ (REST API)            ↓ (Vision)
  Tool calls             API key auth           LangSmith traces
```

### 7 Agentes com Soul Prompts (`openclaw-skill/prompts/`)

| Agente | ID | Emoji | Tools | Responsabilidade |
|--------|----|-------|-------|-----------------|
| **Wave** | `bluewave-orchestrator` | 🌊 | 7 | Classifica intent, responde ou delega |
| **Curator** | `asset-curator` | 🎨 | 10 | Lifecycle de assets, catalogação |
| **Director** | `workflow-director` | ✅ | 9 | Workflow de aprovação, SLA, batch ops |
| **Guardian** | `brand-guardian` | 🛡️ | 6 | Brand compliance, visual governance |
| **Strategist** | `analytics-strategist` | 📊 | 6 | Analytics, ROI, insights preditivos |
| **Creative** | `creative-strategist` | ✍️ | 10 | Captions, briefs, scheduling, conteúdo |
| **Admin** | `ops-admin` | ⚙️ | 10 | Team management, billing, security |

### 35 Tools (`tools.json`)
- Definidos em formato MCP-style com JSON Schema
- Cada tool mapeia para um endpoint REST do Bluewave
- Autenticação via API Key no header

### Manifests
- `agents.json` — registry com soul prompt files, tool filters, delegation rules
- `tools.json` — 35 tool definitions com schemas de input/output
- `handlers.py` — execução de tools contra a API do Bluewave
- `server.py` — FastAPI server:
  - `GET /health` — healthcheck
  - `GET /tools` — listar tools disponíveis
  - `GET /agents` — listar agentes
  - `POST /execute` — executar tool call
  - `POST /hooks/bluewave` — receber webhooks do Bluewave

### Soul Prompts (`prompts/`)
- 7 arquivos markdown com personalidade, regras de comportamento, exemplos
- Cada agente tem expertise e tom específicos
- Wave (orchestrator) tem regras de roteamento para delegação

### LangSmith Integration
- Header `X-Langsmith-Trace` propagado automaticamente
- End-to-end tracing: chat → skill → API → Claude
- Parent/child trace relationships

### Docker
- `docker-compose.openclaw.yml` — adiciona skill server ao stack
- `Dockerfile` — container Python com dependências
- Porta `:18790` exposta

### Webhook Events
- Recebe eventos do Bluewave via `/hooks/bluewave`
- Pode reagir a: asset.uploaded, asset.approved, etc.
- Permite comportamentos reativos (ex: auto-analyze on upload)

## Entregáveis

- [x] 7 agentes com soul prompts distintos
- [x] 35 tools MCP-style funcionais
- [x] Wave orchestrator com roteamento inteligente
- [x] Server FastAPI com /execute endpoint
- [x] Webhook handler para eventos reativos
- [x] LangSmith trace propagation
- [x] Docker compose para deployment
- [x] README + SKILL.md + config example
- [x] Testes de handler

## Critérios de Conclusão

- "Show me my recent assets" → Wave delega para Curator → lista assets
- "Check brand compliance on asset X" → Wave delega para Guardian → retorna score
- "What's our ROI this month?" → Wave delega para Strategist → retorna análise
- Trace end-to-end visível no LangSmith
- Skill server healthy em `:18790`
