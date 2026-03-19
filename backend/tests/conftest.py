"""Global test fixtures: async DB engine, session, test client, factories."""

import json
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, create_engine, text
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# SQLite compatibility: PostgreSQL-specific types -> SQLite equivalents
# MUST be registered before any model / metadata DDL is processed.
# ---------------------------------------------------------------------------
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ARRAY


# --- DDL compilation overrides ---
# When SQLAlchemy renders CREATE TABLE DDL for an SQLite engine, these
# functions tell it what SQL type string to emit instead of the Postgres ones.

@compiles(PG_UUID, "sqlite")
def _compile_pg_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(36)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(type_, compiler, **kw):
    return "TEXT"


# --- Value serialization for SQLite ---
# PG_UUID, ARRAY, and JSONB need custom bind/result processors so that
# Python objects (uuid.UUID, list, dict) are properly stored as strings
# in SQLite and deserialized back.

_original_uuid_bind_processor = PG_UUID.bind_processor
_original_uuid_result_processor = PG_UUID.result_processor


def _uuid_bind_processor(self, dialect):
    if dialect.name == "sqlite":
        def process(value):
            if value is not None:
                return str(value) if isinstance(value, uuid.UUID) else value
            return value
        return process
    return _original_uuid_bind_processor(self, dialect)


def _uuid_result_processor(self, dialect, coltype):
    if dialect.name == "sqlite":
        def process(value):
            if value is not None and not isinstance(value, uuid.UUID):
                return uuid.UUID(str(value))
            return value
        return process
    return _original_uuid_result_processor(self, dialect, coltype)


PG_UUID.bind_processor = _uuid_bind_processor
PG_UUID.result_processor = _uuid_result_processor

_original_array_bind_processor = ARRAY.bind_processor
_original_array_result_processor = ARRAY.result_processor


def _array_bind_processor(self, dialect):
    if dialect.name == "sqlite":
        def process(value):
            if value is not None:
                return json.dumps(value)
            return value
        return process
    return _original_array_bind_processor(self, dialect)


def _array_result_processor(self, dialect, coltype):
    if dialect.name == "sqlite":
        def process(value):
            if value is not None and isinstance(value, str):
                return json.loads(value)
            return value
        return process
    return _original_array_result_processor(self, dialect, coltype)


ARRAY.bind_processor = _array_bind_processor
ARRAY.result_processor = _array_result_processor

_original_jsonb_bind_processor = JSONB.bind_processor
_original_jsonb_result_processor = JSONB.result_processor


def _jsonb_bind_processor(self, dialect):
    if dialect.name == "sqlite":
        def process(value):
            if value is not None and not isinstance(value, str):
                return json.dumps(value)
            return value
        return process
    return _original_jsonb_bind_processor(self, dialect)


def _jsonb_result_processor(self, dialect, coltype):
    if dialect.name == "sqlite":
        def process(value):
            if value is not None and isinstance(value, str):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            return value
        return process
    return _original_jsonb_result_processor(self, dialect, coltype)


JSONB.bind_processor = _jsonb_bind_processor
JSONB.result_processor = _jsonb_result_processor

# ---------------------------------------------------------------------------
# App imports (after type compilation overrides are registered)
# ---------------------------------------------------------------------------
from app.core.config import settings
from app.core.deps import UserContext, get_current_user
from app.core.security import create_access_token, hash_password
from app.core.tenant import _current_tenant_id, get_tenant_db
from app.models import Base
from app.models.ai_usage import AIActionType, AIUsageLog
from app.models.api_key import APIKey
from app.models.asset import AssetStatus, MediaAsset
from app.models.brand_guideline import BrandGuideline
from app.models.subscription import PlanTier, TenantSubscription
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.models.webhook import Webhook

# ---------------------------------------------------------------------------
# In-memory SQLite async engine for tests
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def engine():
    eng = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


# ---------------------------------------------------------------------------
# Pre-built tenant + users
# ---------------------------------------------------------------------------

@pytest.fixture
async def tenant(db_session: AsyncSession) -> Tenant:
    t = Tenant(name="Test Corp")
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


