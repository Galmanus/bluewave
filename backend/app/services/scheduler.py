"""Background scheduler — publishes scheduled posts when their time arrives.

Started on app startup. Checks every 60 seconds for posts due for publishing.
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("bluewave.scheduler")

_task: asyncio.Task | None = None


async def _publish_due_posts() -> None:
    """Find and publish all scheduled posts whose time has arrived."""
    from app.core.database import async_session_factory
    from app.models.scheduled_post import PostStatus, ScheduledPost
    from app.services.social_publish_service import publish_scheduled_post

    try:
        async with async_session_factory() as db:
            now = datetime.now(timezone.utc)
            result = await db.execute(
                select(ScheduledPost.id).where(
                    ScheduledPost.scheduled_at <= now,
                    ScheduledPost.status == PostStatus.scheduled,
                )
            )
            post_ids = [r[0] for r in result.all()]

        for post_id in post_ids:
            try:
                await publish_scheduled_post(post_id)
            except Exception:
                logger.exception("Failed to publish post %s", post_id)

        if post_ids:
            logger.info("Published %d scheduled posts", len(post_ids))

    except Exception:
        logger.exception("Scheduler cycle failed")


async def _scheduler_loop() -> None:
    """Main scheduler loop — runs every 60 seconds."""
    logger.info("Post scheduler started")
    while True:
        await asyncio.sleep(60)
        await _publish_due_posts()


def start_scheduler() -> None:
    """Start the scheduler as a background task. Call from app startup."""
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_scheduler_loop())
        logger.info("Scheduler task created")


def stop_scheduler() -> None:
    """Stop the scheduler. Call from app shutdown."""
    global _task
    if _task and not _task.done():
        _task.cancel()
        logger.info("Scheduler task cancelled")
