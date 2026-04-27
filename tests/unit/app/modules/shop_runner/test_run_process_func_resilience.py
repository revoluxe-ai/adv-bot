from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.modules.shop_runner import run_process_func


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_shops_loop_retries_on_unknown_error_without_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StopLoop(Exception):
        pass

    update_mock = AsyncMock(side_effect=[RuntimeError("unexpected"), None])
    sleep_mock = AsyncMock(side_effect=[None, StopLoop()])

    monkeypatch.setattr(run_process_func, "_update_tasks", update_mock)
    monkeypatch.setattr(run_process_func.asyncio, "sleep", sleep_mock)

    with pytest.raises(StopLoop):
        await run_process_func._run_shops_loop(
            tasks_manager=object(),  # type: ignore[arg-type]
            client_session=object(),  # type: ignore[arg-type]
            plan_fact_reader=object(),  # type: ignore[arg-type]
        )

    assert update_mock.await_count >= 2
