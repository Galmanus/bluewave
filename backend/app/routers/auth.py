from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)

import logging
logger = logging.getLogger("bluewave.auth")

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"


def _validate_password_strength(password: str) -> None:
    """Enforce minimum password requirements."""
    errors = []
    if len(password) < 8:
        errors.append("at least 8 characters")
    if not any(c.isupper() for c in password):
        errors.append("at least 1 uppercase letter")
    if not any(c.isdigit() for c in password):
        errors.append("at least 1 number")
    if errors:
        raise HTTPException(
            status_code=400,
            detail=f"Password too weak. Required: {', '.join(errors)}.",
        )


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    _validate_password_strength(body.password)

    # Check if email already taken
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create tenant
    tenant = Tenant(name=body.tenant_name)
    db.add(tenant)
    await db.flush()

    # Create admin user
    user = User(
        tenant_id=tenant.id,
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=UserRole.admin,
    )
    db.add(user)
    await db.commit()
    await db.refresh(tenant)
    await db.refresh(user)

    return RegisterResponse(tenant_id=tenant.id, user_id=user.id)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        logger.warning("Login failed", extra={"email": body.email, "reason": "invalid_credentials"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    logger.info("Login success", extra={"email": body.email, "user_id": str(user.id)})
    access_token = create_access_token(
        str(user.id), str(user.tenant_id), user.role.value
    )
    refresh_token = create_refresh_token(
        str(user.id), str(user.tenant_id), user.role.value
    )

    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        samesite="strict",
        max_age=7 * 24 * 3600,
    )

    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response):
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    payload = decode_token(token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    access_token = create_access_token(
        payload["sub"], payload["tenant_id"], payload["role"]
    )
    new_refresh = create_refresh_token(
        payload["sub"], payload["tenant_id"], payload["role"]
    )

    response.set_cookie(
        key=REFRESH_COOKIE,
        value=new_refresh,
        httponly=True,
        samesite="strict",
        max_age=7 * 24 * 3600,
    )

    return TokenResponse(access_token=access_token)


@router.post("/logout", status_code=204)
async def logout(response: Response):
    response.delete_cookie(REFRESH_COOKIE)
    return None


@router.post("/reset-password-request", status_code=200)
async def request_password_reset(
    body: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Request a password reset. Sends a reset link via email (Resend)."""
    from app.core.security import create_access_token
    from app.services.email_service import send_password_reset

    email = body.get("email", "")
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    # Always return 200 to prevent email enumeration
    if not user:
        return {"message": "If an account with that email exists, a reset link has been sent."}

    # Create a short-lived reset token (15 min)
    reset_token = create_access_token(
        str(user.id), str(user.tenant_id), user.role.value,
    )

    # Send reset email in background (fire-and-forget)
    background_tasks.add_task(send_password_reset, user.email, reset_token, user.full_name)

    return {"message": "If an account with that email exists, a reset link has been sent."}


@router.post("/reset-password", status_code=200)
async def reset_password(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """Reset password using a valid reset token."""
    token = body.get("token", "")
    new_password = body.get("new_password", "")

    if not token or not new_password:
        raise HTTPException(400, "Token and new_password are required")

    if len(new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(401, "Invalid or expired reset token")

    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    user.hashed_password = hash_password(new_password)
    await db.commit()

    return {"message": "Password updated successfully"}
