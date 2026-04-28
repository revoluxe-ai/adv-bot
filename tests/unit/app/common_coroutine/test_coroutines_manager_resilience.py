from __future__ import annotations

import asyncio

import pytest

from app.common_coroutine.corounines_manager.coroutines_manager import (
    CommonCoroutineManager,
)


def _fake_backoff(attempt: int, *, base_seconds: int, max_seconds: int) -> float:
    _ = (base_seconds, max_seconds)
    return float(attempt * 10)


class _FlakyWorker:
    def __init__(self) -> None:
        self.calls = 0

    async def run(self) -> None:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("boom")
        await asyncio.sleep(0)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_common_coroutine_manager_restarts_worker_after_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StopLoop(Exception):
        pass

    worker = _FlakyWorker()
    manager = CommonCoroutineManager([worker])  # type: ignore[arg-type]

    restart_delays: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        if seconds == 0:
            return None
        restart_delays.append(seconds)
        if len(restart_delays) >= 2:
            raise StopLoop()
        return None

    monkeypatch.setattr(
        "app.common_coroutine.corounines_manager.coroutines_manager.exponential_retry_delay_seconds",
        _fake_backoff,
    )
    monkeypatch.setattr("app.common_coroutine.corounines_manager.coroutines_manager.asyncio.sleep", fake_sleep)

    with pytest.raises(StopLoop):
        await manager.run()

    assert worker.calls >= 2
    assert restart_delays == [10.0, 10.0]


class _StopsThenCrashesWorker:
    def __init__(self) -> None:
        self.calls = 0

    async def run(self) -> None:
        self.calls += 1
        if self.calls == 2:
            raise RuntimeError("boom after clean stop")
        await asyncio.sleep(0)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_common_coroutine_manager_resets_crash_backoff_after_clean_stop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StopLoop(Exception):
        pass

    worker = _StopsThenCrashesWorker()
    manager = CommonCoroutineManager([worker])  # type: ignore[arg-type]

    restart_delays: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        if seconds == 0:
            return None
        restart_delays.append(seconds)
        if len(restart_delays) >= 2:
            raise StopLoop()
        return None

    monkeypatch.setattr(
        "app.common_coroutine.corounines_manager.coroutines_manager.exponential_retry_delay_seconds",
        _fake_backoff,
    )
    monkeypatch.setattr(
        "app.common_coroutine.corounines_manager.coroutines_manager.asyncio.sleep",
        fake_sleep,
    )

    with pytest.raises(StopLoop):
        await manager.run()

    assert worker.calls >= 2
    # First restart is after clean stop, second is first crash after that stop.
    assert restart_delays == [10.0, 10.0]
