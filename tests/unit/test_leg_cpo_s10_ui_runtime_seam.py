"""LEG-CPO-010 / GAP-S10-SEAM: один LegCpoSnapshot → UI Search CPO == runtime Search CPO."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.common_slaves.wildberries.models.models import BidderCoroutineType
from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStat
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.loaders import (
    resolve_v3_fact_data,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.shared.domains.wb.dto.wb_adv_dto import WBAdvDTO
from app.client_bot.user_interface.views.messages.adv_keyword_messages.adv_keyword_messages import (
    AdvKeywordsSetting,
)
from tests.support.leg_cpo_ch_contract import GOLDEN_PAIR_CASE, golden_leg_cpo_snapshot

pytestmark = pytest.mark.unit


def _stat(*, spend: float, orders: int) -> SmallFullAdvStat:
    """Production-shaped stat для UI render helper."""
    return SmallFullAdvStat(
        views=1000,
        clicks=100,
        spend=spend,
        added_to_cart=10,
        orders=orders,
        sum_price=10_000.0,
    )


def _render_search_cpo_from_snapshot(*, snapshot: object) -> str:
    """UI render: Search CPO берётся только из snapshot, без отдельной формулы."""
    search_cpo = getattr(snapshot, "search_cpo")
    auto_cpo = getattr(snapshot, "auto_cpo")
    view = AdvKeywordsSetting.__new__(AdvKeywordsSetting)
    view._keywords = []
    view._on_page = 24
    view._page = 1
    view._only_relevant_phrase_status = ""
    view._status_auction = "started"
    view._adv_setting = type(
        "_Adv",
        (),
        {
            "name": "Leg CPO seam",
            "active_status": "started",
            "strategy": None,
            "bot_active": True,
            "adv_id": GOLDEN_PAIR_CASE.auto_adv_id,
            "search_adv_id": GOLDEN_PAIR_CASE.search_adv_id,
            "orders_source_for_auto_mode": OrdersSourceForAutoMode.ADV_SUM,
            "plan_for_sales_for_day": 10,
            "target_price_for_order": 350,
            "max_price_for_order": 500,
            "bidder_for_auto": False,
            "bidder_coroutine_type": BidderCoroutineType.OLD_UPDATE_CPM_BIDDER,
            "max_place": 10,
        },
    )()
    view.min_orders_per_1000_rub = 1.25
    view.total_spend = 12_345.67
    view.full_adv_stat_for_last_days_for_auto_adv = _stat(
        spend=GOLDEN_PAIR_CASE.auto_spend,
        orders=GOLDEN_PAIR_CASE.auto_orders,
    )
    view.full_adv_stat_for_last_days_for_auction = _stat(
        spend=GOLDEN_PAIR_CASE.search_spend,
        orders=GOLDEN_PAIR_CASE.search_orders,
    )
    view.addition_spend_in_adv = 6000.0
    view.cost_per_order_from_additional_last_week = 250.0
    view.auto_cpo = auto_cpo
    view.search_cpo = search_cpo
    view._all_orders_for_last_days = 55
    view._fact_data = FactData(
        predict_orders=55.0,
        original_orders=55.0,
        pay_for_order=224.47,
        fact_method=FactMethods.DIRECT_SALES,
    )
    view._common_stat_by_days = ""
    view.auto_cpm = 0
    view.auction_cpm = 0
    view._last_saved_bids = {}
    return view.text


@pytest.mark.asyncio
async def test_single_snapshot_drives_search_ui_and_v3_runtime() -> None:
    """Один golden snapshot без второй формулы: UI label == ``search_fact_cpo`` == V3 fact."""
    snapshot = golden_leg_cpo_snapshot(GOLDEN_PAIR_CASE)
    assert snapshot.search_cpo is not None

    adv_setting = MagicMock()
    adv_setting.adv_id = GOLDEN_PAIR_CASE.auto_adv_id
    adv_setting.search_adv_id = GOLDEN_PAIR_CASE.search_adv_id
    adv_setting.plan_for_sales_for_day = 10
    adv_setting.target_price_for_order = 100
    adv_setting.max_price_for_order = 150
    adv_setting.nmids = [777]
    complex_adv = ComplexAdv(adv_setting=adv_setting, search_adv=MagicMock(adv_id=GOLDEN_PAIR_CASE.search_adv_id))
    complex_adv.attach_leg_cpo(snapshot)

    aggregate_fact = FactData(
        pay_for_order=999.0,
        predict_orders=3.0,
        original_orders=3.0,
        fact_method=FactMethods.DIRECT_SALES,
    )
    dto = WBAdvDTO(
        complex_adv=complex_adv,
        plan=PlanData(orders=10, target_pay_for_order=80, max_pay_for_order=100),
        fact=aggregate_fact,
        keywords=[],
        min_bids=MagicMock(search={777: 50}),
    )
    updater = MagicMock()
    updater.get_fact_data = AsyncMock()

    resolved, source = await resolve_v3_fact_data(
        dto=dto,
        updater=updater,
        keywords=[],
        max_last_period=2,
    )

    ui_text = _render_search_cpo_from_snapshot(snapshot=snapshot)
    expected_search_label = f"CPO Search: {snapshot.search_cpo:.2f} р."

    assert complex_adv.search_fact_cpo == snapshot.search_cpo
    assert resolved.pay_for_order == snapshot.search_cpo
    assert source == "dto_search_leg"
    assert expected_search_label in ui_text
    assert resolved.pay_for_order == complex_adv.search_fact_cpo
    assert aggregate_fact.pay_for_order == pytest.approx(999.0)
    updater.get_fact_data.assert_not_awaited()
