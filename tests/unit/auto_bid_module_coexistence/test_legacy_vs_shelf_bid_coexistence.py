"""Парные тесты coexistence: «Управление ставкой для Авто» vs «в полках».

Spec: openspec/changes/pin-legacy-autobidder-vs-shelf-coexistence/specs/auto-bid-module-coexistence/spec.md

Runtime seams (task 1.1):
- Legacy «для Авто»: ``run_bidder_process_for_adv`` → ``wb_api.update_cpm(auto_adv_id, …)``
  при ``bidder_for_auto`` (app/modules/shop_runner/bidder/bidder_func.py).
- Полки: ``AutoShelfBidControlManager.is_coroutine_candidate`` /
  ``_set_target_bid`` при ``auto_shelf_bid_control_enabled``.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from dependency_injector import providers

from app.core.di import DIManager
from app.core.di.app_container import AppContainer
from app.core.wb_api.data_classes.advs.auction_adv import AuctionAdv
from app.modules.shop_runner.bidder import bidder_func
from app.modules.shop_runner.bidder.bidder_func import run_bidder_process_for_adv
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager import (
    ControlReason,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager import (
    AutoShelfBidControlManager,
)
from app.modules.shop_runner.service_manager.services.redis_campaign_activity_reason_manager.enums import (
    AutoReasonCode,
)
from tests.factories.keyword_pipeline import make_calculated_keyword


def _make_auction_adv(bid: int, advert_id: int, nmid: int) -> AuctionAdv:
    """Минимальный AuctionAdv для bidder path (статус started)."""
    adv_data = {
        "auction_multibids": [{"bid": bid}],
        "status": 9,
        "advertId": advert_id,
        "type": 9,
        "autoParams": {
            "active": {"booster": False, "carousel": False, "recom": False},
            "subject": {"id": 1, "name": "subject"},
            "nms": [nmid],
        },
        "unitedParams": [
            {
                "searchCPM": bid,
                "subject": {"id": 1, "name": "subject"},
                "nms": [nmid],
            }
        ],
        "name": "test",
        "dailyBudget": 1000,
        "startTime": "2025-01-01T00:00:00",
        "endTime": "2025-01-02T00:00:00",
        "createTime": "2025-01-01T00:00:00",
        "changeTime": "2025-01-01T00:00:00",
    }
    return AuctionAdv(adv_data)


async def _run_legacy_bidder_with_flags(
    monkeypatch: pytest.MonkeyPatch,
    *,
    bidder_for_auto: bool,
    auto_shelf_bid_control_enabled: bool,
    search_adv_id: int | None = 444,
) -> AsyncMock:
    """Прогон ``run_bidder_process_for_adv`` с флагами coexistence; возвращает update_cpm mock."""
    monkeypatch.setattr(
        "app.core.di.databases.redis.RedisLifecycle.init",
        AsyncMock(return_value=None),
    )
    di_manager = await DIManager.create(AppContainer)
    async with di_manager as app_container:
        app_container.settings.override(providers.Object(Mock()))
        app_container.redis_client.override(providers.Object(Mock()))
        app_container.redis_client_wrapper.override(providers.Object(Mock()))

        redis_last_views = SimpleNamespace(
            get=AsyncMock(return_value=None), set=AsyncMock()
        )
        redis_last_views_provider = (
            app_container.module_resources.bidder_container.redis_last_total_views
        )
        redis_last_views_provider.override(providers.Object(redis_last_views))

        stamp_cache = SimpleNamespace(
            get=AsyncMock(return_value=None), set=AsyncMock()
        )
        stamp_cache_provider = (
            app_container.module_resources.bidder_container.last_keyword_stamp_timestamp_cache
        )
        stamp_cache_provider.override(providers.Object(stamp_cache))

        class DummyAdvParameterManager:
            async def get_min_cpm(self, _):
                return 1

        monkeypatch.setattr(bidder_func, "AdvParameterManager", DummyAdvParameterManager)

        try:
            auction_adv = _make_auction_adv(100, 333, 701)
            best_keyword = make_calculated_keyword()
            monkeypatch.setattr(
                bidder_func,
                "_update_and_get_advs_from_wb",
                AsyncMock(return_value=[auction_adv]),
            )
            monkeypatch.setattr(
                bidder_func.data_manager,
                "get_best_keyword",
                Mock(return_value=best_keyword),
            )

            adv_setting = SimpleNamespace(
                adv_id=333,
                bidder_for_auto=bidder_for_auto,
                auto_shelf_bid_control_enabled=auto_shelf_bid_control_enabled,
                search_adv_id=search_adv_id,
                max_cpm=150,
                nmids=[701],
                bidder_step=5,
                max_place=10,
                reset_place=False,
                id=2,
            )
            wb_api = SimpleNamespace(
                shop_id=55,
                access=SimpleNamespace(wb_cabinet=SimpleNamespace(id=2000)),
                update_cpm=AsyncMock(),
            )
            await run_bidder_process_for_adv(adv_setting, wb_api, [best_keyword])
            return wb_api.update_cpm
        finally:
            stamp_cache_provider.reset_override()
            redis_last_views_provider.reset_override()
            app_container.redis_client_wrapper.reset_override()
            app_container.redis_client.reset_override()
            app_container.settings.reset_override()


def _auto_update_cpm_calls(update_cpm: AsyncMock) -> list[tuple]:
    """Вызовы update_cpm именно для Auto adv_id=333 (не Search)."""
    return [
        call.args
        for call in update_cpm.await_args_list
        if call.args and call.args[0] == 333
    ]


@pytest.mark.asyncio
async def test_shelf_on_legacy_auto_bid_path_must_not_update_auto_cpm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec auto-bid-module-coexistence — Scenario: Shelf bid control on — legacy Auto bid path ignored.

    Seam: run_bidder_process_for_adv → update_cpm(auto_adv_id). При включённом
    «Управление ставкой в полках» путь «для Авто» MUST NOT успешно писать ставку Авто.
    """
    update_cpm = await _run_legacy_bidder_with_flags(
        monkeypatch,
        bidder_for_auto=True,
        auto_shelf_bid_control_enabled=True,
    )
    assert _auto_update_cpm_calls(update_cpm) == []


