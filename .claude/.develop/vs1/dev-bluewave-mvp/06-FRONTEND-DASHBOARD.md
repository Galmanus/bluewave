# Fase 06 — Frontend Dashboard & Asset Management 🟢

## Objetivo

Construir todas as páginas da aplicação, hooks de dados com React Query e componentes de layout, cobrindo o ciclo completo de gestão de assets.

## Componentes

### 15 Páginas (`pages/`)

| Página | Rota | Descrição |
|--------|------|-----------|
| `LandingPage` | `/` | Marketing site (público) |
| `LoginPage` | `/login` | Login JWT |
| `RegisterPage` | `/register` | Registro tenant + admin |
| `DashboardPage` | `/dashboard` | Quick start + atividade recente |
| `AssetListPage` | `/assets` | Grid/list de assets com filtros + full-text search |
| `AssetDetailPage` | `/assets/:id` | Preview, versões, comentários, compliance score |
| `UploadPage` | `/assets/upload` | Drag-drop com progresso + status pipeline AI |
| `CalendarPage` | `/calendar` | Calendário mensal com posts agendados |
| `BrandPage` | `/brand` | Editor de guidelines (cores, tom, dos/don'ts) |
| `BriefsPage` | `/briefs` | Content brief CRUD + geração AI |
| `TrendsPage` | `/trends` | Trends sociais + predições |
| `AnalyticsPage` | `/analytics` | KPIs, ROI, produtividade da equipe |
| `BillingPage` | `/billing` | Plano atual, usage, upgrade, invoices |
| `TeamPage` | `/team` | Gestão de usuários, convite, roles |
| `IntegrationsPage` | `/integrations` | API keys, webhooks, conexões sociais |

### 9 Hooks (`hooks/`)

| Hook | React Query | Endpoints |
|------|-------------|-----------|
| `useAssets` | list, get, create, update, delete | `/assets` |
| `useUsers` | list, create, update, delete | `/users` |
| `useBrand` | get, update guidelines | `/brand` |
| `useBriefs` | list, create, generate | `/briefs` |
| `useCalendar` | list, schedule, publish | `/calendar` |
| `useComments` | list, create, resolve | `/comments` |
| `useTrends` | discover, list | `/trends` |
| `useIntegrations` | API keys + webhooks CRUD | `/api-keys`, `/webhooks` |
| `useVersions` | list, restore | `/versions` |

### Componentes de Layout
- `AppLayout.tsx` — sidebar colapsável (240→64px) + header (tenant name, user, logout)
- `AssetThumbnail.tsx` — preview com lazy loading + fallback
- `CommentsSection.tsx` — thread de comentários com resolve
- `VersionHistory.tsx` — timeline de versões do asset
- `SelectionToolbar.tsx` — toolbar flutuante para multi-select (bulk export, batch actions)
- `ErrorBoundary.tsx` — React error boundary

### Componentes Analytics (`components/analytics/`)
- `StatCard.tsx` — KPI card com trend indicator
- `TeamTable.tsx` — tabela de produtividade
- `ROICard.tsx` — display de cálculo ROI
- `AIQualityCard.tsx` — métricas de performance AI

## Entregáveis

- [x] 15 páginas implementadas e roteadas
- [x] 9 hooks React Query com cache invalidation
- [x] AppLayout com sidebar colapsável
- [x] Grid/list view de assets com filtros de status
- [x] Asset detail com versões, comentários e compliance
- [x] Upload drag-drop com barra de progresso
- [x] Calendário mensal funcional
- [x] Analytics dashboard com 4 cards

## Critérios de Conclusão

- Fluxo E2E no browser: upload → AI metadata → submit → approve
- Filtros de status funcionais na listagem
- Sidebar colapsa/expande com persistência
- React Query invalidation após mutations
