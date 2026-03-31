# ADR-04 — Stripe como Provider de Billing

> Status: Aceita
> Data: 2026-03-18

## Contexto

O Bluewave precisa de billing com 4 tiers de assinatura, enforcement de limites por plano, e self-service para upgrade/downgrade/cancelamento.

## Decisão

Adotamos **Stripe** com Checkout Sessions, Customer Portal, Webhooks e Usage Metering para billing completo.

### Implementação
- `TenantSubscription` model: plan_tier, stripe_customer_id, stripe_subscription_id, ai_actions_used/limit
- 4 tiers: free ($0, 50 AI/mês), pro ($12/user), business ($49/user), enterprise ($149/user)
- Checkout Sessions para signup de plano pago
- Customer Portal para self-service (upgrade, cancel, payment method)
- Webhooks: subscription.created/updated/deleted, invoice.paid/failed
- Metering: cada AI action incrementa contador, reset mensal
- Enforcement: middleware retorna 402 Payment Required quando limite atingido
- `plan_limits.py` bloqueia features por tier (ex: brand compliance → Pro+)

## Alternativas Consideradas

| Provider | Prós | Contras | Veredicto |
|----------|------|---------|-----------|
| Paddle | Tax handling built-in | Menos flexível, SaaS focus | Rejeitada — menos controle |
| LemonSqueezy | Simples, MoR | Menos features enterprise | Rejeitada — limitado |
| Custom billing | Controle total | PCI compliance, manutenção pesada | Rejeitada — não vale o esforço |
| **Stripe** | Padrão de indústria, completo | Precisa de webhook handling | **Aceita** |

## Consequências

**Positivas:**
- PCI compliance delegada ao Stripe
- Customer Portal elimina 90% do suporte de billing
- Webhooks mantêm sync confiável
- Metering permite billing baseado em uso (AI actions)
- Checkout Sessions são mobile-friendly

**Negativas:**
- Taxa Stripe (2.9% + 30¢ por transação)
- Webhook handling requer idempotência (implementado)
- Debugging de webhooks pode ser complexo (Stripe CLI ajuda)
