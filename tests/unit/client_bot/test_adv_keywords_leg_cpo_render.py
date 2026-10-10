"""UI regression для leg-cpo-economics на paid keyword/campaign экране."""

from __future__ import annotations

from app.client_bot.const import TELEGRAM_CAPTION_LIMIT
from app.client_bot.user_interface.views.messages.adv_keyword_messages.adv_keyword_messages import (
    AdvKeywordsSetting,
)
from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.common_slaves.wildberries.models.models import BidderCoroutineType
from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStat
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
)
from tests.helpers.telegram_message_asserts import (
    assert_html_is_telegram_safe,
    assert_no_raw_technical_text,
)


def _stat(*, spend: float, orders: int) -> SmallFullAdvStat:
    """Создать production-shaped stat для одной рекламной ноги."""
    return SmallFullAdvStat(
        views=1000,
        clicks=100,
        spend=spend,
        added_to_cart=10,
        orders=orders,
        sum_price=10_000.0,
    )

def _render(*, auto_cpo: float | None, search_cpo: float | None) -> str:
    """Собрать text без Telegram/DB I/O, сохранив production field semantics."""
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
            "name": "Кампания " + ("ОченьДлинноеИмя🚀" * 45),
            "active_status": "started",
            "strategy": None,
            "bot_active": True,
            "adv_id": 123456789,
            "search_adv_id": 987654321,
            "orders_source_for_auto_mode": OrdersSourceForAutoMode.ADV_SUM,
            "plan_for_sales_for_day": 100,
            "target_price_for_order": 350,
            "max_price_for_order": 500,
            "bidder_for_auto": False,
            "bidder_coroutine_type": BidderCoroutineType.OLD_UPDATE_CPM_BIDDER,
            "max_place": 10,
        },
    )()
    view.min_orders_per_1000_rub = 1.25
    view.total_spend = 12_345.67
    view.full_adv_stat_for_last_days_for_auto_adv = _stat(spend=9000.0, orders=30)
    view.full_adv_stat_for_last_days_for_auction = _stat(spend=3345.67, orders=20)
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


def test_paid_keyword_ui_shows_auto_and_search_cpo_separately() -> None:
    """Оба leg CPO видны как разные значения и caption остаётся Telegram-safe."""
    text = _render(auto_cpo=300.0, search_cpo=100.0)

    assert "CPO Auto: 300.00 р." in text
    assert "CPO Search: 100.00 р." in text
    head, _overflow = AdvKeywordsSetting._split_caption(text)
    assert len(head) <= TELEGRAM_CAPTION_LIMIT
    assert_html_is_telegram_safe(head)
    assert_no_raw_technical_text(head)


def test_paid_keyword_ui_missing_search_cpo_has_no_neighbor_fallback() -> None:
    """Missing Search отображается как unavailable, а Auto остаётся своим."""
    text = _render(auto_cpo=300.0, search_cpo=None)

    assert "CPO Auto: 300.00 р." in text
    assert "CPO Search: нет данных" in text
