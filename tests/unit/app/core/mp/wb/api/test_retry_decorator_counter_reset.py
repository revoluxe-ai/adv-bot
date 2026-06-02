"""Unit-тесты корректного сброса счётчиков в retry_decorator между вызовами.

Bug-fix: _pool_timeout_attempts и _attempts сбрасываются в начале каждого
нового вызова wrapper, не только на success. Это устраняет накопление
pool_timeout_attempts=44/72/66 между вызовами при лимите 3.
"""

from __future__ import annotations

import pytest

from app.core.mp.wb.api.adapter.promotion_client.finance.adapter import FinanceAdapter
from app.core.mp.wb.api.excs import (
    HttpTimeOutError,
    MaxAttemptsError,
    PoolTimeoutError,
)
from app.core.mp.wb.api.request_limit_manager import RequestLimitManager
from app.core.mp.wb.api.retry_decorator import (
    POOL_TIMEOUT_MAX_ATTEMPTS,
    retry_decorator,
)


def _build_adapter() -> FinanceAdapter:
    return FinanceAdapter(
        base_url="https://advert-api.wildberries.ru",
        auth_client_handler=_FakeAuthHandler(),
        request_limit_manager=RequestLimitManager(),
    )


class _FakeAuthHandler:
    shop_id = "shop-reset-test"

    async def mark_current_token_invalided(self, *args: object, **kwargs: object) -> None:
        return None