@pytest.mark.asyncio
async def test_shelf_off_legacy_auto_bid_path_may_update_auto_cpm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec auto-bid-module-coexistence — Scenario: Shelf bid control off — legacy may write.

    Paired positive: полки выкл + «для Авто» вкл → update_cpm(auto) MAY;
    is_coroutine_candidate полок MUST быть False.
    """
    update_cpm = await _run_legacy_bidder_with_flags(
        monkeypatch,
        bidder_for_auto=True,
        auto_shelf_bid_control_enabled=False,
    )
    assert len(_auto_update_cpm_calls(update_cpm)) == 1

    complex_adv = SimpleNamespace(auto_shelf_bid_control_enabled=False)
    assert AutoShelfBidControlManager.is_coroutine_candidate(complex_adv) is False


@pytest.mark.asyncio
async def test_shelf_on_both_modules_must_not_both_write_auto_bid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec auto-bid-module-coexistence — Scenario: Both modules must not write together when shelves on.

    При полках вкл legacy MUST NOT писать Auto; полки остаются кандидатом на свой path.
    """
    update_cpm = await _run_legacy_bidder_with_flags(
        monkeypatch,
        bidder_for_auto=True,
        auto_shelf_bid_control_enabled=True,
    )
    assert _auto_update_cpm_calls(update_cpm) == []
    complex_adv = SimpleNamespace(auto_shelf_bid_control_enabled=True)
    assert AutoShelfBidControlManager.is_coroutine_candidate(complex_adv) is True


def test_shelf_control_reason_is_not_cost_rule_failed() -> None:
    """Spec auto-bid-module-coexistence — Scenario: Shelf bid action is not labeled as cost_rule_failed.

    ControlReason полок и AutoReasonCode.COST_RULE_FAILED MUST оставаться различимы.
    """
    shelf_reasons = {
        getattr(ControlReason, name)
        for name in dir(ControlReason)
        if name.isupper() and isinstance(getattr(ControlReason, name), str)
    }
    assert AutoReasonCode.COST_RULE_FAILED.value not in shelf_reasons
    assert AutoReasonCode.COST_RULE_FAILED.value == "cost_rule_failed"
    assert AutoReasonCode.COST_RULE_FAILED.value != ControlReason.SET_BID_OK
