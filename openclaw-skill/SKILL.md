---
name: bluewave
description: "Sistema multi-agente de operações criativas — 1 orquestrador + 6 agentes especialistas PhD que gerenciam assets, aprovações, compliance, analytics, conteúdo e equipe via chat."
homepage: https://bluewave.app
user-invocable: true
metadata: {"openclaw":{"requires":{"env":["BLUEWAVE_API_URL","BLUEWAVE_API_KEY"]},"primaryEnv":"BLUEWAVE_API_KEY","emoji":"🌊"}}
---

# 🌊 Bluewave — Sistema Multi-Agente de Operações Criativas

Conecte seu workspace Bluewave ao OpenClaw. Um orquestrador central (Wave) classifica intenções e delega para 6 agentes especialistas PhD — cada um com domínio profundo em assets, aprovações, compliance, analytics, conteúdo ou administração. Tudo via WhatsApp, Telegram, Discord ou Slack.

## Configuração

1. No Bluewave (admin), vá em **Settings → API Keys** e crie uma nova chave.
2. Configure as variáveis de ambiente:
   ```bash
   export BLUEWAVE_API_URL="https://your-bluewave-instance.com/api/v1"
   export BLUEWAVE_API_KEY="bw_your_api_key_here"
   ```

## Agentes Especialistas

O sistema opera com 1 orquestrador + 6 especialistas. Cada agente tem um soul prompt dedicado, ferramentas restritas ao seu domínio e personalidade própria.

### 🌊 Wave — Orquestrador Principal

Ponto de entrada conversacional. Classifica intenções, responde perguntas simples diretamente e delega tarefas complexas para o especialista adequado. Coordena fluxos que cruzam múltiplos domínios.

**Tools:** `bluewave_list_assets`, `bluewave_get_asset`, `bluewave_get_profile`, `bluewave_list_team`, `bluewave_ai_usage`, `bluewave_get_brand_guidelines`, `delegate_to_agent`

### 🎨 Curator — Gestão de Assets Digitais

PhD em Ciência da Informação. Gestão, catalogação, busca e ciclo de vida de assets de mídia. Detecta duplicação e sugere limpeza proativamente.

**Tools:** `bluewave_list_assets`, `bluewave_get_asset`, `bluewave_upload_asset`, `bluewave_update_asset`, `bluewave_delete_asset`, `bluewave_regenerate_caption`, `bluewave_regenerate_hashtags`, `bluewave_search_assets`, `bluewave_bulk_export`, `bluewave_asset_variants`

### ✅ Director — Workflow de Aprovação

PhD em Gestão de Operações. Automação de processos, teoria de filas e tomada de decisão para workflows de aprovação. Monitora SLAs e alerta sobre gargalos.

**Tools:** `bluewave_submit_for_approval`, `bluewave_approve_asset`, `bluewave_reject_asset`, `bluewave_list_assets`, `bluewave_get_asset`, `bluewave_batch_approve`, `bluewave_workflow_stats`, `bluewave_auto_approve_by_score`, `bluewave_check_compliance`

### 🛡️ Guardian — Brand Compliance e Governança Visual

PhD em Comunicação Visual. Semiótica de marca, color science, tipografia e brand recognition. Gatekeeper da integridade visual e tonal.

**Tools:** `bluewave_check_compliance`, `bluewave_get_brand_guidelines`, `bluewave_get_asset`, `bluewave_update_brand_guidelines`, `bluewave_compliance_report`, `bluewave_check_external_image`

### 📊 Strategist — Analytics e Inteligência de Dados

PhD em Business Analytics. Marketing analytics, predictive modeling e data storytelling. Transforma dados brutos em insights acionáveis.

**Tools:** `bluewave_ai_usage`, `bluewave_list_assets`, `bluewave_dashboard_metrics`, `bluewave_roi_report`, `bluewave_trend_analysis`, `bluewave_team_productivity`

### ✍️ Creative — Estratégia de Conteúdo

PhD em Comunicação e Marketing Digital. Content strategy, brand storytelling e social media psychology. Sempre oferece 3 alternativas.

**Tools:** `bluewave_regenerate_caption`, `bluewave_regenerate_hashtags`, `bluewave_get_asset`, `bluewave_list_assets`, `bluewave_update_asset`, `bluewave_generate_brief`, `bluewave_caption_variants`, `bluewave_translate_caption`, `bluewave_content_calendar`, `bluewave_schedule_post`

### ⚙️ Admin — Administração de Plataforma

PhD em Sistemas de Informação. SaaS platform administration, IAM e segurança organizacional. Metódico e security-conscious.

