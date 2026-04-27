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

    restart_sleeps = 0

    async def fake_sleep(seconds: float) -> None:
        nonlocal restart_sleeps
        if seconds == 0:
            return None
        restart_sleeps += 1
        if restart_sleeps >= 2:
            raise StopLoop()
        return None

    monkeypatch.setattr("app.common_coroutine.corounines_manager.coroutines_manager.asyncio.sleep", fake_sleep)

    with pytest.raises(StopLoop):
        await manager.run()

    assert worker.calls >= 2
