import uuid
from datetime import datetime

from pydantic import BaseModel


class BrandGuidelineCreate(BaseModel):
    primary_colors: list[str] | None = None
    secondary_colors: list[str] | None = None
    fonts: list[str] | None = None
    tone_description: str | None = None
    dos: list[str] | None = None
    donts: list[str] | None = None
    custom_rules: dict | None = None


class BrandGuidelineOut(BaseModel):
    id: uuid.UUID
    primary_colors: list[str] | None
    secondary_colors: list[str] | None
    fonts: list[str] | None
    logo_urls: list[str] | None
    tone_description: str | None
    dos: list[str] | None
    donts: list[str] | None
    custom_rules: dict | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ComplianceIssueOut(BaseModel):
    severity: str
    category: str
    message: str
    suggestion: str


class ComplianceResultOut(BaseModel):
    score: int
    passed: bool
    summary: str
    issues: list[ComplianceIssueOut]
