import uuid
from collections.abc import AsyncGenerator
from contextvars import ContextVar

from fastapi import Depends
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import ORMExecuteState, Session

from app.core.database import async_session_factory
from app.core.deps import UserContext, get_current_user
from app.models.base import TenantMixin

# Context var holds the current tenant_id for the session event listener
_current_tenant_id: ContextVar[uuid.UUID | None] = ContextVar(
    "_current_tenant_id", default=None
)


@event.listens_for(Session, "do_orm_execute")
def _add_tenant_filter(execute_state: ORMExecuteState):
    """Automatically inject WHERE tenant_id = :tid on SELECT/UPDATE/DELETE
    for any model that inherits TenantMixin."""
    tid = _current_tenant_id.get()
    if tid is None:
        return

    if execute_state.is_select or execute_state.is_update or execute_state.is_delete:
        for mapper in execute_state.all_mappers:
            if issubclass(mapper.class_, TenantMixin):
                execute_state.statement = execute_state.statement.options().filter_by(
                    tenant_id=tid
                )


async def get_tenant_db(
    current_user: UserContext = Depends(get_current_user),
) -> AsyncGenerator[AsyncSession, None]:
    """Yields an AsyncSession that auto-filters by the current user's tenant_id."""
    token = _current_tenant_id.set(current_user.tenant_id)
    try:
        async with async_session_factory() as session:
            yield session
    finally:
        _current_tenant_id.reset(token)
