"""Парные scenario_seam: «Управление ставкой для Авто» vs «в полках».

Spec: openspec/changes/pin-legacy-autobidder-vs-shelf-coexistence/specs/auto-bid-module-coexistence/spec.md

ContractCase sources:
- ``update_cpm_contract`` (legacy Auto / Search WB thin end)
- ``shelf_set_bid_contract`` (полки set_bid / patch)
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
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_setter import (
    AutoShelfBidSetter,
)
from app.modules.shop_runner.service_manager.services.redis_campaign_activity_reason_manager.enums import (
    AutoReasonCode,
)
from app.modules.shop_runner.service_manager.services.redis_campaign_activity_reason_manager.reason_display import (
    reason_code_to_display_text,
)
from tests.factories.keyword_pipeline import make_calculated_keyword
from tests.unit.auto_bid_module_coexistence.shelf_set_bid_contract import (
    SHELF_SET_BID_CASES,
    RecordingPatchAutoAdvBids,
    ShelfSetBidContractCase,
)
from tests.unit.auto_bid_module_coexistence.update_cpm_contract import (
    UPDATE_CPM_CASES,
    RecordingFakeUpdateCpm,
    UpdateCpmContractCase,
)


def _case_update(case_id: str) -> UpdateCpmContractCase:
    for case in UPDATE_CPM_CASES:
        if case.case_id == case_id:
            return case
    raise KeyError(case_id)


def _case_shelf(case_id: str) -> ShelfSetBidContractCase:
    for case in SHELF_SET_BID_CASES:
        if case.case_id == case_id:
            return case
    raise KeyError(case_id)


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


async def _run_legacy_bidder_with_contract(
    monkeypatch: pytest.MonkeyPatch,
    case: UpdateCpmContractCase,
) -> RecordingFakeUpdateCpm:
    """Прогон ``run_bidder_process_for_adv`` с ContractCase flags; recording fake."""
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
            auction_adv = _make_auction_adv(100, case.auto_adv_id, case.nmid)
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

            update_cpm = RecordingFakeUpdateCpm()
            adv_setting = SimpleNamespace(
                adv_id=case.auto_adv_id,
                bidder_for_auto=case.bidder_for_auto,
                auto_shelf_bid_control_enabled=case.shelves_on,
                search_adv_id=case.search_adv_id,
                max_cpm=150,
                nmids=[case.nmid],
                bidder_step=5,
                max_place=10,
                reset_place=False,
                id=2,
            )
            wb_api = SimpleNamespace(
                shop_id=55,
                access=SimpleNamespace(wb_cabinet=SimpleNamespace(id=2000)),
                update_cpm=update_cpm,
            )
            await run_bidder_process_for_adv(adv_setting, wb_api, [best_keyword])
            return update_cpm
        finally:
            stamp_cache_provider.reset_override()
            redis_last_views_provider.reset_override()
            app_container.redis_client_wrapper.reset_override()
            app_container.redis_client.reset_override()
            app_container.settings.reset_override()


@pytest.mark.asyncio
async def test_shelf_on_legacy_auto_bid_path_must_not_update_auto_cpm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec — Scenario: Shelf bid control on — legacy Auto bid path ignored.

    OWNER_LIFECYCLE_ECHO step 3. ContractCase forbidden_auto_shelves_on.
    """
    case = _case_update("forbidden_auto_shelves_on")
    update_cpm = await _run_legacy_bidder_with_contract(monkeypatch, case)
    update_cpm.assert_matches_case(case)


@pytest.mark.asyncio
async def test_shelf_off_legacy_auto_bid_path_may_update_auto_cpm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec — Scenario: Shelf bid control off — legacy Auto bid path may write.

    OWNER_LIFECYCLE_ECHO step 4. ContractCase allowed_auto_shelves_off +
    Positive case when shelf control is off.
    """
    case = _case_update("allowed_auto_shelves_off")
    update_cpm = await _run_legacy_bidder_with_contract(monkeypatch, case)
    update_cpm.assert_matches_case(case)

    complex_adv = SimpleNamespace(auto_shelf_bid_control_enabled=False)
    assert AutoShelfBidControlManager.is_coroutine_candidate(complex_adv) is False


@pytest.mark.asyncio
async def test_search_sibling_ungated_when_shelves_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Search ``update_cpm(search_adv_id)`` не блокируется shelf coexistence gate."""
    case = _case_update("search_sibling_ungated")
    update_cpm = await _run_legacy_bidder_with_contract(monkeypatch, case)
    update_cpm.assert_matches_case(case)