@pytest.fixture(autouse=True)
def _no_real_retry_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Юнит-тесты счётчиков не ждут backoff (2/4/8… с и PT pause 2 с)."""

    async def fake_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("app.core.mp.wb.api.retry_decorator.asyncio.sleep", fake_sleep)


# ---------------------------------------------------------------------------
# Основные тесты сброса счётчика pool timeout
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pool_timeout_counter_resets_on_second_call() -> None:
    """Второй вызов начинает _pool_timeout_attempts с 0, а не с остатка первого."""
    adapter = _build_adapter()
    call_counts: list[int] = []

    @retry_decorator(period=1, limit=100, max_attempts=50, max_delay=120)
    async def flaky(self: FinanceAdapter) -> None:
        call_counts.append(len(call_counts))
        raise PoolTimeoutError(original_exc=None)

    # Первый вызов: exhausts 3 попытки → MaxAttemptsError
    with pytest.raises(MaxAttemptsError, match="PoolTimeout"):
        await flaky(adapter)

    first_call_count = len(call_counts)
    assert first_call_count == POOL_TIMEOUT_MAX_ATTEMPTS

    # Второй вызов: должен снова получить 3 попытки, не 0
    with pytest.raises(MaxAttemptsError, match="PoolTimeout"):
        await flaky(adapter)

    second_call_count = len(call_counts) - first_call_count
    assert second_call_count == POOL_TIMEOUT_MAX_ATTEMPTS, (
        f"Second call got {second_call_count} attempts instead of {POOL_TIMEOUT_MAX_ATTEMPTS}. "
        "Counter was not reset between calls."
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pool_timeout_counter_resets_after_success() -> None:
    """После успешного вызова счётчик PT сброшен для следующего вызова."""
    adapter = _build_adapter()
    call_count = 0

    @retry_decorator(period=1, limit=100, max_attempts=50, max_delay=120)
    async def succeed_then_fail(self: FinanceAdapter) -> None:
        nonlocal call_count
        call_count += 1
        # Первый decorated call — сразу успех
        if call_count == 1:
            return None
        # Второй decorated call — всегда PT
        raise PoolTimeoutError(original_exc=None)

    # Первый вызов: success
    await succeed_then_fail(adapter)
    assert call_count == 1

    reset_at = call_count
    # Второй вызов должен дать POOL_TIMEOUT_MAX_ATTEMPTS попыток, не меньше
    with pytest.raises(MaxAttemptsError, match="PoolTimeout"):
        await succeed_then_fail(adapter)

    attempts_in_second_call = call_count - reset_at
    assert attempts_in_second_call == POOL_TIMEOUT_MAX_ATTEMPTS, (
        f"After success, second call got {attempts_in_second_call} attempts "
        f"instead of {POOL_TIMEOUT_MAX_ATTEMPTS}."
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_general_attempts_counter_resets_between_calls() -> None:
    """_attempts (429 / read timeout) сбрасывается между вызовами."""
    adapter = _build_adapter()
    max_attempts = 3
    call_count = 0

    @retry_decorator(period=1, limit=100, max_attempts=max_attempts, max_delay=120)
    async def always_http_timeout(self: FinanceAdapter) -> None:
        nonlocal call_count
        call_count += 1
        raise HttpTimeOutError("always")

    # Первый вызов: max_attempts попыток → exhausted
    with pytest.raises(MaxAttemptsError):
        await always_http_timeout(adapter)

    assert call_count == max_attempts

    reset_at = call_count

    # Второй вызов: должен снова получить max_attempts попыток
    with pytest.raises(MaxAttemptsError):
        await always_http_timeout(adapter)

    second_attempts = call_count - reset_at
    assert second_attempts == max_attempts, (
        f"Second call got {second_attempts} attempts instead of {max_attempts}. "
        "_attempts counter was not reset."
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pool_timeout_counter_independent_of_calls_on_different_adapters() -> None:
    """Разные экземпляры адаптера имеют изолированные счётчики (через RequestLimitManager)."""
    adapter_a = _build_adapter()
    adapter_b = _build_adapter()

    call_counts = {"a": 0, "b": 0}

    @retry_decorator(period=1, limit=100, max_attempts=50, max_delay=120)
    async def always_pt(self: FinanceAdapter) -> None:
        if self is adapter_a:
            call_counts["a"] += 1
        else:
            call_counts["b"] += 1
        raise PoolTimeoutError(original_exc=None)

    with pytest.raises(MaxAttemptsError):
        await always_pt(adapter_a)

    with pytest.raises(MaxAttemptsError):
        await always_pt(adapter_b)

    assert call_counts["a"] == POOL_TIMEOUT_MAX_ATTEMPTS
    assert call_counts["b"] == POOL_TIMEOUT_MAX_ATTEMPTS


# ---------------------------------------------------------------------------
# Регрессионные тесты: существующая политика 429/read/connect не сломана
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pool_timeout_still_capped_at_three_within_single_call() -> None:
    """В рамках одного вызова по-прежнему не более POOL_TIMEOUT_MAX_ATTEMPTS попыток."""
    adapter = _build_adapter()
    call_count = 0

    @retry_decorator(period=1, limit=100, max_attempts=50, max_delay=120)
    async def always_pt(self: FinanceAdapter) -> None:
        nonlocal call_count
        call_count += 1
        raise PoolTimeoutError(original_exc=None)

    with pytest.raises(MaxAttemptsError, match="PoolTimeout"):
        await always_pt(adapter)

    assert call_count == POOL_TIMEOUT_MAX_ATTEMPTS


@pytest.mark.unit
@pytest.mark.asyncio
async def test_success_clears_state_and_next_call_gets_full_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """success → reset state; следующий вызов получает полный rate-limit budget."""
    adapter = _build_adapter()
    sleeps: list[float] = []

    async def fake_sleep(sec: float) -> None:
        sleeps.append(sec)

    monkeypatch.setattr("app.core.mp.wb.api.retry_decorator.asyncio.sleep", fake_sleep)

    call_count = 0

    @retry_decorator(period=1, limit=100, max_attempts=50, max_delay=120)
    async def succeed(self: FinanceAdapter) -> str:
        nonlocal call_count
        call_count += 1
        return "ok"

    await succeed(adapter)
    await succeed(adapter)

    assert call_count == 2
    # Максимальный sleep не должен превышать period/limit (пауза rate-limit),
    # никаких pool-timeout backoff (2.0) не должно быть между успешными вызовами.
    assert all(s <= 0.02 for s in sleeps), f"Unexpected large sleep after success: {sleeps}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_http_timeout_policy_unaffected() -> None:
    """read/connect timeout по-прежнему использует max_attempts, не POOL_TIMEOUT_MAX_ATTEMPTS."""
    adapter = _build_adapter()

    max_attempts = 5
    call_count = 0

    @retry_decorator(period=1, limit=100, max_attempts=max_attempts, max_delay=120)
    async def always_http_timeout(self: FinanceAdapter) -> None:
        nonlocal call_count
        call_count += 1
        raise HttpTimeOutError("timeout")

    with pytest.raises(MaxAttemptsError):
        await always_http_timeout(adapter)

    assert call_count == max_attempts
    assert call_count != POOL_TIMEOUT_MAX_ATTEMPTS, (
        "HttpTimeOutError должен использовать max_attempts, а не pool limit"
    )
