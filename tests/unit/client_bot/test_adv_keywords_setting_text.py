"""Unit tests for compact diagnostics in the keywords/stat screen."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.client_bot.user_interface.handlers.keyword_settings import (
    _build_adv_keywords_diagnostics_view_model,
    load_adv_keywords_diagnostics_view,
)
from app.client_bot.user_interface.views.messages.adv_keyword_messages.adv_keyword_messages import (
    AdvKeywordsDiagnosticsView,
    AdvKeywordsSetting,
    format_adv_keywords_diagnostics_block,
)
from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.common_slaves.wildberries.models.models import BidderCoroutineType
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_diagnostics_cache import (
    AutoShelfBidDiagnosticsCacheManager,
    AutoShelfBidDiagnosticsDTO,
)


class _FakeRedisClient:
    def __init__(self, payload: str | None = None) -> None:
        self._payload = payload
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        if key in self.store:
            return self.store[key]
        if key != "auto_shelf:diagnostics:123":
            return None
        return self._payload

    async def set(
        self,
        key: str,
        value: str,
        ex: int | None = None,
        px: int | None = None,
        nx: bool | None = None,
    ) -> bool:
        self.store[key] = value
        return True


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
            bid="123",
            cpo="45.67",
            last_update_ts="07.07 13:00",
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


@pytest.mark.asyncio
async def test_diagnostics_view_reads_cached_auto_shelf_values() -> None:
    adv_setting = SimpleNamespace(
        id=123,
        bidder_for_auto=True,
        bidder_coroutine_type=BidderCoroutineType.OLD_UPDATE_CPM_BIDDER,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy="PLAN_DISTANCE",
    )
    payload = AutoShelfBidDiagnosticsDTO(
        best_cpo_bid_rub=123.0,
        current_bid_rub=123.0,
        expected_bid_rub=123.0,
        selected_cpo_rub=45.67,
        updated_at=datetime(2026, 7, 7, 13, 0, tzinfo=UTC),
        source="source",
    ).model_dump_json()

    diagnostics = await load_adv_keywords_diagnostics_view(
        adv_setting, redis_client=_FakeRedisClient(payload)
    )

    assert diagnostics.bid == "123"
    assert diagnostics.cpo == "45.67"
    assert diagnostics.last_update_ts == "07.07 16:00"


@pytest.mark.asyncio
async def test_diagnostics_cache_round_trip_returns_text() -> None:
    redis_client = _FakeRedisClient()
    cache = AutoShelfBidDiagnosticsCacheManager(redis_client)  # type: ignore[arg-type]
    await cache.set(
        123,
        AutoShelfBidDiagnosticsDTO(
            best_cpo_bid_rub=None,
            current_bid_rub=None,
            expected_bid_rub=None,
            selected_cpo_rub=None,
            updated_at=None,
            source="source",
        ),
    )

    adv_setting = SimpleNamespace(
        id=123,
        bidder_for_auto=True,
        bidder_coroutine_type=BidderCoroutineType.OLD_UPDATE_CPM_BIDDER,
        auto_shelf_bid_control_enabled=True,
        auto_shelf_bid_control_strategy="PLAN_DISTANCE",
    )
    diagnostics = await load_adv_keywords_diagnostics_view(
        adv_setting,
        redis_client=redis_client,  # type: ignore[arg-type]
    )
    text = format_adv_keywords_diagnostics_block(diagnostics)

    assert "🤖 Биддер: старый · Auto Shelf: вкл" in text
    assert "Ставка/CPO/время: н/д" in text
    assert text.endswith("\n")


def test_adv_keywords_setting_text_includes_compact_partial_diagnostics() -> None:
    setting = _build_setting()

    text = setting.text

    assert "🤖 Биддер: старый · Auto Shelf: вкл" in text
    assert "Режим: PLAN_DISTANCE" in text
    assert "Ставка: 123 · CPO: 45.67 · (07.07 13:00)" in text
    assert "fallback_possible" not in text
    assert "⚙️ Управление рекламой" not in text
    assert "CPM Авто: 25 р." in text
    assert "Последняя ставка (по артикулам): Нет данных" in text
    assert len(text) < 4000


def test_adv_keywords_setting_text_keeps_legacy_stats_without_diagnostics() -> None:
    setting = _build_setting()
    setting._diagnostics = None

    text = setting.text

    assert "🤖 Биддер:" not in text
    assert "Ставка/CPO/время: н/д" not in text
    assert "Последняя ставка (по артикулам): Нет данных" in text


def test_adv_keywords_setting_text_shows_overall_nd_when_diagnostics_missing() -> None:
    setting = _build_setting()
    setting._diagnostics = AdvKeywordsDiagnosticsView(
        bidder_label="старый",
        auto_shelf_enabled=True,
        strategy_label="PLAN_DISTANCE",
    )

    text = setting.text

    assert "🤖 Биддер: старый · Auto Shelf: вкл" in text
    assert "Ставка/CPO/время: н/д" in text


def test_adv_keywords_setting_text_renders_explicit_cpo_semantics() -> None:
    diagnostics = AdvKeywordsDiagnosticsView(
        bidder_label="старый",
        auto_shelf_enabled=True,
        strategy_label="PLAN_DISTANCE",
        best_cpo_bid_rub="123",
        current_bid_rub="120",
        expected_bid_rub="125",
        selected_cpo_rub=None,
        unavailable_reason="selected_bid_not_applied",
    )

    text = format_adv_keywords_diagnostics_block(diagnostics)

    assert "Лучшая ставка по CPO: 123" in text
    assert "Текущая ставка WB: 120" in text
    assert "Целевая ставка бота: 125" in text
    assert "Примечание: selected_bid_not_applied" in text
    assert "синхрониз" not in text
    assert "safe" not in text
    assert "Ставка: 123" not in text


def test_adv_keywords_setting_text_renders_available_contract_without_note() -> None:
    diagnostics = AdvKeywordsDiagnosticsView(
        bidder_label="старый",
        auto_shelf_enabled=True,
        strategy_label="PLAN_DISTANCE",
        best_cpo_bid_rub="123",
        current_bid_rub="123",
        expected_bid_rub="123",
        selected_cpo_rub="45.67",
    )

    text = format_adv_keywords_diagnostics_block(diagnostics)

    assert "Лучшая ставка по CPO: 123" in text
    assert "Текущая ставка WB: 123" in text
    assert "Целевая ставка бота: 123" in text
    assert "Примечание:" not in text


def test_diagnostics_view_model_formats_cached_values() -> None:
    diagnostics = _build_adv_keywords_diagnostics_view_model(
        bidder_label="старый",
        auto_shelf_enabled=True,
        strategy_label="PLAN_DISTANCE",
        cache_value=SimpleNamespace(
            best_cpo_bid_rub=123.0,
            current_bid_rub=120.0,
            expected_bid_rub=123.0,
            selected_cpo_rub=45.67,
            unavailable_reason="selected_bid_not_applied",
            updated_at=datetime(2026, 7, 7, 13, 0, tzinfo=UTC),
        ),
    )

    assert diagnostics.bid == "123"
    assert diagnostics.best_cpo_bid_rub == "123"
    assert diagnostics.current_bid_rub == "120"
    assert diagnostics.expected_bid_rub == "123"
    assert diagnostics.cpo == "45.67"
    assert diagnostics.selected_cpo_rub == "45.67"
    assert diagnostics.unavailable_reason == "selected_bid_not_applied"
    assert diagnostics.last_update_ts == "07.07 16:00"
    text = format_adv_keywords_diagnostics_block(diagnostics)
    assert "Лучшая ставка по CPO: 123" in text
    assert "Текущая ставка WB: 120" in text
    assert "Целевая ставка бота: 123" in text
    assert "Примечание: selected_bid_not_applied" in text
