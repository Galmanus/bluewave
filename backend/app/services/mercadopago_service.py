"""Mercado Pago Payment Service — Pix, cartão, boleto, assinaturas recorrentes.

Handles:
- One-time payments (Pix, cartão, boleto)
- Recurring subscriptions (planos Pro e Agência)
- Webhook processing for payment confirmation
- Plan management (create/update/cancel)

Setup: MERCADOPAGO_ACCESS_TOKEN in .env
Docs: https://www.mercadopago.com.br/developers/pt/docs
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("bluewave.mercadopago")

MP_API = "https://api.mercadopago.com"

# Plan definitions — prices in BRL cents
PLANS = {
    "free": {"name": "Grátis", "price_cents": 0, "interval": "monthly", "features": ["1 marca", "50 checks/mês"]},
    "pro": {"name": "Pro", "price_cents": 19700, "interval": "monthly", "features": ["3 marcas", "Checks ilimitados", "Gerador de conteúdo"]},
    "pro_annual": {"name": "Pro Anual", "price_cents": 15700, "interval": "monthly", "features": ["3 marcas", "Checks ilimitados", "Economia de 20%"]},
    "agency": {"name": "Agência", "price_cents": 49700, "interval": "monthly", "features": ["Marcas ilimitadas", "White-label", "Wave autônomo"]},
    "agency_annual": {"name": "Agência Anual", "price_cents": 39700, "interval": "monthly", "features": ["Marcas ilimitadas", "White-label", "Economia de 20%"]},
}


def _headers():
    return {
        "Authorization": f"Bearer {settings.MERCADOPAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


async def create_pix_payment(
    amount_brl: float,
    description: str,
    payer_email: str,
    payer_name: str,
    external_reference: str,
) -> dict:
    """Create a Pix payment. Returns QR code and copy-paste code.

    The client scans the QR or copies the code to pay instantly.
    Webhook confirms payment automatically.
    """
    if not settings.MERCADOPAGO_ACCESS_TOKEN:
        return {"success": False, "error": "MERCADOPAGO_ACCESS_TOKEN not configured"}

    payload = {
        "transaction_amount": amount_brl,
        "description": description,
        "payment_method_id": "pix",
        "payer": {
            "email": payer_email,
            "first_name": payer_name.split()[0] if payer_name else "Cliente",
        },
        "external_reference": external_reference,
        "notification_url": f"{settings.APP_URL}/api/v1/webhooks/mercadopago",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{MP_API}/v1/payments", headers=_headers(), json=payload)
            data = r.json()

            if r.status_code in (200, 201):
                pix_data = data.get("point_of_interaction", {}).get("transaction_data", {})
                return {
                    "success": True,
                    "payment_id": data["id"],
                    "status": data["status"],
                    "qr_code": pix_data.get("qr_code"),
                    "qr_code_base64": pix_data.get("qr_code_base64"),
                    "copy_paste": pix_data.get("qr_code"),
                    "expires_at": data.get("date_of_expiration"),
                }
            else:
                logger.error("Pix payment failed: %s", data)
                return {"success": False, "error": data.get("message", "Payment creation failed")}

    except Exception as e:
        logger.error("Mercado Pago API error: %s", e)
        return {"success": False, "error": str(e)}


async def create_card_payment(
    amount_brl: float,
    description: str,
    token: str,
    installments: int,
    payer_email: str,
    external_reference: str,
) -> dict:
    """Create a credit card payment with optional installments (up to 12x)."""
    if not settings.MERCADOPAGO_ACCESS_TOKEN:
        return {"success": False, "error": "MERCADOPAGO_ACCESS_TOKEN not configured"}

    payload = {
        "transaction_amount": amount_brl,
        "description": description,
        "token": token,
        "installments": min(installments, 12),
        "payer": {"email": payer_email},
        "external_reference": external_reference,
        "notification_url": f"{settings.APP_URL}/api/v1/webhooks/mercadopago",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{MP_API}/v1/payments", headers=_headers(), json=payload)
            data = r.json()

            if r.status_code in (200, 201):
                return {
                    "success": True,
                    "payment_id": data["id"],
                    "status": data["status"],
                    "status_detail": data.get("status_detail"),
                }
            else:
                return {"success": False, "error": data.get("message", "Payment failed")}

    except Exception as e:
        logger.error("Card payment error: %s", e)
        return {"success": False, "error": str(e)}


async def create_subscription(
    plan_id: str,
    payer_email: str,
    card_token: Optional[str] = None,
    external_reference: str = "",
) -> dict:
    """Create a recurring subscription (preapproval) for Pro or Agency plans.

    Supports card-based auto-debit. For Pix recurring, we handle manually
    via cron (Pix doesn't support auto-debit natively in MP).
    """
    plan = PLANS.get(plan_id)
    if not plan:
        return {"success": False, "error": f"Unknown plan: {plan_id}"}

    if plan["price_cents"] == 0:
        return {"success": True, "plan": "free", "message": "Free plan, no payment needed"}

    if not settings.MERCADOPAGO_ACCESS_TOKEN:
        return {"success": False, "error": "MERCADOPAGO_ACCESS_TOKEN not configured"}

    payload = {
        "reason": f"Bluewave {plan['name']}",
        "auto_recurring": {
            "frequency": 1,
            "frequency_type": "months",
            "transaction_amount": plan["price_cents"] / 100,
            "currency_id": "BRL",
        },
        "payer_email": payer_email,
        "external_reference": external_reference,
        "back_url": f"{settings.APP_URL}/billing",
        "notification_url": f"{settings.APP_URL}/api/v1/webhooks/mercadopago",
    }

    if card_token:
        payload["card_token_id"] = card_token

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{MP_API}/preapproval", headers=_headers(), json=payload)
            data = r.json()

            if r.status_code in (200, 201):
                return {
                    "success": True,
                    "subscription_id": data.get("id"),
                    "status": data.get("status"),
                    "init_point": data.get("init_point"),
                    "plan": plan_id,
                }
            else:
                return {"success": False, "error": data.get("message", "Subscription creation failed")}

    except Exception as e:
        logger.error("Subscription error: %s", e)
        return {"success": False, "error": str(e)}


async def cancel_subscription(subscription_id: str) -> dict:
    """Cancel a recurring subscription."""
    if not settings.MERCADOPAGO_ACCESS_TOKEN:
        return {"success": False, "error": "Not configured"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.put(
                f"{MP_API}/preapproval/{subscription_id}",
                headers=_headers(),
                json={"status": "cancelled"},
            )
            return {"success": r.status_code == 200, "status": "cancelled"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_payment_status(payment_id: str) -> dict:
    """Check payment status by ID."""
    if not settings.MERCADOPAGO_ACCESS_TOKEN:
        return {"success": False, "error": "Not configured"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{MP_API}/v1/payments/{payment_id}", headers=_headers())
            data = r.json()
            return {
                "success": True,
                "payment_id": data.get("id"),
                "status": data.get("status"),
                "status_detail": data.get("status_detail"),
                "amount": data.get("transaction_amount"),
                "method": data.get("payment_method_id"),
                "payer_email": data.get("payer", {}).get("email"),
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def process_webhook(payload: dict) -> dict:
    """Process Mercado Pago webhook notification.

    Returns action to take: activate_plan, cancel_plan, etc.
    """
    action_type = payload.get("action")
    data_id = payload.get("data", {}).get("id")
    topic = payload.get("type", payload.get("topic", ""))

    if topic == "payment" and action_type == "payment.created":
        return {"action": "payment_pending", "payment_id": data_id}

    if topic == "payment" and action_type == "payment.updated":
        return {"action": "check_payment", "payment_id": data_id}

    if topic == "subscription_preapproval":
        return {"action": "subscription_update", "subscription_id": data_id}

    return {"action": "unknown", "raw": payload}
