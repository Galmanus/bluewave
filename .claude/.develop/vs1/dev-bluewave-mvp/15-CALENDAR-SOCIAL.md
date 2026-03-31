# Fase 15 — Content Calendar & Social Media Publishing 🟢

## Objetivo

Implementar calendário de conteúdo com agendamento e publicação direta em Twitter/X e LinkedIn, com scheduler em background para auto-publicação.

## Componentes

### Modelo
- `ScheduledPost` — asset_id, platform (twitter/linkedin), scheduled_at, published_at, status (scheduled/published/failed), caption_override, error_message

### Social Publishing Service (`services/social_publish_service.py`)
- **Twitter/X**: Tweepy (API v2) — upload media + create tweet
- **LinkedIn**: API v2 — upload image + create share
- Suporte a caption override (usa caption do asset se não especificado)
- Error handling com logging detalhado

### Scheduler (`services/scheduler.py`)
- APScheduler background task
- Verifica posts com `scheduled_at <= now()` e `status = scheduled`
- Executa publicação e atualiza status
- Retry em caso de falha temporária

### Router (`routers/calendar.py`)
- `GET /calendar` — listar posts agendados (filtro por data range)
- `POST /calendar` — agendar publicação (asset + platform + datetime)
- `POST /calendar/{id}/publish` — publicar imediatamente (on-demand)
- `DELETE /calendar/{id}` — cancelar agendamento

### Frontend
- `CalendarPage.tsx` — visualização mensal com grid
  - Posts agendados exibidos no dia correto
  - Botão de publicar imediata em cada post
  - Formulário de agendamento (select asset, platform, datetime)
  - Status badges: scheduled (azul), published (verde), failed (vermelho)

### Config
- `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET`
- `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`

## Entregáveis

- [x] ScheduledPost model funcional
- [x] Twitter/X publishing via Tweepy
- [x] LinkedIn publishing via API v2
- [x] APScheduler auto-publicação
- [x] Calendar router com CRUD
- [x] CalendarPage com visualização mensal
- [x] Publicação on-demand
- [x] Status tracking (scheduled/published/failed)

## Critérios de Conclusão

- Agendar post para Twitter → no horário, post publicado automaticamente
- Publicar on-demand → tweet criado imediatamente
- CalendarPage mostra posts no dia correto
- Falha de API → status `failed` com error message
