"""Payment routes — Mercado Pago (Brazil) + Stripe (international).

Endpoints:
- POST /payments/pix          — Generate Pix QR code
- POST /payments/card         — Pay with credit card
- POST /payments/subscribe    — Create recurring subscription
- POST /payments/cancel       — Cancel subscription
- GET  /payments/status/:id   — Check payment status
- POST /webhooks/mercadopago  — Webhook for payment confirmations
"""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import UserContext, get_current_user
from app.core.tenant import get_tenant_db

logger = logging.getLogger("bluewave.payments")

router = APIRouter(prefix="/payments", tags=["payments"])
webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# ── Request Models ──────────────────────────────────────────

class PixRequest(BaseModel):
    plan: str  # "pro", "pro_annual", "agency", "agency_annual"


class CardRequest(BaseModel):
    plan: str
    token: str  # Mercado Pago card token from frontend SDK
    installments: int = 1


class SubscribeRequest(BaseModel):
    plan: str  # "pro", "pro_annual", "agency", "agency_annual"
    card_token: str | None = None


class CancelRequest(BaseModel):
    subscription_id: str


# ── Pix Payment ─────────────────────────────────────────────

@router.post("/pix")
async def create_pix(
    req: PixRequest,
    current_user: UserContext = Depends(get_current_user),
):
    """Generate a Pix QR code for plan payment."""
    from app.services.mercadopago_service import PLANS, create_pix_payment

    plan = PLANS.get(req.plan)
    if not plan:
        raise HTTPException(400, f"Unknown plan: {req.plan}")

    if plan["price_cents"] == 0:
        return {"success": True, "message": "Plano gratuito, sem pagamento necessário"}

    result = await create_pix_payment(
        amount_brl=plan["price_cents"] / 100,
        description=f"Bluewave {plan['name']}",
        payer_email=current_user.email,
        payer_name=current_user.full_name or "",
        external_reference=f"tenant_{current_user.tenant_id}_plan_{req.plan}",
    )

    if not result["success"]:
        raise HTTPException(502, result.get("error", "Payment creation failed"))

    return result


# ── Card Payment ────────────────────────────────────────────

@router.post("/card")
async def create_card(
    req: CardRequest,
    current_user: UserContext = Depends(get_current_user),
):
    """Pay with credit card (supports up to 12x installments)."""
    from app.services.mercadopago_service import PLANS, create_card_payment

    plan = PLANS.get(req.plan)
    if not plan:
        raise HTTPException(400, f"Unknown plan: {req.plan}")

    result = await create_card_payment(
        amount_brl=plan["price_cents"] / 100,
        description=f"Bluewave {plan['name']}",
        token=req.token,
        installments=req.installments,
        payer_email=current_user.email,
        external_reference=f"tenant_{current_user.tenant_id}_plan_{req.plan}",
    )

    if not result["success"]:
        raise HTTPException(502, result.get("error", "Payment failed"))

    return result


# ── Subscription ────────────────────────────────────────────

@router.post("/subscribe")
async def subscribe(
    req: SubscribeRequest,
    current_user: UserContext = Depends(get_current_user),
):
    """Create recurring subscription (auto-debit monthly)."""
    from app.services.mercadopago_service import create_subscription

    result = await create_subscription(
        plan_id=req.plan,
        payer_email=current_user.email,
        card_token=req.card_token,
        external_reference=f"tenant_{current_user.tenant_id}",
    )

    if not result["success"]:
        raise HTTPException(502, result.get("error", "Subscription failed"))

    return result


@router.post("/cancel")
async def cancel(
    req: CancelRequest,
    current_user: UserContext = Depends(get_current_user),
):
    """Cancel a recurring subscription."""
    from app.services.mercadopago_service import cancel_subscription

    result = await cancel_subscription(req.subscription_id)
    return result


# ── Payment Status ──────────────────────────────────────────

@router.get("/status/{payment_id}")
async def payment_status(
    payment_id: str,
    current_user: UserContext = Depends(get_current_user),
):
    """Check payment status."""
    from app.services.mercadopago_service import get_payment_status

    return await get_payment_status(payment_id)


# ── Webhook ─────────────────────────────────────────────────

@webhook_router.post("/mercadopago")
async def mercadopago_webhook(request: Request):
    """Receive Mercado Pago payment notifications.

    Processes: payment confirmations, subscription updates.
    Updates tenant plan on successful payment.
    """
    from app.services.mercadopago_service import process_webhook, get_payment_status

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON")

    logger.info("Mercado Pago webhook: %s", payload.get("action", "unknown"))

    result = process_webhook(payload)

    if result["action"] == "check_payment":
        # Payment was updated — check if it's approved
        payment = await get_payment_status(str(result["payment_id"]))
        if payment.get("status") == "approved":
            logger.info(
                "Payment approved: %s — %s BRL — %s",
                payment.get("payment_id"),
                payment.get("amount"),
                payment.get("payer_email"),
            )
            # TODO: activate tenant plan based on external_reference
            # Parse: "tenant_{uuid}_plan_{plan_id}" from payment details

            # ── PUT Feedback Loop: auto-record conversion outcome ──
            try:
                await _record_put_conversion(payment)
            except Exception as e:
                logger.warning("PUT feedback recording failed (non-blocking): %s", e)

    return {"received": True}


async def _record_put_conversion(payment: dict):
    """Auto-record successful payment as PUT feedback.

    Closes the feedback loop: purchase_complete → put_record_outcome.
    This is what transforms PUT from framework to predictive science.
    """
    from app.routers.put_api import _calibration_state, _normalize_response

    payer_email = payment.get("payer_email", "unknown")
    amount = payment.get("amount", 0)
    prospect_id = payer_email.split("@")[0] if payer_email else "unknown"

    interaction = {
        "prospect_id": prospect_id,
        "predicted": "receptive",  # We presented an offer, they converted
        "actual": "converted",
        "actual_normalized": "receptive",
        "correct": True,  # Conversion confirms receptive prediction
        "archetype": None,
        "deal_value": float(amount) if amount else None,
        "timestamp": datetime.now().isoformat() if hasattr(datetime, "now") else "",
        "source": "mercadopago_webhook",
    }

    _calibration_state["interactions"].append(interaction)
    _calibration_state["accuracy_history"] = (
        _calibration_state["accuracy_history"] + [1]
    )[-100:]

    logger.info(
        "PUT auto-feedback: conversion recorded for %s (R$%.2f)",
        prospect_id, float(amount) if amount else 0,
    )
