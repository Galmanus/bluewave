# Fase 16 — Billing Integration com Stripe 🟢

## Objetivo

Implementar billing completo com Stripe: 4 tiers de assinatura, checkout, customer portal, webhooks para sincronização e enforcement de limites por plano.

## Componentes

### Modelo
- `TenantSubscription` — tenant_id, plan_tier, stripe_customer_id, stripe_subscription_id, current_period_start/end, ai_actions_used, ai_actions_limit
- `PlanTier` enum: `free`, `pro`, `business`, `enterprise`

### Planos

| Tier | Preço | AI Actions/mês | Features |
|------|-------|-----------------|----------|
| Free | $0 | 50 | Core DAM + 1 user |
| Pro | $12/user | Ilimitado | + Brand compliance + analytics |
| Business | $49/user | Ilimitado | + Portals + automations + calendar |
| Enterprise | $149/user | Ilimitado | + SSO + dedicated support |

### Stripe Service (`services/stripe_service.py`)
- `create_checkout_session()` — redireciona para Stripe Checkout
- `create_portal_session()` — abre Stripe Customer Portal (self-service)
- `handle_webhook()` — processa eventos Stripe (subscription created/updated/deleted, invoice paid/failed)
- `meter_usage()` — registra AI actions para billing

### Rate Limiting (`core/rate_limit.py`)
- Verifica `ai_actions_used` vs `ai_actions_limit`
- Free: 50 AI actions/mês
- Pro+: ilimitado
- Retorna 402 Payment Required quando limite atingido

### Plan Enforcement (`core/plan_limits.py`)
- Middleware que verifica tier do tenant
- Features bloqueadas retornam 402 com mensagem explicativa
- Ex: "Brand compliance requires Pro plan or higher"

### Router (`routers/subscriptions.py`)
- `GET /billing/plan` — plano atual + uso
- `GET /billing/usage` — detalhamento de AI actions
- `POST /billing/checkout` — cria Stripe Checkout session
- `POST /billing/portal` — cria Stripe Portal session
- `GET /billing/invoices` — histórico de faturas
- `POST /stripe/webhook` — endpoint para webhooks Stripe

### Frontend
- `BillingPage.tsx`:
  - Card do plano atual com usage meter
  - Botão "Upgrade" → redireciona para Stripe Checkout
  - Botão "Manage" → abre Stripe Portal
  - Histórico de invoices

### Config
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_IDS` (JSON com price IDs por tier)

## Entregáveis

- [x] TenantSubscription model com PlanTier
- [x] Stripe Checkout integration
- [x] Stripe Customer Portal
- [x] Webhook handling (subscription lifecycle)
- [x] Rate limiting por plano (free: 50/mês)
- [x] Plan enforcement com 402
- [x] BillingPage com usage e upgrade
- [x] Invoice history

## Critérios de Conclusão

- Free tier → 51ª AI action → 402 Payment Required
- Upgrade via Checkout → webhook atualiza plano → limite removido
- Customer Portal abre e permite cancelamento
- Invoices listadas corretamente
