"""Stripe billing service — checkout, portal, customer management, usage metering."""

import json
import logging
import uuid

import stripe

from app.core.config import settings

logger = logging.getLogger("bluewave.stripe")


def init_stripe() -> bool:
    """Configure Stripe API key. Returns True if configured."""
    if not settings.STRIPE_SECRET_KEY:
        logger.warning("STRIPE_SECRET_KEY not set — billing features disabled")
        return False
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return True


def get_price_ids() -> dict[str, str]:
    """Parse STRIPE_PRICE_IDS JSON into {plan: price_id} dict."""
    if not settings.STRIPE_PRICE_IDS:
        return {}
    try:
        return json.loads(settings.STRIPE_PRICE_IDS)
    except json.JSONDecodeError:
        logger.error("Invalid STRIPE_PRICE_IDS JSON: %s", settings.STRIPE_PRICE_IDS)
        return {}


async def create_customer(
    tenant_id: uuid.UUID,
    email: str,
    name: str,
) -> stripe.Customer:
    """Create a Stripe customer for a tenant."""
    return stripe.Customer.create(
        email=email,
        name=name,
        metadata={"tenant_id": str(tenant_id)},
    )


async def create_checkout_session(
    customer_id: str,
    price_id: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """Create a Stripe Checkout session. Returns the session URL."""
    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return session.url


async def create_portal_session(
    customer_id: str,
    return_url: str,
) -> str:
    """Create a Stripe Customer Portal session. Returns the portal URL."""
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return session.url


async def list_invoices(customer_id: str, limit: int = 20) -> list[dict]:
    """List invoices for a Stripe customer."""
    invoices = stripe.Invoice.list(customer=customer_id, limit=limit)
    return [
        {
            "id": inv.id,
            "status": inv.status,
            "amount_due": inv.amount_due,
            "currency": inv.currency,
            "created": inv.created,
            "hosted_invoice_url": inv.hosted_invoice_url,
            "pdf": inv.invoice_pdf,
        }
        for inv in invoices.data
    ]


async def report_usage(
    subscription_item_id: str,
    quantity: int = 1,
) -> None:
    """Report metered usage to Stripe for billing."""
    try:
        stripe.SubscriptionItem.create_usage_record(
            subscription_item_id,
            quantity=quantity,
            action="increment",
        )
    except stripe.StripeError:
        logger.exception("Failed to report usage to Stripe")


def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
    """Verify and construct a Stripe webhook event."""
    return stripe.Webhook.construct_event(
        payload,
        sig_header,
        settings.STRIPE_WEBHOOK_SECRET,
    )
