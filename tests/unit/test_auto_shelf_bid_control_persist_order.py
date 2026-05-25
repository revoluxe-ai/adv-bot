"""Unit-тест порядка save_state → PATCH при смене фазы цикла."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.common_slaves.wildberries.models.auto_shelf_bid_control import (
    AutoShelfBidControlState,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager import (
    AutoShelfBidControlManager,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_persist_state_then_set_bid_saves_before_patch() -> None:
    """PG фиксирует mode до WB PATCH (контракт test↔main)."""
    call_order: list[str] = []
    repository = MagicMock()
    repository.save_state = AsyncMock(
        side_effect=lambda s: (call_order.append("save"), s)[1]
    )
    setter = MagicMock()
    setter.set_bid = AsyncMock(
        side_effect=lambda *args, **kwargs: call_order.append("patch")
    )
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=setter,
        repository=repository,
    )
    state = AutoShelfBidControlState(
        nmid=1,
        current_mode="test",
        current_main_bid_minor=20_000,
        current_test_bid_minor=31_000,
        currency="RUB",
        current_cycle_started_at=datetime.now(timezone.utc),
    )
    complex_adv = MagicMock()
    complex_adv.nmids = [1]
    complex_adv.auto_adv_id = 99

    await manager._persist_state_then_set_bid(
        complex_adv,
        state=state,
        bid_minor=50_000,
    )

    assert call_order == ["save", "patch"]
    setter.set_bid.assert_awaited_once_with(
        complex_adv,
        bid_minor=50_000,
        currency="RUB",
    )
