from __future__ import annotations

from contextlib import asynccontextmanager
import pytest

from app.modules.wb_adv_updater import runner


@pytest.mark.unit
def test_is_infra_error_detects_dns_resolution_message() -> None:
    exc = RuntimeError("Failed to resolve host: Name or service not known")
    assert runner._is_infra_error(exc) is True


@pytest.mark.unit
def test_calc_backoff_capped_and_monotonic_with_zero_jitter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner.random, "uniform", lambda _a, _b: 0.0)
    first = runner._calc_backoff(attempt=1, base_seconds=5, max_seconds=300)
    second = runner._calc_backoff(attempt=2, base_seconds=5, max_seconds=300)
    capped = runner._calc_backoff(attempt=100, base_seconds=5, max_seconds=300)
    assert first == 5
    assert second == 10
    assert capped == 300


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_payment_for_advs_retries_after_di_bootstrap_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StopLoop(Exception):
        pass

    create_calls = 0
    billing_calls = 0

    @asynccontextmanager
    async def fake_context():
        yield object()

    async def fake_create(_container_cls):  # type: ignore[no-untyped-def]
        nonlocal create_calls
        create_calls += 1
        if create_calls == 1:
            raise RuntimeError("name or service not known")
        return fake_context()

    async def fake_billing(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        nonlocal billing_calls
        billing_calls += 1
        return None

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 2:
            raise StopLoop()
        return None

    monkeypatch.setattr(runner.DIManager, "create", fake_create)
    monkeypatch.setattr("app.modules.billing.process_payment_for_advs", fake_billing)
    monkeypatch.setattr(runner.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(runner.random, "uniform", lambda _a, _b: 0.0)

    with pytest.raises(StopLoop):
        await runner.process_payment_for_advs()

    assert create_calls >= 2
    assert billing_calls == 1
