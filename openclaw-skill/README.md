# Bluewave OpenClaw Skill — Sistema Multi-Agente

Sistema multi-agente de operações criativas para o OpenClaw. Um orquestrador central (Wave) classifica intenções e delega para 6 agentes especialistas PhD — cada um com domínio profundo, soul prompt dedicado e ferramentas restritas. Gerencie assets, aprovações, compliance, analytics, conteúdo e equipe via WhatsApp, Telegram, Discord ou Slack.

## Arquitetura

```
WhatsApp / Telegram / Discord / Slack
        │
        ▼
   OpenClaw Gateway
   (routing + sessions)
        │
        ▼ Tool calls (HTTP POST)
   Bluewave Skill Server (:18790)
   ├── GET  /health          → verificação de status
   ├── GET  /tools           → manifesto de tools (35 tools)
   ├── GET  /agents          → manifesto de agentes (7 agentes)
   ├── POST /execute         → executar uma tool contra a API Bluewave
   └── POST /hooks/bluewave  → receber + formatar eventos de webhook
        │
        ▼ REST API (autenticação via X-API-Key + X-Langsmith-Trace)
   Bluewave Backend (:8300)
   /api/v1/*
        │
        ├── ▼ Eventos de webhook (HMAC-SHA256)
        │   Skill Server → OpenClaw → Notificação no chat
        │
        └── ▼ AI Traces (opcional)
            LangSmith (observabilidade end-to-end)
```

### Fluxo Multi-Agente

```
Mensagem do usuário
        │
        ▼
  🌊 Wave (Orquestrador)
  Classifica intenção, responde direto ou delega
        │
        ├──→ 🎨 Curator     (upload, busca, organização, export de assets)
        ├──→ ✅ Director     (submissão, aprovação, rejeição, batch ops)
        ├──→ 🛡️ Guardian     (compliance check, guidelines, relatórios de marca)
        ├──→ 📊 Strategist   (dashboard, ROI, tendências, produtividade)
        ├──→ ✍️ Creative     (captions, briefs, calendário, agendamento)
        └──→ ⚙️ Admin        (equipe, billing, API keys, auditoria)
                │
                ▼
        Resposta ao usuário
```

## Estrutura de Arquivos

| Arquivo | Finalidade |
|---------|-----------|
| `agents.json` | Manifesto multi-agente — define orquestrador, 6 especialistas, tools por agente e regras de roteamento |
| `tools.json` | Manifesto de tools no estilo MCP (35 tools com JSON schemas) |
| `handler.py` | Handler Python — executa tools contra a API Bluewave |
| `server.py` | Servidor HTTP (FastAPI) — expõe tools, agentes + receptor de webhook |
| `prompts/` | Soul prompts dos agentes (1 arquivo `.md` por agente) |
| `prompts/orchestrator.md` | Soul prompt do orquestrador Wave |
| `prompts/curator.md` | Soul prompt do Curator (assets) |
| `prompts/director.md` | Soul prompt do Director (workflow) |
| `prompts/guardian.md` | Soul prompt do Guardian (compliance) |
| `prompts/strategist.md` | Soul prompt do Strategist (analytics) |
| `prompts/creative.md` | Soul prompt do Creative (conteúdo) |
| `prompts/admin.md` | Soul prompt do Admin (plataforma) |
| `SKILL.md` | Definição da skill OpenClaw com frontmatter |
| `openclaw-config-example.json5` | Template completo de configuração OpenClaw multi-agente |
| `Dockerfile` | Build do container para o skill server |
| `requirements.txt` | Dependências Python |

## Agentes Especialistas

### 🌊 Wave — Orquestrador Principal

**ID:** `bluewave-orchestrator`
**Domínio:** Ponto de entrada conversacional

Classifica intenções, responde perguntas simples diretamente e delega tarefas complexas para o especialista adequado. Coordena fluxos que cruzam múltiplos domínios.

