"""Paid regression: shelf control tick планируется для active adv."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.bot_active_gates.helpers import unwrap_coroutine

pytestmark = [pytest.mark.unit, pytest.mark.paid_regression, pytest.mark.asyncio]


async def test_shelf_bid_control_scheduled_when_bot_active(
    coroutines_manager_paid: MagicMock,
    active_complex_adv: MagicMock,
) -> None:
    manager = coroutines_manager_paid
    manager._wb_shop_data_manager.get_complex_advs = AsyncMock(
        return_value=[active_complex_adv]
    )
    manager._wb_shop_data_manager.attach_min_nmids_bids = AsyncMock()
    manager._auto_shelf_bid_control_manager.update = AsyncMock(return_value=None)

    with patch(
        "app.modules.shop_runner.service_manager.manager.run_tasks",
        new=AsyncMock(return_value=[None]),
    ) as run_tasks_mock:
        await unwrap_coroutine(manager.auto_shelf_bid_control)(manager)

    run_tasks_mock.assert_awaited_once()
    handlers = run_tasks_mock.await_args.kwargs.get("handlers") or run_tasks_mock.await_args.args[0]
    assert len(handlers) == 1