@pytest.mark.asyncio
async def test_shelf_on_both_modules_must_not_both_write_auto_bid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec — Scenario: Both modules must not write together when shelves on.

    OWNER_LIFECYCLE_ECHO steps 2+3: legacy MUST NOT Auto write; shelf MAY write
    через ``AutoShelfBidSetter.set_bid`` (ContractCase shelves_on_may_write).
    """
    legacy_case = _case_update("forbidden_auto_shelves_on")
    update_cpm = await _run_legacy_bidder_with_contract(monkeypatch, legacy_case)
    update_cpm.assert_matches_case(legacy_case)

    shelf_case = _case_shelf("shelves_on_may_write")
    complex_adv = SimpleNamespace(
        auto_shelf_bid_control_enabled=True,
        auto_adv_id=shelf_case.auto_adv_id,
        nmids=[shelf_case.nmid],
    )
    assert AutoShelfBidControlManager.is_coroutine_candidate(complex_adv) is True

    patch_fake = RecordingPatchAutoAdvBids()
    monkeypatch.setenv("AUTO_SHELF_BID_CONTROL_DRY_RUN", "false")
    setter = AutoShelfBidSetter(wb_modifier=patch_fake)
    await setter.set_bid(
        complex_adv,
        bid_minor=shelf_case.bid_minor,
        currency=shelf_case.currency,
    )
    patch_fake.assert_matches_case(shelf_case)


@pytest.mark.asyncio
async def test_shelves_off_shelf_path_must_not_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Paired: полки OFF → candidate False; patch не вызывается без candidate tick."""
    shelf_case = _case_shelf("shelves_off_must_not")
    complex_adv = SimpleNamespace(
        auto_shelf_bid_control_enabled=False,
        auto_adv_id=shelf_case.auto_adv_id,
        nmids=[shelf_case.nmid],
    )
    assert AutoShelfBidControlManager.is_coroutine_candidate(complex_adv) is False
    patch_fake = RecordingPatchAutoAdvBids()
    assert patch_fake.calls == []
    patch_fake.assert_matches_case(shelf_case)


def test_shelf_control_reason_is_not_cost_rule_failed() -> None:
    """Spec — Scenario: Shelf bid action is not labeled as cost_rule_failed.

    OWNER_LIFECYCLE_ECHO step 5: ControlReason / SET_BID_OK ≠ cost_rule_failed.
    """
    shelf_reasons = {
        getattr(ControlReason, name)
        for name in dir(ControlReason)
        if name.isupper() and isinstance(getattr(ControlReason, name), str)
    }
    assert AutoReasonCode.COST_RULE_FAILED.value not in shelf_reasons
    assert ControlReason.SET_BID_OK != AutoReasonCode.COST_RULE_FAILED.value
    assert ControlReason.SET_BID_FAILED != AutoReasonCode.COST_RULE_FAILED.value
    cost_display = reason_code_to_display_text(AutoReasonCode.COST_RULE_FAILED.value)
    assert "себес" in cost_display.lower() or "Прав" in cost_display
    assert cost_display != ControlReason.SET_BID_OK


def test_cost_pause_remains_a_separate_activity_reason() -> None:
    """Spec — Scenario: Cost pause remains a separate activity reason.

    OWNER_LIFECYCLE_ECHO step 5: GIVEN cost_rule_failed → readable as cost,
    not as shelf bid ControlReason.
    """
    code = AutoReasonCode.COST_RULE_FAILED.value
    assert code == "cost_rule_failed"
    display = reason_code_to_display_text(code)
    assert display != ControlReason.SET_BID_OK
    assert display != ControlReason.SET_BID_FAILED
    assert display != ControlReason.BEST_BID_SELECTED
    assert code not in {
        getattr(ControlReason, name)
        for name in dir(ControlReason)
        if name.isupper() and isinstance(getattr(ControlReason, name), str)
    }
