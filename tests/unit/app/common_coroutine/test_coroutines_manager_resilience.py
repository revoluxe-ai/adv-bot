from __future__ import annotations

import asyncio

import pytest

from app.common_coroutine.corounines_manager.coroutines_manager import (
    CommonCoroutineManager,
)


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
        lambda attempt, *, base_seconds, max_seconds: float(attempt * 10),
    )
    monkeypatch.setattr("app.common_coroutine.corounines_manager.coroutines_manager.asyncio.sleep", fake_sleep)

    with pytest.raises(StopLoop):
        await manager.run()

    assert worker.calls >= 2
    assert restart_delays == [10.0, 20.0]
