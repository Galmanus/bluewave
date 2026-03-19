import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UserContext, require_role
from app.core.tenant import get_tenant_db
from app.models.automation import Automation, AutomationLog, AutomationTrigger

router = APIRouter(prefix="/automations", tags=["automations"])


class AutomationCreate(BaseModel):
    name: str
    description: str | None = None
    trigger_type: AutomationTrigger
    conditions: list[dict] = []
    actions: list[dict] = []


class AutomationOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    trigger_type: str
    conditions: list
    actions: list
    is_active: bool
    run_count: int
    last_run_at: datetime | None
    created_at: datetime
    model_config = {"from_attributes": True}


class AutomationUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    conditions: list[dict] | None = None
    actions: list[dict] | None = None


class AutomationLogOut(BaseModel):
    id: uuid.UUID
    automation_id: uuid.UUID
    asset_id: uuid.UUID | None
    trigger_type: str
    actions_executed: list
    status: str
    error_message: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


# Pre-built templates
TEMPLATES = [
    {
        "name": "Social Media Fast Track",
        "description": "Auto-submit images for approval after upload + compliance check",
        "trigger_type": "asset_uploaded",
        "conditions": [{"field": "file_type", "operator": "starts_with", "value": "image/"}],
        "actions": [
            {"type": "run_compliance", "config": {}},
            {"type": "auto_submit", "config": {}},
        ],
    },
    {
        "name": "Compliance Gate",
        "description": "Auto-approve assets that score 90+ on compliance, auto-reject below 50",
        "trigger_type": "asset_submitted",
        "conditions": [],
        "actions": [
            {"type": "run_compliance", "config": {}},
            {"type": "auto_approve", "config": {"min_compliance_score": 90}},
            {"type": "auto_reject", "config": {"max_compliance_score": 50}},
        ],
    },
    {
        "name": "Webhook Notify on Approval",
        "description": "Send webhook notification when any asset is approved",
        "trigger_type": "asset_approved",
        "conditions": [],
        "actions": [{"type": "notify_webhook", "config": {}}],
    },
    {
        "name": "Auto-Submit All Uploads",
        "description": "Immediately submit every uploaded asset for approval",
        "trigger_type": "asset_uploaded",
        "conditions": [],
        "actions": [{"type": "auto_submit", "config": {}}],
    },
]


@router.get("", response_model=list[AutomationOut])
async def list_automations(
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(select(Automation))
    return result.scalars().all()


@router.get("/templates")
async def get_templates(
    current_user: UserContext = Depends(require_role("admin")),
):
    return TEMPLATES


@router.post("", response_model=AutomationOut, status_code=201)
async def create_automation(
    body: AutomationCreate,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    auto = Automation(
        tenant_id=current_user.tenant_id,
        name=body.name,
        description=body.description,
        trigger_type=body.trigger_type,
        conditions=body.conditions,
        actions=body.actions,
        is_active=True,
    )
    db.add(auto)
    await db.commit()
    await db.refresh(auto)
    return auto


@router.patch("/{automation_id}", response_model=AutomationOut)
async def update_automation(
    automation_id: uuid.UUID,
    body: AutomationUpdate,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(select(Automation).where(Automation.id == automation_id))
    auto = result.scalar_one_or_none()
    if not auto:
        raise HTTPException(status_code=404, detail="Automation not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(auto, field, value)

    await db.commit()
    await db.refresh(auto)
    return auto


@router.post("/{automation_id}/toggle", response_model=AutomationOut)
async def toggle_automation(
    automation_id: uuid.UUID,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(select(Automation).where(Automation.id == automation_id))
    auto = result.scalar_one_or_none()
    if not auto:
        raise HTTPException(status_code=404, detail="Automation not found")
    auto.is_active = not auto.is_active
    await db.commit()
    await db.refresh(auto)
    return auto


@router.delete("/{automation_id}", status_code=204)
async def delete_automation(
    automation_id: uuid.UUID,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(select(Automation).where(Automation.id == automation_id))
    auto = result.scalar_one_or_none()
    if not auto:
        raise HTTPException(status_code=404, detail="Automation not found")
    await db.delete(auto)
    await db.commit()
    return None


@router.get("/{automation_id}/logs", response_model=list[AutomationLogOut])
async def get_automation_logs(
    automation_id: uuid.UUID,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(
        select(AutomationLog)
        .where(AutomationLog.automation_id == automation_id)
        .order_by(desc(AutomationLog.created_at))
        .limit(50)
    )
    return result.scalars().all()
