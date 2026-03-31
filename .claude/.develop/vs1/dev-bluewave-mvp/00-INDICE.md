# Índice — Bluewave MVP (vs1/dev-bluewave-mvp)

> **Projeto:** Bluewave — AI Creative Operations SaaS
> **Versão:** vs1 (MVP)
> **Status:** 🟢 19/19 fases concluídas

## Descrição

Plataforma SaaS para agências de marketing gerenciarem assets de mídia com IA (Claude Vision), workflow de aprovação, compliance de marca, analytics, billing e publicação social. Arquitetura multi-tenant com isolamento row-level.

## Fases

| # | Fase | Arquivo | Dependências | Prioridade | Status |
|---|------|---------|--------------|------------|--------|
| 01 | Infraestrutura Docker | `01-INFRA-DOCKER.md` | — | Crítica | 🟢 |
| 02 | Database Models & Migrations | `02-DATABASE-MODELS.md` | 01 | Crítica | 🟢 |
| 03 | Autenticação JWT | `03-AUTH-JWT.md` | 02 | Crítica | 🟢 |
| 04 | Rotas de Negócio | `04-BUSINESS-ROUTES.md` | 03 | Crítica | 🟢 |
| 05 | Frontend Auth UI | `05-FRONTEND-AUTH.md` | 03 | Crítica | 🟢 |
| 06 | Frontend Dashboard & Assets | `06-FRONTEND-DASHBOARD.md` | 04, 05 | Crítica | 🟢 |
| 07 | Polish & Integração | `07-POLISH-INTEGRATION.md` | 06 | Alta | 🟢 |
| 08 | UX/UI Premium Redesign | `08-UX-UI-PREMIUM.md` | 07 | Alta | 🟢 |
| 09 | Landing Page | `09-LANDING-PAGE.md` | 08 | Média | 🟢 |
| 10 | IA Real — Claude Vision | `10-AI-CLAUDE-VISION.md` | 04 | Crítica | 🟢 |
| 11 | OpenClaw + Webhooks + API Keys | `11-OPENCLAW-WEBHOOKS-APIKEYS.md` | 10 | Alta | 🟢 |
| 12 | Brand Compliance Engine | `12-BRAND-COMPLIANCE.md` | 10 | Alta | 🟢 |
| 13 | Portals & Automações | `13-PORTALS-AUTOMATIONS.md` | 11 | Média | 🟢 |
| 14 | Analytics & ROI Dashboard | `14-ANALYTICS-ROI.md` | 04 | Alta | 🟢 |
| 15 | Calendar & Social Publishing | `15-CALENDAR-SOCIAL.md` | 04 | Média | 🟢 |
| 16 | Billing & Stripe | `16-BILLING-STRIPE.md` | 04 | Alta | 🟢 |
| 17 | Observabilidade (LangSmith + Sentry) | `17-OBSERVABILITY.md` | 10 | Alta | 🟢 |
| 18 | Trend Intelligence Agent | `18-TREND-INTELLIGENCE.md` | 10 | Média | 🟢 |
| 19 | OpenClaw Multi-Agent System | `19-OPENCLAW-AGENTS.md` | 11 | Alta | 🟢 |

## Grafo de Dependências

```
01 (Docker)
 └──► 02 (DB Models)
       └──► 03 (Auth JWT)
             ├──► 04 (Business Routes)
             │     ├──► 10 (AI Claude Vision)
             │     │     ├──► 11 (OpenClaw + Webhooks + API Keys)
             │     │     │     ├──► 13 (Portals & Automações)
             │     │     │     └──► 19 (OpenClaw Multi-Agent)
             │     │     ├──► 12 (Brand Compliance)
             │     │     ├──► 17 (Observabilidade)
             │     │     └──► 18 (Trend Intelligence)
             │     ├──► 14 (Analytics & ROI)
             │     ├──► 15 (Calendar & Social)
             │     └──► 16 (Billing & Stripe)
             └──► 05 (Frontend Auth)
                   └──► 06 (Frontend Dashboard)
                         └──► 07 (Polish)
                               └──► 08 (UX/UI Premium)
                                     └──► 09 (Landing Page)
```

## Referências

- **Documentação:** `.docs/` — visao-geral, pesquisas, decisoes, prompts, notas
- **Roadmap:** `.roadmap/roadmap-dev-bluewave-mvp.md` (plano) + `roadmap-dev-bluewave-mvp-status.md` (status)
- **Código:** `/home/manuel/bluewave/` (backend, frontend, openclaw-skill)
- **Docs públicos:** `/home/manuel/bluewave/docs/` (CHANGELOG.md, whitepaper.md)
