from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_setter import (
    AutoShelfBidControlWriteBlockedError,
    AutoShelfBidSetter,
)


pytestmark = pytest.mark.unit


def _build_adv() -> SimpleNamespace:
    return SimpleNamespace(
        auto_adv_id=12345,
        nmids=[111],
        bot_active=True,
        auto_shelf_bid_control_enabled=True,
    )


def test_to_api_bid_identity() -> None:
    assert AutoShelfBidSetter.to_api_bid(7000) == 7000
    assert AutoShelfBidSetter.to_api_bid(150) == 150


@pytest.mark.asyncio
async def test_set_bid_dry_run_skips_wb_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTO_SHELF_BID_CONTROL_DRY_RUN", "true")
    wb_modifier = MagicMock()
    wb_modifier.patch_auto_adv_bids_kopecks = AsyncMock()
    setter = AutoShelfBidSetter(wb_modifier=wb_modifier)

    await setter.set_bid(_build_adv(), bid_minor=7000, currency="RUB")

    wb_modifier.patch_auto_adv_bids_kopecks.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_bid_calls_v1_bids_when_not_dry_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTO_SHELF_BID_CONTROL_DRY_RUN", "false")
    wb_modifier = MagicMock()
    wb_modifier.patch_auto_adv_bids_kopecks = AsyncMock()
    setter = AutoShelfBidSetter(wb_modifier=wb_modifier)

    await setter.set_bid(_build_adv(), bid_minor=7000, currency="RUB")

    wb_modifier.patch_auto_adv_bids_kopecks.assert_awaited_once_with(
        12345, {111: 7000}
    )


@pytest.mark.asyncio
async def test_set_bid_updates_redis_cache_after_patch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTO_SHELF_BID_CONTROL_DRY_RUN", "false")
    wb_modifier = MagicMock()
    wb_modifier.patch_auto_adv_bids_kopecks = AsyncMock()
    bid_cache = MagicMock()
    bid_cache.set_bids = AsyncMock()
    setter = AutoShelfBidSetter(
        wb_modifier=wb_modifier,
        bid_cache_manager=bid_cache,
    )

    await setter.set_bid(_build_adv(), bid_minor=7000, currency="RUB")

    bid_cache.set_bids.assert_awaited_once_with(12345, {111: 7000})


@pytest.mark.asyncio
async def test_set_bid_dry_run_skips_redis_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTO_SHELF_BID_CONTROL_DRY_RUN", "true")
    wb_modifier = MagicMock()
    wb_modifier.patch_auto_adv_bids_kopecks = AsyncMock()
    bid_cache = MagicMock()
    bid_cache.set_bids = AsyncMock()
    setter = AutoShelfBidSetter(
        wb_modifier=wb_modifier,
        bid_cache_manager=bid_cache,
    )

    await setter.set_bid(_build_adv(), bid_minor=7000, currency="RUB")

    bid_cache.set_bids.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_bid_blocks_wb_patch_when_bot_inactive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTO_SHELF_BID_CONTROL_DRY_RUN", "false")
    wb_modifier = MagicMock()
    wb_modifier.patch_auto_adv_bids_kopecks = AsyncMock()
    bid_cache = MagicMock()
    bid_cache.set_bids = AsyncMock()
    setter = AutoShelfBidSetter(
        wb_modifier=wb_modifier,
        bid_cache_manager=bid_cache,
    )
    adv = _build_adv()
    adv.bot_active = False

    with pytest.raises(AutoShelfBidControlWriteBlockedError):
        await setter.set_bid(adv, bid_minor=7000, currency="RUB")

    wb_modifier.patch_auto_adv_bids_kopecks.assert_not_awaited()
    bid_cache.set_bids.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_bid_skips_wb_patch_when_module_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTO_SHELF_BID_CONTROL_DRY_RUN", "false")
    wb_modifier = MagicMock()
    wb_modifier.patch_auto_adv_bids_kopecks = AsyncMock()
    bid_cache = MagicMock()
    bid_cache.set_bids = AsyncMock()
    setter = AutoShelfBidSetter(
        wb_modifier=wb_modifier,
        bid_cache_manager=bid_cache,
    )
    adv = _build_adv()
    adv.auto_shelf_bid_control_enabled = False

    await setter.set_bid(adv, bid_minor=7000, currency="RUB")

    wb_modifier.patch_auto_adv_bids_kopecks.assert_not_awaited()
    bid_cache.set_bids.assert_not_awaited()
