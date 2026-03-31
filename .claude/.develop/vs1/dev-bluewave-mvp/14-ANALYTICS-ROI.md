# Fase 14 — Analytics & ROI Dashboard 🟢

## Objetivo

Fornecer insights de negócio com KPIs, análise de tendências, produtividade da equipe, qualidade da IA, cálculo de ROI e relatórios PDF, com cache Redis para performance.

## Componentes

### Router (`routers/analytics.py`)

| Endpoint | Descrição |
|----------|-----------|
| `GET /analytics/overview` | KPIs principais: total assets, aprovados, tempo médio aprovação, AI actions |
| `GET /analytics/trends` | Time series: assets por dia/semana/mês, aprovações, rejeições |
| `GET /analytics/team` | Produtividade por usuário: uploads, aprovações, tempo médio |
| `GET /analytics/ai-quality` | Performance AI: acceptance rate, edit rate, avg confidence |
| `GET /analytics/roi` | Cálculo ROI: tempo economizado × custo/hora vs. custo da plataforma |
| `GET /analytics/predictions` | Projeções: volume estimado, bottlenecks, recomendações |
| `POST /analytics/report` | Gera relatório PDF mensal com todos os KPIs |

### Services

#### `prediction_service.py`
- Análise de tendências históricas
- Projeções de volume e bottlenecks
- Cache Redis 24h para evitar recalcular

#### `report_service.py`
- Geração PDF com ReportLab
- KPIs do mês, gráficos, sumário executivo
- Anexável em email mensal (via `email_service`)

### Frontend

#### `AnalyticsPage.tsx`
- Dashboard com 4 cards + gráficos

#### Componentes (`components/analytics/`)
- `StatCard.tsx` — KPI com trend indicator (↑↓) e variação percentual
- `TeamTable.tsx` — ranking de produtividade da equipe
- `ROICard.tsx` — display de ROI calculado (horas economizadas × valor)
- `AIQualityCard.tsx` — métricas de qualidade AI (acceptance, edits, confidence)

### Cache (`core/cache.py`)
- Redis async client
- Keys cacheadas: guidelines, billing, asset counts, predictions
- TTL: predictions 24h, outros 5-15min

## Entregáveis

- [x] 6 endpoints analytics + 1 report generation
- [x] Prediction service com cache Redis
- [x] PDF report com ReportLab
- [x] AnalyticsPage com 4 cards
- [x] StatCard, TeamTable, ROICard, AIQualityCard
- [x] Redis cache para performance

## Critérios de Conclusão

- Dashboard mostra KPIs reais do tenant
- Predictions retornam em <200ms (cache hit)
- PDF report gerado com dados corretos
- Team table mostra produtividade por usuário
