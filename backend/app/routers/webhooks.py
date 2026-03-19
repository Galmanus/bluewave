import uuid

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UserContext, require_role
from app.core.tenant import get_tenant_db
from app.models.webhook import Webhook

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookCreate(BaseModel):
    name: str
    url: str
    secret: str | None = None
    events: str = "*"


class WebhookOut(BaseModel):
    id: uuid.UUID
    name: str
    url: str
    events: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    secret: str | None = None
    events: str | None = None
    is_active: bool | None = None


@router.get("", response_model=list[WebhookOut])
async def list_webhooks(
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(select(Webhook))
    return result.scalars().all()


@router.post("", response_model=WebhookOut, status_code=201)
async def create_webhook(
    body: WebhookCreate,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    wh = Webhook(
        tenant_id=current_user.tenant_id,
        name=body.name,
        url=body.url,
        secret=body.secret,
        events=body.events,
        is_active=True,
    )
    db.add(wh)
    await db.commit()
    await db.refresh(wh)
    return wh


@router.patch("/{webhook_id}", response_model=WebhookOut)
async def update_webhook(
    webhook_id: uuid.UUID,
    body: WebhookUpdate,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(select(Webhook).where(Webhook.id == webhook_id))
    wh = result.scalar_one_or_none()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")

    if body.name is not None:
        wh.name = body.name
    if body.url is not None:
        wh.url = body.url
    if body.secret is not None:
        wh.secret = body.secret
    if body.events is not None:
        wh.events = body.events
    if body.is_active is not None:
        wh.is_active = body.is_active

    await db.commit()
    await db.refresh(wh)
    return wh


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: uuid.UUID,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(select(Webhook).where(Webhook.id == webhook_id))
    wh = result.scalar_one_or_none()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await db.delete(wh)
    await db.commit()
    return None