@pytest.fixture
async def admin_user(db_session: AsyncSession, tenant: Tenant) -> User:
    u = User(
        tenant_id=tenant.id,
        email="admin@test.com",
        hashed_password=hash_password("Admin123"),
        full_name="Admin User",
        role=UserRole.admin,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture
async def editor_user(db_session: AsyncSession, tenant: Tenant) -> User:
    u = User(
        tenant_id=tenant.id,
        email="editor@test.com",
        hashed_password=hash_password("Editor123"),
        full_name="Editor User",
        role=UserRole.editor,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture
async def viewer_user(db_session: AsyncSession, tenant: Tenant) -> User:
    u = User(
        tenant_id=tenant.id,
        email="viewer@test.com",
        hashed_password=hash_password("Viewer123"),
        full_name="Viewer User",
        role=UserRole.viewer,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


# ---------------------------------------------------------------------------
# Second tenant for isolation tests
# ---------------------------------------------------------------------------

@pytest.fixture
async def tenant_b(db_session: AsyncSession) -> Tenant:
    t = Tenant(name="Other Corp")
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


@pytest.fixture
async def admin_b(db_session: AsyncSession, tenant_b: Tenant) -> User:
    u = User(
        tenant_id=tenant_b.id,
        email="admin_b@test.com",
        hashed_password=hash_password("Admin123"),
        full_name="Admin B",
        role=UserRole.admin,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def make_token(user: User) -> str:
    return create_access_token(str(user.id), str(user.tenant_id), user.role.value)


def auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(user)}"}


@pytest.fixture
def admin_headers(admin_user: User) -> dict[str, str]:
    return auth_headers(admin_user)


@pytest.fixture
def editor_headers(editor_user: User) -> dict[str, str]:
    return auth_headers(editor_user)


@pytest.fixture
def viewer_headers(viewer_user: User) -> dict[str, str]:
    return auth_headers(viewer_user)


@pytest.fixture
def admin_b_headers(admin_b: User) -> dict[str, str]:
    return auth_headers(admin_b)


# ---------------------------------------------------------------------------
# Test client with dependency overrides
# ---------------------------------------------------------------------------

@pytest.fixture
async def client(engine, db_session: AsyncSession, admin_user: User, tenant: Tenant) -> AsyncGenerator[AsyncClient, None]:
    """HTTPX AsyncClient wired to the test database."""
    from app.core.database import get_db
    from app.main import app

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    async def override_get_tenant_db(
        current_user: UserContext = None,
    ):
        """Tenant-scoped session for tests.

        Unlike production, we set the tenant context var directly
        since SQLite doesn't support the same event listener approach.
        """
        token = _current_tenant_id.set(
            current_user.tenant_id if current_user else tenant.id
        )
        try:
            async with session_factory() as session:
                yield session
        finally:
            _current_tenant_id.reset(token)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_tenant_db] = override_get_tenant_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Asset factory
# ---------------------------------------------------------------------------

@pytest.fixture
async def draft_asset(db_session: AsyncSession, tenant: Tenant, admin_user: User) -> MediaAsset:
    a = MediaAsset(
        tenant_id=tenant.id,
        uploaded_by=admin_user.id,
        file_path="/app/uploads/test/test.jpg",
        file_type="image/jpeg",
        file_size=1024,
        status=AssetStatus.draft,
        caption="Test caption",
        hashtags=["#test"],
    )
    db_session.add(a)
    await db_session.commit()
    await db_session.refresh(a)
    return a


@pytest.fixture
async def pending_asset(db_session: AsyncSession, tenant: Tenant, admin_user: User) -> MediaAsset:
    a = MediaAsset(
        tenant_id=tenant.id,
        uploaded_by=admin_user.id,
        file_path="/app/uploads/test/pending.jpg",
        file_type="image/jpeg",
        file_size=2048,
        status=AssetStatus.pending_approval,
        caption="Pending caption",
        hashtags=["#pending"],
    )
    db_session.add(a)
    await db_session.commit()
    await db_session.refresh(a)
    return a


@pytest.fixture
async def approved_asset(db_session: AsyncSession, tenant: Tenant, admin_user: User) -> MediaAsset:
    a = MediaAsset(
        tenant_id=tenant.id,
        uploaded_by=admin_user.id,
        file_path="/app/uploads/test/approved.jpg",
        file_type="image/jpeg",
        file_size=4096,
        status=AssetStatus.approved,
        caption="Approved caption",
        hashtags=["#approved"],
        compliance_score=95,
    )
    db_session.add(a)
    await db_session.commit()
    await db_session.refresh(a)
    return a


# ---------------------------------------------------------------------------
# Webhook + API Key factories
# ---------------------------------------------------------------------------

@pytest.fixture
async def webhook(db_session: AsyncSession, tenant: Tenant) -> Webhook:
    wh = Webhook(
        tenant_id=tenant.id,
        name="Test Webhook",
        url="https://example.com/webhook",
        secret="test-secret",
        events="*",
        is_active=True,
    )
    db_session.add(wh)
    await db_session.commit()
    await db_session.refresh(wh)
    return wh


@pytest.fixture
async def brand_guideline(db_session: AsyncSession, tenant: Tenant) -> BrandGuideline:
    bg = BrandGuideline(
        tenant_id=tenant.id,
        primary_colors=["#2563EB", "#1E40AF"],
        secondary_colors=["#F59E0B"],
        fonts=["Inter", "Roboto"],
        tone_description="Professional, friendly, and concise",
        dos=["Use active voice", "Be inclusive"],
        donts=["Don't use jargon", "Avoid passive voice"],
        is_active=True,
    )
    db_session.add(bg)
    await db_session.commit()
    await db_session.refresh(bg)
    return bg
