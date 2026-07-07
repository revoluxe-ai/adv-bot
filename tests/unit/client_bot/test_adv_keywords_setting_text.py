"""Unit tests for compact diagnostics in the keywords/stat screen."""

from __future__ import annotations

from types import SimpleNamespace

from app.client_bot.user_interface.views.messages.adv_keyword_messages.adv_keyword_messages import (
    AdvKeywordsDiagnosticsView,
    AdvKeywordsSetting,
)
from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.common_slaves.wildberries.models.models import BidderCoroutineType


def _build_setting() -> AdvKeywordsSetting:
    adv_setting = SimpleNamespace(
        name="Кампания",
        active_status="active",
        strategy="strategy-x",
        bot_active=True,
        adv_id=123,
        search_adv_id=456,
        orders_source_for_auto_mode=OrdersSourceForAutoMode.ADV_SUM,
        plan_for_sales_for_day=10,
        target_price_for_order=20,
        max_price_for_order=30,
        bidder_for_auto=True,
        bidder_coroutine_type=BidderCoroutineType.OLD_UPDATE_CPM_BIDDER,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy="PLAN_DISTANCE",
        max_place=7,
    )
    setting = AdvKeywordsSetting(
        bot=SimpleNamespace(),
        chat_id=1,
        keywords=[],
        adv_setting=adv_setting,
        wb_user_cabinet_original_id=10,
        adv_choice_last_page=1,
        image="img",
        page=1,
        diagnostics=AdvKeywordsDiagnosticsView(
            bidder_label="старый",
            auto_shelf_enabled=True,
            strategy_label="PLAN_DISTANCE",
        ),
    )
    setting._status_auction = "active"
    setting.min_orders_per_1000_rub = 1.5
    setting.auto_cpm = 2500
    setting.auction_cpm = 1800
    setting.total_spend = 123.45
    setting.addition_spend_in_adv = 12.34
    setting._all_orders_for_last_days = 8
    setting._mean_orders_for_days = 4
    setting._mean_price_for_order = 27.5
    setting._spend_for_inner_adv_for_3_days = 15.0
    setting.hard_min_ctr = 0.1
    setting.full_adv_stat_for_last_days_for_auto_adv = SimpleNamespace(
        spend=50.0,
        orders=5,
    )
    setting.full_adv_stat_for_last_days_for_auction = SimpleNamespace(
        spend=73.45,
        orders=3,
    )
    setting.common_stat = SimpleNamespace()
    setting.cost_per_order_from_additional_last_week = 33.33
    setting._common_stat_by_days = "Статистика по дням:\n..."
    setting._fact_data = SimpleNamespace(
        method_ru="WB",
        pay_for_order=18.5,
        predict_orders=2.25,
    )
    setting._last_saved_bids = {}
    return setting


def test_adv_keywords_setting_text_includes_compact_partial_diagnostics() -> None:
    setting = _build_setting()

    text = setting.text

    assert "🤖 Биддер: старый · Auto Shelf: вкл" in text
    assert "Режим: PLAN_DISTANCE" in text
    assert "CPO/ставка: недоступно в этом экране" in text
    assert "fallback_possible" not in text
    assert "⚙️ Управление рекламой" not in text
    assert "Общий расход: 123.45" in text
    assert "CPM Авто: 25 р." in text
    assert "Последняя ставка (по артикулам): Нет данных" in text
    assert len(text) < 4000


def test_adv_keywords_setting_text_keeps_legacy_stats_without_diagnostics() -> None:
    setting = _build_setting()
    setting._diagnostics = None

    text = setting.text

    assert "🤖 Биддер:" not in text
    assert "CPO/ставка: недоступно в этом экране" not in text
    assert "Общий расход: 123.45" in text
    assert "Последняя ставка (по артикулам): Нет данных" in text
