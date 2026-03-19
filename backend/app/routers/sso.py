"""SSO/SAML authentication — Okta, Azure AD, Google Workspace.

Enterprise feature: tenants with SSO enabled redirect to their IdP for login.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.tenant import Tenant

logger = logging.getLogger("bluewave.sso")
router = APIRouter(prefix="/auth/sso", tags=["sso"])


@router.get("/login")
async def sso_login(tenant: str, db: AsyncSession = Depends(get_db)):
    """Initiate SSO login. Redirects to the tenant's IdP."""
    result = await db.execute(select(Tenant).where(Tenant.name == tenant))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Tenant not found")
    raise HTTPException(501, "SSO login not yet configured for this tenant. Contact admin to set up SAML/OIDC.")


@router.post("/callback")
async def sso_callback():
    """Handle SAML Response from IdP. Creates/updates user, generates JWT."""
    raise HTTPException(501, "SSO callback handler pending SAML library integration")


@router.get("/metadata")
async def sso_metadata():
    """Return SAML Service Provider metadata XML for IdP configuration."""
    xml = f"""<?xml version="1.0"?>
<EntityDescriptor xmlns="urn:oasis:names:tc:SAML:2.0:metadata"
    entityID="{settings.APP_URL}/api/v1/auth/sso/metadata">
  <SPSSODescriptor AuthnRequestsSigned="false" WantAssertionsSigned="true"
    protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <AssertionConsumerService
      Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
      Location="{settings.APP_URL}/api/v1/auth/sso/callback"
      index="1"/>
  </SPSSODescriptor>
</EntityDescriptor>"""
    return Response(content=xml, media_type="application/xml")
