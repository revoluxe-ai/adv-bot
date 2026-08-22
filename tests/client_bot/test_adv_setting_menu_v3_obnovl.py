"""Блок «Обновл:» в меню РК: V3 vs V2."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.client_bot.user_interface.views.messages.last_auto_update_informer import (
    LastAutoUpdateSettingInformer,
)
from app.client_bot.user_interface.views.messages.main_adv_setting_menu.adv_setting_menu import (
    AdvSettingMenu,
)
from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy


def _minimal_menu_for_text(
    *,
    bot_active: bool,
    v3_last_action_str: str | None,
) -> AdvSettingMenu:
    menu = AdvSettingMenu.__new__(AdvSettingMenu)
    menu.adv = SimpleNamespace(
        bot_active=bot_active,
        auto_budget_watchdog_enabled=False,
        adv_id=1,
        search_adv_id=None,
        name="Test",
        active_status="9",
        strategy=Strategy.MIN_CPO,
        rec_system_mode=False,
    )
    informer = LastAutoUpdateSettingInformer.__new__(LastAutoUpdateSettingInformer)
    informer.add_to_white_list_str = "10:00:00 01-01-2026"
    informer.delete_from_white_list_str = "Нет данных"
    informer.up_target_place_str = "Нет данных"
    informer.down_target_place_str = "Нет данных"
    informer.update_top_key_str = "Нет данных"
    menu._update_informer = informer
    menu._v3_last_action_str = v3_last_action_str
    menu.last_update_common_stat_str = "н/д"
    menu.full_stat_update_time = "н/д"
    menu.last_update_cluster_stat_str = "н/д"
    menu.keywords_status_last_update_auto_adv = "н/д"
    menu.keywords_status_last_update_search_adv = "н/д"
    menu.last_cluster_bids_update = None
    menu.last_common_bid_update_str = "Н/д"
    menu._emergency_mode_active = False
    menu._stats_fresh = True
    menu._stats_stale_reason = None
    menu._topup_failed = None
    menu._shop_balance_snapshot = None
    menu._last_topup_success = None
    menu._spend_auto_today = None
    menu._spend_search_today = None
    menu._reason_auto = None
    menu._reason_search = None
    menu._status_auction = "—"
    menu._strategy = Strategy.MIN_CPO
    menu._min_orders_per_1000_rub = None
    menu._min_conv_views_to_orders = None
    menu._target_cost = None
    menu._avg_cost_additional = None
    menu._is_campaign_active_by_cost = None
    menu._cost_threshold_kind = None
    menu._plan_set = False
    menu._plan_fact_ch_max_ts_str = None
    menu._traffic_clicks_dto = None
    menu.adv_stat = None
    return menu


def _extract_obnovl_block(menu: AdvSettingMenu) -> str:
    text = menu.text
    start = text.index("Обновл:\n")
    marker = "топ в БС:"
    end = text.index(marker)
    return text[start : text.index("\n", end) + 1]


@pytest.mark.unit
def test_obnovl_v3_shows_last_v3_not_bs() -> None:
    menu = _minimal_menu_for_text(
        bot_active=True,
        v3_last_action_str="UP «kw» MIN_CPA→OPTIMUM 18:32:06 26-05-2026",
    )
    block = _extract_obnovl_block(menu)
    assert "посл. V3:" in block
    assert "MIN_CPA→OPTIMUM" in block
    assert "добавл в БС" not in block
    assert "удал из БС" not in block
    assert "цел.поз +" in block


@pytest.mark.unit
def test_obnovl_v2_shows_bs_not_v3() -> None:
    menu = _minimal_menu_for_text(bot_active=False, v3_last_action_str=None)
    block = _extract_obnovl_block(menu)
    assert "добавл в БС" in block
    assert "удал из БС" in block
    assert "посл. V3" not in block