**Tools (7):** `bluewave_list_assets`, `bluewave_get_asset`, `bluewave_get_profile`, `bluewave_list_team`, `bluewave_ai_usage`, `bluewave_get_brand_guidelines`, `delegate_to_agent`

---

### 🎨 Curator — Gestão de Assets Digitais

**ID:** `asset-curator`
**Domínio:** Ciência da Informação — gestão, catalogação, busca e ciclo de vida de assets

Organiza, busca e gerencia o ciclo de vida completo de assets de mídia. Detecta duplicação e sugere limpeza proativamente.

**Tools (10):**

| Tool | Descrição |
|------|-----------|
| `bluewave_list_assets` | Listar assets com filtro de status e paginação |
| `bluewave_get_asset` | Obter detalhes do asset (caption, hashtags, compliance, info do arquivo) |
| `bluewave_upload_asset` | Upload de imagem/vídeo — IA gera caption + hashtags automaticamente |
| `bluewave_update_asset` | Atualizar caption ou hashtags |
| `bluewave_delete_asset` | Deletar um asset (apenas admin, confirma antes) |
| `bluewave_regenerate_caption` | Re-executar Claude Vision para novo caption |
| `bluewave_regenerate_hashtags` | Re-executar Claude Vision para novas hashtags |
| `bluewave_search_assets` | Busca full-text por caption, hashtags ou filename |
| `bluewave_bulk_export` | Exportar múltiplos assets como ZIP |
| `bluewave_asset_variants` | Listar variantes de resize (thumbnails, crops para social) |

---

### ✅ Director — Workflow de Aprovação e Operações

**ID:** `workflow-director`
**Domínio:** Gestão de Operações — automação de processos, teoria de filas, decision-making

Gerencia o pipeline de aprovação de ponta a ponta. Monitora SLAs, alerta sobre gargalos e suporta operações em lote.

**Tools (9):**

| Tool | Descrição |
|------|-----------|
| `bluewave_submit_for_approval` | Submeter draft para aprovação pendente |
| `bluewave_approve_asset` | Aprovar asset pendente (apenas admin) |
| `bluewave_reject_asset` | Rejeitar com comentário (apenas admin) |
| `bluewave_list_assets` | Listar assets filtrados por status |
| `bluewave_get_asset` | Obter detalhes do asset |
| `bluewave_batch_approve` | Aprovar múltiplos assets de uma vez |
| `bluewave_workflow_stats` | Métricas de performance do workflow (tempo médio, taxa de rejeição) |
| `bluewave_auto_approve_by_score` | Auto-aprovar assets com compliance score acima de threshold |
| `bluewave_check_compliance` | Pontuar asset contra brand guidelines (0-100) |

---

### 🛡️ Guardian — Brand Compliance e Governança Visual

**ID:** `brand-guardian`
**Domínio:** Comunicação Visual — semiótica de marca, color science, tipografia

Gatekeeper da integridade visual e tonal da marca. Oferece correções, não apenas críticas.

**Tools (6):**

| Tool | Descrição |
|------|-----------|
| `bluewave_check_compliance` | Pontuar asset contra brand guidelines (0-100) |
| `bluewave_get_brand_guidelines` | Obter cores da marca, tom, dos/don'ts |
| `bluewave_get_asset` | Obter detalhes do asset |
| `bluewave_update_brand_guidelines` | Atualizar guidelines (cores, fontes, tom, regras) |
| `bluewave_compliance_report` | Relatório agregado de compliance (scores médios, issues comuns) |
| `bluewave_check_external_image` | Verificar compliance de imagem externa por URL (sem upload) |

---

### 📊 Strategist — Analytics de Operações Criativas

**ID:** `analytics-strategist`
**Domínio:** Business Analytics — marketing analytics, predictive modeling, data storytelling

Transforma dados brutos em insights acionáveis. Nunca apresenta números isolados — sempre com contexto, tendência e ação recomendada.

**Tools (6):**

