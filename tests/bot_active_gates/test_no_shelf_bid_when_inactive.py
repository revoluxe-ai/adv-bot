"""Gate: shelf bid setter не вызывается при bot_active=False."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.bot_active_gates.helpers import unwrap_coroutine

pytestmark = [pytest.mark.unit, pytest.mark.bot_active_gates, pytest.mark.asyncio]


async def test_shelf_bid_setter_skipped_when_bot_inactive(
    coroutines_manager_gate: MagicMock,
    inactive_complex_adv: MagicMock,
) -> None:
    """Проверить inactive shelf gate через test-local TasksManager без patch run_tasks."""
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

    await unwrap_coroutine(manager.auto_shelf_bid_control)(manager)

    manager._auto_shelf_bid_control_manager._set_target_bid.assert_not_awaited()
    manager._auto_shelf_bid_control_manager._persist_state_then_set_bid.assert_not_awaited()
