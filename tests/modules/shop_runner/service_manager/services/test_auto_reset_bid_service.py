"""Regression tests for AutoResetBidService (partial get_min_bids results)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.mp.wb.dto.adv_min_bids import AdvMinNmidsBids
from app.modules.shop_runner.service_manager.services.auto_reset_bid_service import (
    AutoResetBidService,
)


def _make_adv(
    *,
    auto_adv_id: int,
    cpm: int = 900,
    card_ab_hold_mode: str = "off",
) -> MagicMock:
    adv = MagicMock()
    adv.bot_active = True
    adv.bidder_for_auto = True
    adv.nmids = [10]
    adv.auto_adv_id = auto_adv_id
    adv.adv_setting.cpm = cpm
    adv.shop_id = f"shop-{auto_adv_id}"
    adv.card_ab_hold_mode = card_ab_hold_mode
    return adv


async def _run_handlers_inline(
    handlers: Sequence[Callable[[], Awaitable[Any]]],
    **_: Any,
) -> list[Any]:
    return [await h() for h in handlers]


@pytest.mark.asyncio
async def test_ensure_auto_bids_minimum_partial_nmids_in_min_bids_still_resets() -> None:
    """When min_bids lacks some nmids, service uses only available keys and does not crash."""
    hub = MagicMock()
    hub.wb_manager = MagicMock()
    hub.wb_modifier = MagicMock()
    hub.wb_modifier.update_auto_adv_cpm = AsyncMock()

    adv = MagicMock()
    adv.bot_active = True
    adv.bidder_for_auto = True
    adv.nmids = [10, 20]
    adv.auto_adv_id = 501
    adv.adv_setting.cpm = 900
    adv.shop_id = "shop-partial"

    hub.wb_manager.get_min_bids_cache_only = AsyncMock(
        return_value=AdvMinNmidsBids(
            auto={10: 150},
            search={},
        )
    )

    service = AutoResetBidService(hub, MagicMock())

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_reset_bid_service.run_tasks",
        new=_run_handlers_inline,
    ):
        await service.ensure_auto_bids_minimum([adv])

    hub.wb_modifier.update_auto_adv_cpm.assert_awaited_once()
    call = hub.wb_modifier.update_auto_adv_cpm.await_args
    assert call.args[0] == 501
    assert call.args[1] == {10: 150}


@pytest.mark.asyncio
async def test_ensure_auto_bids_minimum_no_matching_nmids_returns_early() -> None:
    hub = MagicMock()
    hub.wb_manager = MagicMock()
    hub.wb_modifier = MagicMock()
    hub.wb_modifier.update_auto_adv_cpm = AsyncMock()

    adv = MagicMock()
    adv.bot_active = True
    adv.bidder_for_auto = True
    adv.nmids = [99, 100]
    adv.auto_adv_id = 502
    adv.adv_setting.cpm = 900

    hub.wb_manager.get_min_bids_cache_only = AsyncMock(
        return_value=AdvMinNmidsBids(auto={10: 50}, search={})
    )

    service = AutoResetBidService(hub, MagicMock())

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_reset_bid_service.run_tasks",
        new=_run_handlers_inline,
    ):
        await service.ensure_auto_bids_minimum([adv])

    hub.wb_modifier.update_auto_adv_cpm.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_auto_bids_minimum_skips_active_ab_hold_adv() -> None:
    """ACTIVE A/B Hold → AutoReset не трогает ставку; OFF — обрабатывается."""
    hub = MagicMock()
    hub.wb_manager = MagicMock()
    hub.wb_modifier = MagicMock()
    hub.wb_modifier.update_auto_adv_cpm = AsyncMock()

    active_hold = _make_adv(auto_adv_id=601, card_ab_hold_mode="active")
    off_adv = _make_adv(auto_adv_id=602, card_ab_hold_mode="off")

    hub.wb_manager.get_min_bids_cache_only = AsyncMock(
        return_value=AdvMinNmidsBids(auto={10: 150}, search={})
    )

    service = AutoResetBidService(hub, MagicMock())

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_reset_bid_service.run_tasks",
        new=_run_handlers_inline,
    ):
        await service.ensure_auto_bids_minimum([active_hold, off_adv])

    get_min_call = hub.wb_manager.get_min_bids_cache_only.await_args
    assert len(get_min_call.args[0]) == 1
    assert get_min_call.args[0][0].auto_adv_id == 602

    hub.wb_modifier.update_auto_adv_cpm.assert_awaited_once()
    call = hub.wb_modifier.update_auto_adv_cpm.await_args
    assert call.args[0] == 602
    assert call.args[1] == {10: 150}


@pytest.mark.asyncio
async def test_ensure_auto_bids_minimum_empty_auto_cache_returns_early() -> None:
    """When Redis has no auto min bids, exit before scheduling resets (truthy AdvMinNmidsBids)."""
    hub = MagicMock()
    hub.wb_manager = MagicMock()
    hub.wb_modifier = MagicMock()
    hub.wb_modifier.update_auto_adv_cpm = AsyncMock()

    adv = MagicMock()
    adv.bot_active = True
    adv.bidder_for_auto = True
    adv.nmids = [10]
    adv.auto_adv_id = 503
    adv.adv_setting.cpm = 900

    hub.wb_manager.get_min_bids_cache_only = AsyncMock(
        return_value=AdvMinNmidsBids(auto={}, search={10: 50})
    )

    service = AutoResetBidService(hub, MagicMock())

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_reset_bid_service.run_tasks",
        new=_run_handlers_inline,
    ):
        await service.ensure_auto_bids_minimum([adv])

    hub.wb_modifier.update_auto_adv_cpm.assert_not_called()