| Tool | Descrição |
|------|-----------|
| `bluewave_ai_usage` | Contagem de ações de IA + detalhamento de custos |
| `bluewave_list_assets` | Listar assets para análise quantitativa |
| `bluewave_dashboard_metrics` | KPIs principais: volume, velocidade de aprovação, eficiência, economia |
| `bluewave_roi_report` | Cálculo de ROI: tempo economizado vs custo da plataforma |
| `bluewave_trend_analysis` | Análise de tendências com IA (padrões, sazonalidade, previsões) |
| `bluewave_team_productivity` | Métricas por membro (uploads, aprovações, tempo de resposta) |

---

### ✍️ Creative — Estratégia de Conteúdo e Criação Assistida por IA

**ID:** `creative-strategist`
**Domínio:** Comunicação e Marketing Digital — content strategy, brand storytelling, social media

Pensador criativo que equilibra intuição artística com dados. Sempre oferece 3 alternativas e pensa cross-platform.

**Tools (10):**

| Tool | Descrição |
|------|-----------|
| `bluewave_regenerate_caption` | Re-executar Claude Vision para novo caption |
| `bluewave_regenerate_hashtags` | Re-executar Claude Vision para novas hashtags |
| `bluewave_get_asset` | Obter detalhes do asset |
| `bluewave_list_assets` | Listar assets para análise de conteúdo |
| `bluewave_update_asset` | Atualizar caption ou hashtags |
| `bluewave_generate_brief` | Gerar brief criativo completo com IA (objetivos, público, mensagens) |
| `bluewave_caption_variants` | Gerar 3 variantes de caption em tons diferentes |
| `bluewave_translate_caption` | Traduzir caption para múltiplos idiomas |
| `bluewave_content_calendar` | Ver calendário editorial com posts agendados e publicados |
| `bluewave_schedule_post` | Agendar asset aprovado para publicação em canal social |

---

### ⚙️ Admin — Administração de Plataforma e Gestão de Equipe

**ID:** `ops-admin`
**Domínio:** Sistemas de Informação — SaaS administration, IAM, segurança organizacional

Metódico e security-conscious. Explica consequências antes de executar ações destrutivas.

**Tools (10):**

| Tool | Descrição |
|------|-----------|
| `bluewave_list_team` | Listar membros da equipe com roles |
| `bluewave_get_profile` | Obter perfil do usuário atual |
| `bluewave_invite_user` | Convidar novo membro (apenas admin) |
| `bluewave_ai_usage` | Contagem de ações de IA + custos |
| `bluewave_remove_user` | Remover membro da equipe (com resumo de impacto) |
| `bluewave_update_user_role` | Alterar role de um membro (admin/editor/viewer) |
| `bluewave_billing_summary` | Resumo de billing (plano atual, uso, faturas, projeção) |
| `bluewave_create_api_key` | Criar API key para integrações externas |
| `bluewave_audit_log` | Consultar log de auditoria (quem fez o quê e quando) |
| `bluewave_storage_usage` | Uso de storage (total, por tipo de arquivo, crescimento) |

## Início Rápido

### Opção 1: Docker (recomendado)

```bash
# A partir da raiz do projeto bluewave:

# 1. Configure sua API key no .env
echo "BLUEWAVE_API_KEY=bw_your_key_here" >> .env
echo "OPENCLAW_HOOK_TOKEN=your-secret-here" >> .env

# 2. Inicie tudo (base + OpenClaw skill)
docker compose -f docker-compose.yml -f docker-compose.openclaw.yml up -d

# 3. Verifique
curl http://localhost:18790/health
# → {"status":"ok","skill":"bluewave","connected":true}

# 4. Veja as tools disponíveis
curl http://localhost:18790/tools | python -m json.tool

# 5. Veja os agentes disponíveis
curl http://localhost:18790/agents | python -m json.tool
```

### Opção 2: Standalone