**Tools:** `bluewave_list_team`, `bluewave_get_profile`, `bluewave_invite_user`, `bluewave_ai_usage`, `bluewave_remove_user`, `bluewave_update_user_role`, `bluewave_billing_summary`, `bluewave_create_api_key`, `bluewave_audit_log`, `bluewave_storage_usage`

## Comandos

### 🎨 Curator — Gestão de Assets

**Fazer upload de um asset** — Envie uma imagem ou vídeo com a mensagem:
> "Upload this to Bluewave"

O agente fará o upload do arquivo, e a IA do Bluewave gerará automaticamente um caption e hashtags usando Claude Vision.

**Listar assets** — Pergunte:
> "Show my assets" ou "Show pending assets" ou "Show approved assets"

**Ver detalhes do asset** — Pergunte:
> "Show asset [nome ou ID]"

**Buscar assets** — Pergunte:
> "Find assets about summer campaign" ou "Search for beach photos"

**Exportar assets em lote** — Peça:
> "Export these 5 assets as ZIP"

**Ver variantes de um asset** — Peça:
> "Show variants for [nome do asset]"

### ✅ Director — Workflow de Aprovação

**Submeter para aprovação** — Diga:
> "Submit [nome do asset] for approval"

Move o asset de draft → pending_approval.

**Aprovar um asset** — Diga:
> "Approve [nome do asset]"

Move de pending_approval → approved. (Apenas admin.)

**Rejeitar um asset** — Diga:
> "Reject [nome do asset] — needs better lighting"

Move de pending_approval → draft com comentário de rejeição.

**Aprovação em lote** — Diga:
> "Approve all pending assets" ou "Approve these 3 assets"

**Auto-aprovação por score** — Diga:
> "Auto-approve assets with compliance score above 90"

**Ver estatísticas do workflow** — Pergunte:
> "Show workflow stats" ou "What's our approval speed?"

### 🛡️ Guardian — Brand Compliance

**Verificar compliance** — Peça:
> "Check compliance on [nome do asset]"

Retorna score (0-100) + breakdown detalhado.

**Verificar imagem externa** — Peça:
> "Check this image URL for brand compliance"

**Ver brand guidelines** — Pergunte:
> "Show our brand guidelines"

**Atualizar guidelines** — Diga:
> "Update brand colors to #FF5733 and #2E86C1"

**Relatório de compliance** — Peça:
> "Generate a compliance report for the last 30 days"

### 📊 Strategist — Analytics

**Ver dashboard** — Pergunte:
> "Show dashboard" ou "Platform overview"

**Relatório de ROI** — Peça:
> "Generate ROI report"

**Análise de tendências** — Peça:
> "Show upload trends for the last 90 days"

**Produtividade da equipe** — Pergunte:
> "Show team productivity" ou "Who uploaded the most?"

**Uso de IA** — Pergunte:
> "How many AI actions have we used?" ou "AI usage this month"

### ✍️ Creative — Conteúdo

**Regenerar caption** — Peça:
> "Regenerate caption for [nome do asset]"

**Variantes de caption** — Peça:
> "Give me 3 caption options for [nome do asset]"

**Regenerar hashtags** — Peça:
> "New hashtags for [nome do asset]"

**Traduzir caption** — Peça:
> "Translate caption to Portuguese and Spanish"

**Gerar brief criativo** — Peça:
> "Create a brief for a summer sale campaign on Instagram"

**Ver calendário editorial** — Pergunte:
> "Show content calendar for next week"

**Agendar publicação** — Diga:
> "Schedule [nome do asset] for Instagram on April 1st at 2pm"

### ⚙️ Admin — Administração

**Listar membros da equipe** — Pergunte:
> "Show team" ou "Who's on the team?"

**Convidar um usuário** — Diga:
> "Invite jane@company.com as editor"

**Remover um usuário** — Diga:
> "Remove [nome] from the team"

**Alterar role** — Diga:
> "Change [nome] to admin"

**Resumo de billing** — Pergunte:
> "Show billing summary" ou "What's our current plan?"

**Criar API key** — Diga:
> "Create an API key for Zapier integration"

**Log de auditoria** — Pergunte:
> "Show audit log for the last 7 days"

**Uso de storage** — Pergunte:
> "How much storage are we using?"

## Referência da API

Todos os comandos mapeiam para a API REST do Bluewave em `$BLUEWAVE_API_URL`:

### Orquestrador

| Ação | Método | Endpoint |
|------|--------|----------|
| Listar assets | GET | `/assets?status={status}&page=1&size=20` |
| Obter asset | GET | `/assets/{id}` |
| Obter perfil | GET | `/users/me` |
| Listar equipe | GET | `/users` |
| Uso de IA | GET | `/ai/usage?days=30` |
| Obter brand guidelines | GET | `/brand/guidelines` |
| Delegar para agente | — | Interno (roteamento do orquestrador) |

