import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.asset import AssetStatus


class AssetOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    uploaded_by: uuid.UUID
    file_path: str
    file_type: str
    file_size: int
    caption: str | None = None
    hashtags: list[str] | None = None
    status: AssetStatus
    rejection_comment: str | None = None
    compliance_score: int | None = None
    compliance_issues: list[dict] | None = None
    thumbnail_path: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssetUpdate(BaseModel):
    caption: str | None = None
    hashtags: list[str] | None = None


class AssetListResponse(BaseModel):
    items: list[AssetOut]
    total: int
    page: int
    size: int


class RejectRequest(BaseModel):
    comment: str