```bash
cd openclaw-skill

# 1. Instale as dependências
pip install -r requirements.txt

# 2. Configure o ambiente
export BLUEWAVE_API_URL="http://localhost:8300/api/v1"
export BLUEWAVE_API_KEY="bw_your_key_here"

# 3. Execute o skill server
python server.py
# → Bluewave skill connected to http://localhost:8300/api/v1
# → Uvicorn running on http://0.0.0.0:18790
```

### Opção 3: OpenClaw Skills Registry

```bash
openclaw skill install bluewave
```

## Referência Completa de Tools (35)

### Orquestrador (7 tools)

| Tool | Descrição |
|------|-----------|
| `bluewave_list_assets` | Listar assets com filtro de status e paginação |
| `bluewave_get_asset` | Obter detalhes do asset |
| `bluewave_get_profile` | Obter perfil do usuário atual |
| `bluewave_list_team` | Listar membros da equipe com roles |
| `bluewave_ai_usage` | Contagem de ações de IA + custos |
| `bluewave_get_brand_guidelines` | Obter cores da marca, tom, dos/don'ts |
| `delegate_to_agent` | Delegar tarefa para um agente especialista |

### Assets — Curator (10 tools)

| Tool | Descrição |
|------|-----------|
| `bluewave_list_assets` | Listar assets com filtro de status e paginação |
| `bluewave_get_asset` | Obter detalhes do asset (caption, hashtags, compliance, info do arquivo) |
| `bluewave_upload_asset` | Upload de imagem/vídeo — IA gera caption + hashtags automaticamente |
| `bluewave_update_asset` | Atualizar caption ou hashtags |
| `bluewave_delete_asset` | Deletar um asset (apenas admin, confirma antes) |
| `bluewave_regenerate_caption` | Re-executar Claude Vision para novo caption |
| `bluewave_regenerate_hashtags` | Re-executar Claude Vision para novas hashtags |
| `bluewave_search_assets` | Busca full-text por caption, hashtags ou filename |
| `bluewave_bulk_export` | Exportar múltiplos assets como ZIP |
| `bluewave_asset_variants` | Listar variantes de resize (thumbnails, crops para social) |

### Workflow — Director (9 tools)

| Tool | Descrição |
|------|-----------|
| `bluewave_submit_for_approval` | Submeter draft para aprovação pendente |
| `bluewave_approve_asset` | Aprovar asset pendente (apenas admin) |
| `bluewave_reject_asset` | Rejeitar com comentário (apenas admin) |
| `bluewave_list_assets` | Listar assets filtrados por status |
| `bluewave_get_asset` | Obter detalhes do asset |
| `bluewave_batch_approve` | Aprovar múltiplos assets de uma vez |
| `bluewave_workflow_stats` | Métricas de performance do workflow |
| `bluewave_auto_approve_by_score` | Auto-aprovar por compliance score |
| `bluewave_check_compliance` | Pontuar asset contra brand guidelines (0-100) |

### Compliance — Guardian (6 tools)

| Tool | Descrição |
|------|-----------|
| `bluewave_check_compliance` | Pontuar asset contra brand guidelines (0-100) |
| `bluewave_get_brand_guidelines` | Obter cores da marca, tom, dos/don'ts |
| `bluewave_get_asset` | Obter detalhes do asset |
| `bluewave_update_brand_guidelines` | Atualizar guidelines (cores, fontes, tom, regras) |
| `bluewave_compliance_report` | Relatório agregado de compliance |
| `bluewave_check_external_image` | Verificar compliance de imagem externa por URL |

### Analytics — Strategist (6 tools)

| Tool | Descrição |
|------|-----------|
| `bluewave_ai_usage` | Contagem de ações de IA + custos |
| `bluewave_list_assets` | Listar assets para análise quantitativa |
| `bluewave_dashboard_metrics` | KPIs do dashboard (volume, velocidade, eficiência, economia) |
| `bluewave_roi_report` | Cálculo de ROI: tempo economizado vs custo |
| `bluewave_trend_analysis` | Análise de tendências com IA (padrões, previsões) |
| `bluewave_team_productivity` | Métricas de produtividade por membro |

