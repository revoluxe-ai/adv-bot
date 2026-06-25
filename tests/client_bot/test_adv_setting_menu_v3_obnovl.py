"""Блок «Обновл:» в меню РК: V3 vs V2."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.client_bot.ui_access import UiAccessMode
from app.client_bot.user_interface.views.messages.last_auto_update_informer import (
    LastAutoUpdateSettingInformer,
)
from app.client_bot.user_interface.views.messages.main_adv_setting_menu.adv_setting_menu import (
    AdvSettingMenu,
)
from app.client_bot.user_interface.views.messages.main_adv_setting_menu.keyboard.keyboard import (
    get_adv_setting_keyboard,
)
from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy
from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.common_slaves.wildberries.models.models import BidderCoroutineType
from tests.helpers.telegram_message_asserts import (
    assert_caption_within_telegram_limit,
    assert_html_is_telegram_safe,
    assert_keyboard_has_buttons,
    assert_message_contains_required_phrases,
    assert_no_raw_technical_text,
)


def _minimal_menu_for_text(
    *,
    automatic_version: int,
    v3_last_action_str: str | None,
) -> AdvSettingMenu:
    menu = AdvSettingMenu.__new__(AdvSettingMenu)
    menu.adv = SimpleNamespace(
        automatic_version=automatic_version,
        auto_budget_watchdog_enabled=False,
        bot_active=False,
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


def _build_keyboard_adv() -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        adv_id=101,
        bot_active=False,
        individual_keywords_target_place_mode=False,
        use_incremental_stats=False,
        updater_common_bid_in_search_adv_active_status=False,
        auto_budget_watchdog_enabled=False,
        bidder_coroutine_type=BidderCoroutineType.OLD_UPDATE_CPM_BIDDER,
        auto_update_target_place=False,
        auto_add_only_relevant_phrase=False,
        orders_source_for_auto_mode=OrdersSourceForAutoMode.ADV_SUM,
        sales_predict_method=FactMethods.DIRECT_SALES,
        automatic_version=3,
        search_adv_id=202,
        rec_system_mode=False,
        keyword_calibration_max_step=4,
        aggressiveness=2,
        plan_for_sales_for_day=None,
        target_price_for_order=None,
        max_price_for_order=None,
    )


@pytest.mark.unit
def test_obnovl_v3_shows_last_v3_not_bs() -> None:
    menu = _minimal_menu_for_text(
        automatic_version=3,
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
    menu = _minimal_menu_for_text(automatic_version=2, v3_last_action_str=None)
    block = _extract_obnovl_block(menu)
    assert "добавл в БС" in block
    assert "удал из БС" in block
    assert "посл. V3" not in block


@pytest.mark.unit
def test_campaign_menu_free_copy_is_clear_and_safe() -> None:
    menu = _minimal_menu_for_text(automatic_version=3, v3_last_action_str="Нет данных")
    text = menu.text
    keyboard = get_adv_setting_keyboard(
        wb_user_cabinet=SimpleNamespace(id=55),
        adv_setting=_build_keyboard_adv(),
        in_favorites=False,
        ui_access=UiAccessMode.FREE,
    )

    assert_caption_within_telegram_limit(text)
    assert_html_is_telegram_safe(text)
    assert_message_contains_required_phrases(
        text,
        [
            "меню рекламной кампании",
            "free-режиме",
            "ручные действия",
            "Excel",
            "автоуправление",
            "подключаются отдельно",
        ],
    )
    assert_no_raw_technical_text(text)
    assert_keyboard_has_buttons(
        keyboard,
        [
            "Управление ставкой",
            "Изменить ставку в Авто",
            "Выгрузить ключи в csv-файл",
        ],
    )
