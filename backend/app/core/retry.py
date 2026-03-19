"""Retry decorator with exponential backoff and jitter.

Provides a universal ``@retry`` decorator that works with both sync and async
callables.  Designed to protect external service calls (AI APIs, webhooks)
and background tasks against transient failures.

Usage::

    from app.core.retry import retry, RetryExhausted

    @retry(max_retries=3, base_delay=1.0, retryable=(httpx.TransportError,))
    async def call_ai_api(...):
        ...
"""

from __future__ import annotations

import asyncio
import dataclasses
import functools
import logging
import random
import time
import sys
from typing import Callable, Tuple, Type, TypeVar

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

logger = logging.getLogger("bluewave.retry")

P = ParamSpec("P")
T = TypeVar("T")


class RetryExhausted(Exception):
    """All retry attempts failed."""

    def __init__(self, message: str, *, attempts: int = 0) -> None:
        super().__init__(message)
        self.attempts = attempts


@dataclasses.dataclass(frozen=True)
class RetryConfig:
    """Immutable configuration for retry behaviour."""

    max_retries: int = 3
    base_delay: float = 0.5  # seconds
    max_delay: float = 30.0  # ceiling in seconds
    jitter_factor: float = 0.2  # ±20 %
    retryable: Tuple[Type[BaseException], ...] = (Exception,)


def _compute_delay(config: RetryConfig, attempt: int) -> float:
    """Return the sleep duration for a given attempt (1-indexed)."""
    delay = min(config.base_delay * (2 ** (attempt - 1)), config.max_delay)
    jitter = random.uniform(-config.jitter_factor, config.jitter_factor) * delay
    return max(0.0, delay + jitter)


def retry(
    *,
    max_retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 30.0,
    jitter_factor: float = 0.2,
    retryable: Tuple[Type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator that retries a callable with exponential backoff.

    Automatically detects whether the wrapped function is sync or async
    and uses the appropriate sleep mechanism.

    Parameters
    ----------
    max_retries:
        Total number of attempts (including the first call).
    base_delay:
        Initial delay in seconds before the first retry.
    max_delay:
        Upper bound on the delay between retries.
    jitter_factor:
        Random jitter applied as ± percentage of the computed delay.
    retryable:
        Tuple of exception types that should trigger a retry.
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        jitter_factor=jitter_factor,
        retryable=retryable,
    )

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:  # type: ignore[return-value]
                last_exc: BaseException | None = None
                for attempt in range(1, config.max_retries + 1):
                    try:
                        return await func(*args, **kwargs)  # type: ignore[misc]
                    except config.retryable as exc:
                        last_exc = exc
                        if attempt == config.max_retries:
                            break
                        wait = _compute_delay(config, attempt)
                        logger.warning(
                            "Retry %d/%d for %s after %.2fs: %s",
                            attempt,
                            config.max_retries,
                            func.__qualname__,
                            wait,
                            exc,
                        )
                        await asyncio.sleep(wait)
                raise RetryExhausted(
                    f"{func.__qualname__} failed after {config.max_retries} attempts",
                    attempts=config.max_retries,
                ) from last_exc

            return async_wrapper  # type: ignore[return-value]

        else:

            @functools.wraps(func)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                last_exc: BaseException | None = None
                for attempt in range(1, config.max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except config.retryable as exc:
                        last_exc = exc
                        if attempt == config.max_retries:
                            break
                        wait = _compute_delay(config, attempt)
                        logger.warning(
                            "Retry %d/%d for %s after %.2fs: %s",
                            attempt,
                            config.max_retries,
                            func.__qualname__,
                            wait,
                            exc,
                        )
                        time.sleep(wait)
                raise RetryExhausted(
                    f"{func.__qualname__} failed after {config.max_retries} attempts",
                    attempts=config.max_retries,
                ) from last_exc

            return sync_wrapper  # type: ignore[return-value]

    return decorator
