# Fase 18 — Trend Intelligence Agent 🟢

## Objetivo

Criar agente de inteligência de tendências que busca trends em Google Trends e Twitter/X, analisa com Claude para relevância ao tenant, e gera sugestões de conteúdo com captions e hashtags prontos.

## Componentes

### Modelo
- `TrendEntry` — keyword, source (google_trends/twitter), volume, sentiment, AI fields:
  - `relevance_score` (0-100) — relevância para a indústria do tenant
  - `suggestion` — sugestão de conteúdo baseada no trend
  - `caption_draft` — caption pronto para usar
  - `hashtags` — hashtags relevantes
  - `expires_at` — trends são temporais, expiram

### Trend Service (`services/trend_service.py`)
- **Google Trends fetcher** — pytrends: busca por keyword, retorna volume + related queries
- **Twitter/X fetcher** — API v2 (Bearer token): busca tweets recentes, calcula volume + sentiment
- **Combined pipeline** — busca nas duas fontes, deduplica, normaliza

### AI Analysis (`analyze_trends_with_ai()`)
- Envia trend data + contexto do tenant para Claude
- Claude avalia:
  - Relevância para a indústria do tenant (score 0-100)
  - Sugestão de como aproveitar o trend
  - Caption draft pronto
  - Hashtags otimizados
- Resultados persistidos no `TrendEntry`

### Router (`routers/trends.py`)
- `POST /trends/discover` — trigger: busca + AI analysis (keyword + source)
- `GET /trends` — listar trends do tenant (ordenado por relevance)
- `GET /trends/{id}` — detalhe de um trend
- `DELETE /trends/expired` — limpar trends expirados

### Frontend
- `TrendsPage.tsx`:
  - Formulário de descoberta (keyword input + source selector)
  - Cards de trends com:
    - Barra de relevância (0-100, colorida)
    - Sugestão de conteúdo
    - Caption draft com copy-to-clipboard
    - Hashtags com copy-to-clipboard
  - Filtro por source e ordenação por relevância

### Config
- `X_BEARER_TOKEN` — Twitter API v2 bearer token

### Migration
- Alembic migration para tabela `trend_entries`

## Entregáveis

- [x] TrendEntry model com campos AI
- [x] Google Trends fetcher (pytrends)
- [x] Twitter/X fetcher (API v2)
- [x] AI analysis com relevance scoring
- [x] Sugestões + caption draft + hashtags
- [x] Router com discover, list, detail, cleanup
- [x] TrendsPage com cards e copy-to-clipboard
- [x] Expiração automática de trends

## Critérios de Conclusão

- Discover "AI marketing" → busca Google + Twitter → Claude analisa → cards com score + sugestões
- Caption draft copiável com um clique
- Trends ordenados por relevância (mais relevantes primeiro)
- Trends expirados limpáveis via DELETE
