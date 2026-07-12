"""Gate: shelf bid setter не вызывается при bot_active=False."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.bot_active_gates.helpers import unwrap_coroutine

pytestmark = [pytest.mark.unit, pytest.mark.bot_active_gates, pytest.mark.asyncio]


async def _run_handlers(
    handlers: list[Callable[[], Awaitable[Any]]],
    **_: object,
) -> list[None]:
    for handler in handlers:
        await handler()
    return [None] * len(handlers)


async def test_shelf_bid_setter_skipped_when_bot_inactive(
    coroutines_manager_gate: MagicMock,
    inactive_complex_adv: MagicMock,
) -> None:
    manager = coroutines_manager_gate
    manager._wb_shop_data_manager.get_complex_advs = AsyncMock(
        return_value=[inactive_complex_adv]
    )
    manager._wb_shop_data_manager.attach_min_nmids_bids = AsyncMock()
    manager._auto_shelf_bid_control_manager._set_target_bid = AsyncMock()
    manager._auto_shelf_bid_control_manager._persist_state_then_set_bid = AsyncMock()
    manager._auto_shelf_bid_control_manager.update = AsyncMock(
        wraps=manager._auto_shelf_bid_control_manager.update
    )

    import app.modules.shop_runner.service_manager.manager as manager_module

    original_run_tasks = manager_module.run_tasks
    manager_module.run_tasks = _run_handlers
    try:
        await unwrap_coroutine(manager.auto_shelf_bid_control)(manager)
    finally:
        manager_module.run_tasks = original_run_tasks

    manager._auto_shelf_bid_control_manager._set_target_bid.assert_not_awaited()
    manager._auto_shelf_bid_control_manager._persist_state_then_set_bid.assert_not_awaited()
