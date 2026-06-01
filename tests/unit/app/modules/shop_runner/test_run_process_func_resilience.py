from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_runner import run_process_func


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_tasks_removes_failed_shop_before_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failed done() tasks must be popped before re-raise so outer retry loop
    does not see the same stuck entry forever."""

    async def boom() -> None:
        raise RuntimeError("shop failed")

    failed = asyncio.create_task(boom())
    await asyncio.wait({failed})
    assert failed.done()

    shop_id = "shop-a"
    active_tasks: dict[str, asyncio.Task[None]] = {shop_id: failed}

    session_cm = AsyncMock()
    session = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None

    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = [shop_id]
    session.execute = AsyncMock(return_value=execute_result)

    monkeypatch.setattr(run_process_func, "sm", lambda **_: session_cm)

    with pytest.raises(RuntimeError, match="shop failed"):
        await run_process_func._update_tasks(
            active_tasks,
            client_session=AsyncMock(),
            redis_manager=AsyncMock(),
            tasks_manager=AsyncMock(),
            plan_fact_reader=AsyncMock(),
        )

    assert shop_id not in active_tasks


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
