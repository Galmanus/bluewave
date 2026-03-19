"""Tests for app.core.retry — exponential backoff decorator."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.core.retry import RetryExhausted, _compute_delay, RetryConfig, retry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TransientError(Exception):
    """Simulates a transient/retryable failure."""


class PermanentError(Exception):
    """Simulates a non-retryable failure."""


def _make_flaky_sync(fail_times: int, exc: type[Exception] = TransientError):
    """Return a sync callable that fails ``fail_times`` then succeeds."""
    call_count = 0

    def fn() -> str:
        nonlocal call_count
        call_count += 1
        if call_count <= fail_times:
            raise exc(f"fail #{call_count}")
        return "ok"

    fn.call_count = lambda: call_count  # type: ignore[attr-defined]
    return fn


def _make_flaky_async(fail_times: int, exc: type[Exception] = TransientError):
    """Return an async callable that fails ``fail_times`` then succeeds."""
    call_count = 0

    async def fn() -> str:
        nonlocal call_count
        call_count += 1
        if call_count <= fail_times:
            raise exc(f"fail #{call_count}")
        return "ok"

    fn.call_count = lambda: call_count  # type: ignore[attr-defined]
    return fn


# ---------------------------------------------------------------------------
# Async tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_async_success_no_retry():
    """Function succeeds on first call — no retry needed."""

    @retry(max_retries=3, retryable=(TransientError,))
    async def succeed():
        return "hello"

    assert await succeed() == "hello"


@pytest.mark.asyncio
async def test_async_success_after_transient_failures():
    """Function fails twice then succeeds on third attempt."""
    inner = _make_flaky_async(fail_times=2)

    @retry(max_retries=3, base_delay=0.01, retryable=(TransientError,))
    async def wrapper():
        return await inner()

    result = await wrapper()
    assert result == "ok"
    assert inner.call_count() == 3


@pytest.mark.asyncio
async def test_async_retry_exhausted():
    """All retries fail — RetryExhausted is raised."""
    inner = _make_flaky_async(fail_times=10)

    @retry(max_retries=3, base_delay=0.01, retryable=(TransientError,))
    async def wrapper():
        return await inner()

    with pytest.raises(RetryExhausted) as exc_info:
        await wrapper()

    assert exc_info.value.attempts == 3
    assert isinstance(exc_info.value.__cause__, TransientError)


@pytest.mark.asyncio
async def test_async_non_retryable_passes_through():
    """Non-retryable exceptions are raised immediately without retry."""

    call_count = 0

    @retry(max_retries=3, base_delay=0.01, retryable=(TransientError,))
    async def fail_permanent():
        nonlocal call_count
        call_count += 1
        raise PermanentError("fatal")

    with pytest.raises(PermanentError):
        await fail_permanent()

    assert call_count == 1  # no retries attempted


@pytest.mark.asyncio
async def test_async_exponential_delays():
    """Verify asyncio.sleep is called with increasing delays."""
    inner = _make_flaky_async(fail_times=3)

    @retry(max_retries=4, base_delay=1.0, jitter_factor=0.0, retryable=(TransientError,))
    async def wrapper():
        return await inner()

    with patch("app.core.retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await wrapper()

    assert result == "ok"
    assert mock_sleep.call_count == 3
    delays = [call.args[0] for call in mock_sleep.call_args_list]
    # With jitter_factor=0.0: 1.0, 2.0, 4.0
    assert delays == pytest.approx([1.0, 2.0, 4.0])


# ---------------------------------------------------------------------------
# Sync tests
# ---------------------------------------------------------------------------

def test_sync_success_no_retry():
    """Sync function succeeds on first call."""

    @retry(max_retries=3, retryable=(TransientError,))
    def succeed():
        return "hello"

    assert succeed() == "hello"


def test_sync_success_after_transient_failures():
    """Sync function fails once then succeeds."""
    inner = _make_flaky_sync(fail_times=1)

    @retry(max_retries=3, base_delay=0.01, retryable=(TransientError,))
    def wrapper():
        return inner()

    assert wrapper() == "ok"
    assert inner.call_count() == 2


def test_sync_retry_exhausted():
    """Sync: all retries fail — RetryExhausted raised."""
    inner = _make_flaky_sync(fail_times=10)

    @retry(max_retries=2, base_delay=0.01, retryable=(TransientError,))
    def wrapper():
        return inner()

    with pytest.raises(RetryExhausted) as exc_info:
        wrapper()

    assert exc_info.value.attempts == 2
    assert isinstance(exc_info.value.__cause__, TransientError)


def test_sync_non_retryable_passes_through():
    """Sync: non-retryable exception is raised immediately."""
    call_count = 0

    @retry(max_retries=3, base_delay=0.01, retryable=(TransientError,))
    def fail_permanent():
        nonlocal call_count
        call_count += 1
        raise PermanentError("fatal")

    with pytest.raises(PermanentError):
        fail_permanent()

    assert call_count == 1


def test_sync_exponential_delays():
    """Verify time.sleep is called with increasing delays."""
    inner = _make_flaky_sync(fail_times=2)

    @retry(max_retries=3, base_delay=0.5, jitter_factor=0.0, retryable=(TransientError,))
    def wrapper():
        return inner()

    with patch("app.core.retry.time.sleep") as mock_sleep:
        result = wrapper()

    assert result == "ok"
    assert mock_sleep.call_count == 2
    delays = [call.args[0] for call in mock_sleep.call_args_list]
    assert delays == pytest.approx([0.5, 1.0])


# ---------------------------------------------------------------------------
# _compute_delay tests
# ---------------------------------------------------------------------------

def test_compute_delay_exponential():
    """Delays grow exponentially: base * 2^(attempt-1)."""
    config = RetryConfig(base_delay=1.0, jitter_factor=0.0)
    assert _compute_delay(config, 1) == pytest.approx(1.0)
    assert _compute_delay(config, 2) == pytest.approx(2.0)
    assert _compute_delay(config, 3) == pytest.approx(4.0)
    assert _compute_delay(config, 4) == pytest.approx(8.0)


def test_compute_delay_respects_max():
    """Delay is capped at max_delay."""
    config = RetryConfig(base_delay=1.0, max_delay=5.0, jitter_factor=0.0)
    assert _compute_delay(config, 10) == pytest.approx(5.0)


def test_compute_delay_jitter_bounds():
    """With jitter_factor=0.2, delay stays within ±20% of base delay."""
    config = RetryConfig(base_delay=10.0, jitter_factor=0.2)
    for _ in range(200):
        d = _compute_delay(config, 1)
        assert 8.0 <= d <= 12.0  # 10 ± 20%


# ---------------------------------------------------------------------------
# Decorator preserves metadata
# ---------------------------------------------------------------------------

def test_preserves_function_name():
    """@retry preserves __name__ and __qualname__."""

    @retry()
    def my_function():
        pass

    assert my_function.__name__ == "my_function"


@pytest.mark.asyncio
async def test_preserves_async_function_name():
    """@retry preserves __name__ on async functions."""

    @retry()
    async def my_async_function():
        pass

    assert my_async_function.__name__ == "my_async_function"