### 🎨 Curator — Assets

| Ação | Método | Endpoint |
|------|--------|----------|
| Listar assets | GET | `/assets?status={status}&page=1&size=20` |
| Obter asset | GET | `/assets/{id}` |
| Upload de asset | POST | `/assets` (multipart) |
| Atualizar asset | PATCH | `/assets/{id}` |
| Deletar asset | DELETE | `/assets/{id}` |
| Regenerar caption | POST | `/ai/caption/{id}` |
| Regenerar hashtags | POST | `/ai/hashtags/{id}` |
| Buscar assets | GET | `/assets/search?q={query}` |
| Exportar em lote | POST | `/assets/export` |
| Variantes do asset | GET | `/assets/{id}/variants` |

### ✅ Director — Workflow

| Ação | Método | Endpoint |
|------|--------|----------|
| Submeter para aprovação | POST | `/assets/{id}/submit` |
| Aprovar asset | POST | `/assets/{id}/approve` |
| Rejeitar asset | POST | `/assets/{id}/reject` |
| Aprovação em lote | POST | `/assets/batch-approve` |
| Estatísticas do workflow | GET | `/workflow/stats?days=30` |
| Auto-aprovar por score | POST | `/workflow/auto-approve` |
| Verificar compliance | POST | `/brand/check/{id}` |

### 🛡️ Guardian — Compliance

| Ação | Método | Endpoint |
|------|--------|----------|
| Verificar compliance | POST | `/brand/check/{id}` |
| Obter brand guidelines | GET | `/brand/guidelines` |
| Atualizar guidelines | PUT | `/brand/guidelines` |
| Relatório de compliance | GET | `/brand/report?days=30` |
| Verificar imagem externa | POST | `/brand/check-url` |

### 📊 Strategist — Analytics

| Ação | Método | Endpoint |
|------|--------|----------|
| Uso de IA | GET | `/ai/usage?days=30` |
| Métricas do dashboard | GET | `/analytics/dashboard?days=30` |
| Relatório de ROI | GET | `/analytics/roi` |
| Análise de tendências | GET | `/analytics/trends?metric={metric}&days=90` |
| Produtividade da equipe | GET | `/analytics/team-productivity?days=30` |

### ✍️ Creative — Conteúdo

| Ação | Método | Endpoint |
|------|--------|----------|
| Regenerar caption | POST | `/ai/caption/{id}` |
| Regenerar hashtags | POST | `/ai/hashtags/{id}` |
| Gerar brief criativo | POST | `/ai/brief` |
| Variantes de caption | POST | `/ai/caption-variants/{id}` |
| Traduzir caption | POST | `/ai/translate/{id}` |
| Calendário editorial | GET | `/content/calendar?start={date}&end={date}` |
| Agendar publicação | POST | `/content/schedule` |

### ⚙️ Admin — Plataforma

| Ação | Método | Endpoint |
|------|--------|----------|
| Listar equipe | GET | `/users` |
| Obter perfil | GET | `/users/me` |
| Convidar usuário | POST | `/users` |
| Remover usuário | DELETE | `/users/{id}` |
| Alterar role | PATCH | `/users/{id}/role` |
| Resumo de billing | GET | `/billing/summary` |
| Criar API key | POST | `/api-keys` |
| Log de auditoria | GET | `/audit?days=7` |
| Uso de storage | GET | `/storage/usage` |

**Autenticação:** Todas as requisições usam o header `X-API-Key: $BLUEWAVE_API_KEY`.

## Eventos de Webhook

Configure o Bluewave para enviar eventos ao endpoint de webhook do OpenClaw para notificações em tempo real:

| Evento | Gatilho |
|--------|---------|
| `asset.uploaded` | Novo arquivo enviado |
| `asset.submitted` | Asset submetido para aprovação |
| `asset.approved` | Asset aprovado pelo admin |
| `asset.rejected` | Asset rejeitado com comentário |
| `ai.completed` | Caption/hashtags gerados pela IA |
| `user.invited` | Novo membro adicionado à equipe |

### Configurar webhook no Bluewave

```bash
curl -X POST $BLUEWAVE_API_URL/webhooks \
  -H "X-API-Key: $BLUEWAVE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "OpenClaw",
    "url": "http://localhost:18789/hooks/agent",
    "secret": "your-openclaw-hook-token",
    "events": "*"
  }'
```

Isso envia todos os eventos do Bluewave para o seu agente OpenClaw para notificações em tempo real via chat.