### Conteúdo — Creative (10 tools)

| Tool | Descrição |
|------|-----------|
| `bluewave_regenerate_caption` | Re-executar Claude Vision para novo caption |
| `bluewave_regenerate_hashtags` | Re-executar Claude Vision para novas hashtags |
| `bluewave_get_asset` | Obter detalhes do asset |
| `bluewave_list_assets` | Listar assets para análise de conteúdo |
| `bluewave_update_asset` | Atualizar caption ou hashtags |
| `bluewave_generate_brief` | Gerar brief criativo completo com IA |
| `bluewave_caption_variants` | Gerar 3 variantes de caption em tons diferentes |
| `bluewave_translate_caption` | Traduzir caption para múltiplos idiomas |
| `bluewave_content_calendar` | Ver calendário editorial |
| `bluewave_schedule_post` | Agendar asset para publicação em canal social |

### Plataforma — Admin (10 tools)

| Tool | Descrição |
|------|-----------|
| `bluewave_list_team` | Listar membros da equipe com roles |
| `bluewave_get_profile` | Obter perfil do usuário atual |
| `bluewave_invite_user` | Convidar novo membro (apenas admin) |
| `bluewave_ai_usage` | Contagem de ações de IA + custos |
| `bluewave_remove_user` | Remover membro da equipe |
| `bluewave_update_user_role` | Alterar role de um membro |
| `bluewave_billing_summary` | Resumo de billing |
| `bluewave_create_api_key` | Criar API key para integrações |
| `bluewave_audit_log` | Consultar log de auditoria |
| `bluewave_storage_usage` | Uso de storage |

## Customizando Soul Prompts

Cada agente possui um soul prompt dedicado na pasta `prompts/`. O soul prompt define a personalidade, regras de comportamento e estilo de comunicação do agente.

### Arquivos de prompt

| Arquivo | Agente |
|---------|--------|
| `prompts/orchestrator.md` | 🌊 Wave — regras de roteamento e coordenação |
| `prompts/curator.md` | 🎨 Curator — gestão de assets e organização |
| `prompts/director.md` | ✅ Director — workflow de aprovação e SLAs |
| `prompts/guardian.md` | 🛡️ Guardian — compliance de marca e color science |
| `prompts/strategist.md` | 📊 Strategist — analytics e data storytelling |
| `prompts/creative.md` | ✍️ Creative — conteúdo e estratégia criativa |
| `prompts/admin.md` | ⚙️ Admin — administração e segurança |

### Como personalizar

1. Edite o arquivo `.md` correspondente na pasta `prompts/`.
2. O `agents.json` referencia cada arquivo via `soul_prompt_file`.
3. Reinicie o skill server para carregar as alterações.

Exemplo de customização no `openclaw-config-example.json5` — o campo `soul` de cada agente na seção `agents.list` pode ser sobrescrito inline ou apontar para o arquivo:

```json5
{
  id: "asset-curator",
  soul: `🎨 Você é Curator, o especialista em gestão de ativos digitais...

  REGRAS:
  - Ao listar assets, sempre incluir contexto (total por status)
  - Ao upload, informar o pipeline IA
  - Buscas vagas: usar busca textual e oferecer melhores matches
  ...`,

  skills: [{ name: "bluewave", url: "http://localhost:18790" }],
  toolFilter: ["bluewave_list_assets", "bluewave_get_asset", ...]
}
```

## Configuração OpenClaw

Copie as seções relevantes de `openclaw-config-example.json5` para o seu `~/.openclaw/openclaw.json`.

Seções principais:

- **agents.list** — Define os 7 agentes (orquestrador + 6 especialistas) com soul prompts, skills e filtros de tools
- **agents.list[].canDelegate** — No orquestrador, lista os IDs dos agentes para os quais pode delegar
- **agents.list[].toolFilter** — Em cada especialista, restringe as tools visíveis ao domínio do agente
- **bindings** — Roteia mensagens de chat para agentes (por padrão tudo vai ao orquestrador; canais específicos podem ir direto a um especialista)
- **hooks** — Recebe eventos de webhook do Bluewave para notificações em tempo real
- **env** — URL da API, chave e secret do webhook

### Exemplo de binding direto para canais especializados

```json5
// Slack: brand compliance channel → Guardian diretamente
{
  agentId: "brand-guardian",
  match: {
    channel: "slack",
    peer: { kind: "channel", id: "C_BRAND_COMPLIANCE" }
  }
}
```

## Eventos de Webhook

| Evento | Notificação no Chat |
|--------|---------------------|
| `asset.uploaded` | "Novo asset enviado — IA gerando caption..." |
| `asset.submitted` | "Asset submetido para aprovação" |
| `asset.approved` | "Asset aprovado!" |
| `asset.rejected` | "Asset rejeitado: [motivo]" |
| `ai.completed` | "Análise de IA completa — [caption] [hashtags]" |
| `user.invited` | "Novo membro: [nome] entrou como [role]" |

## Exemplos de Chat

| Você diz | Agente acionado | O agente faz |
|----------|-----------------|-------------|
| *Envia uma imagem* | 🎨 Curator | `bluewave_upload_asset` — mostra caption + hashtags gerados pela IA |
| "Show my assets" | 🌊 Wave | `bluewave_list_assets` — lista formatada com ícones de status |
| "Find beach photos" | 🎨 Curator | `bluewave_search_assets` — busca full-text |
| "Submit abc123 for approval" | ✅ Director | `bluewave_submit_for_approval` |
| "Approve all pending" | ✅ Director | `bluewave_batch_approve` — confirma lista antes |
| "Check compliance on abc123" | 🛡️ Guardian | `bluewave_check_compliance` — score + breakdown |
| "Show dashboard" | 📊 Strategist | `bluewave_dashboard_metrics` — KPIs completos |
| "ROI report" | 📊 Strategist | `bluewave_roi_report` — tempo economizado vs custo |
| "Give me 3 caption options" | ✍️ Creative | `bluewave_caption_variants` — 3 tons diferentes |
| "Create a brief for summer campaign" | ✍️ Creative | `bluewave_generate_brief` — brief completo |
| "Schedule for Instagram tomorrow 2pm" | ✍️ Creative | `bluewave_schedule_post` |
| "Show team" | ⚙️ Admin | `bluewave_list_team` — membros com roles |
| "Invite jane@co.com as editor" | ⚙️ Admin | `bluewave_invite_user` — confirmação |
| "Show audit log" | ⚙️ Admin | `bluewave_audit_log` — últimas ações |

## LangSmith Cross-Service Tracing

Quando o Bluewave backend tem LangSmith configurado, o skill server automaticamente propaga o header `X-Langsmith-Trace` em todas as chamadas à API. Isso conecta os traces do OpenClaw (chat → skill → API) com os traces do Bluewave (API → Claude), permitindo visibilidade end-to-end no LangSmith dashboard.

Para ativar, passe um `langsmith_run_id` ao criar o handler:

```python
handler = BlueWaveHandler(langsmith_run_id="run_abc123...")
```

O header é adicionado automaticamente em todas as chamadas HTTP para endpoints AI (`/ai/caption`, `/ai/hashtags`, `/brand/check`).

## Variáveis de Ambiente

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `BLUEWAVE_API_URL` | Sim | URL base da API Bluewave |
| `BLUEWAVE_API_KEY` | Sim | Chave da API (formato: `bw_...`) |
| `BLUEWAVE_SKILL_PORT` | Não | Porta do skill server (padrão: `18790`) |
| `OPENCLAW_HOOK_TOKEN` | Não | Secret HMAC para webhooks |
