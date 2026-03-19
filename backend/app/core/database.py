from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Use a SQLite fallback URL when DATABASE_URL is empty (e.g. during tests).
# Tests override get_db / get_tenant_db anyway, so the engine is never used.
_url = settings.DATABASE_URL or "sqlite+aiosqlite:///:memory:"

_engine_kwargs: dict = {}
if _url.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs.update(
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

engine = create_async_engine(_url, echo=False, **_engine_kwargs)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
