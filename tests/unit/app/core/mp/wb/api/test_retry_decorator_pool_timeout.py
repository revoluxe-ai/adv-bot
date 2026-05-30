"""Unit-тесты отдельной retry-политики для PoolTimeout в retry_decorator."""

import pytest

from app.core.mp.wb.api.adapter.promotion_client.finance.adapter import FinanceAdapter
from app.core.mp.wb.api.excs import HttpTimeOutError, MaxAttemptsError, PoolTimeoutError
from app.core.mp.wb.api.request_limit_manager import RequestLimitManager
from app.core.mp.wb.api.retry_decorator import (
    POOL_TIMEOUT_MAX_ATTEMPTS,
    retry_decorator,
)


class _FakeAuthHandler:
    shop_id = "shop-test-42"

    async def mark_current_token_invalided(self, *args, **kwargs) -> None:
        return None


def _build_adapter() -> FinanceAdapter:
    return FinanceAdapter(
        base_url="https://advert-api.wildberries.ru",
        auth_client_handler=_FakeAuthHandler(),
        request_limit_manager=RequestLimitManager(),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pool_timeout_not_retried_50_times() -> None:
    adapter = _build_adapter()
    call_count = 0

    @retry_decorator(period=1, limit=100, max_attempts=50, max_delay=120)
    async def flaky_method(self) -> None:
        nonlocal call_count
        call_count += 1
        raise PoolTimeoutError(original_exc=None)

    with pytest.raises(MaxAttemptsError, match="PoolTimeout"):
        await flaky_method(adapter)

    assert call_count == POOL_TIMEOUT_MAX_ATTEMPTS


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pool_timeout_uses_short_retry_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _build_adapter()
    sleeps: list[float] = []

    async def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(
        "app.core.mp.wb.api.retry_decorator.asyncio.sleep",
        record_sleep,
    )

    call_count = 0

    @retry_decorator(period=1, limit=100, max_attempts=50, max_delay=120)
    async def flaky_method(self) -> None:
        nonlocal call_count
        call_count += 1
        raise PoolTimeoutError(original_exc=None)

    with pytest.raises(MaxAttemptsError):
        await flaky_method(adapter)

    assert call_count == POOL_TIMEOUT_MAX_ATTEMPTS
    assert sleeps
    assert max(sleeps) <= 2.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pool_timeout_attempts_independent_of_other_errors() -> None:
    """Счётчик pool-timeout не делит лимит с 429/read timeout и др."""
    adapter = _build_adapter()
    call_count = 0

    @retry_decorator(period=1, limit=100, max_attempts=50, max_delay=120)
    async def flaky_method(self) -> None:
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise HttpTimeOutError("read timeout")
        raise PoolTimeoutError(original_exc=None)

    with pytest.raises(MaxAttemptsError, match="PoolTimeout"):
        await flaky_method(adapter)

    assert call_count == 2 + POOL_TIMEOUT_MAX_ATTEMPTS


@pytest.mark.unit
@pytest.mark.asyncio
async def test_http_timeout_still_uses_max_attempts() -> None:
    adapter = _build_adapter()
    call_count = 0
    max_attempts = 5

    @retry_decorator(
        period=1,
        limit=100,
        max_attempts=max_attempts,
        max_delay=120,
    )
    async def flaky_method(self) -> None:
        nonlocal call_count
        call_count += 1
        raise HttpTimeOutError("read timeout")

    with pytest.raises(MaxAttemptsError, match="Не удалось выполнить"):
        await flaky_method(adapter)

    assert call_count == max_attempts


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unknown_api_error_still_uses_max_attempts() -> None:
    from app.core.mp.wb.api.excs import UnknownApiRequestError

    adapter = _build_adapter()
    call_count = 0
    max_attempts = 4

    @retry_decorator(
        period=1,
        limit=100,
        max_attempts=max_attempts,
        max_delay=120,
    )
    async def flaky_method(self) -> None:
        nonlocal call_count
        call_count += 1
        raise UnknownApiRequestError()

    with pytest.raises(MaxAttemptsError):
        await flaky_method(adapter)

    assert call_count == max_attempts
