"""Unit tests for campaign menu freemium keyboard rendering."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.client_bot.ui_access import UiAccessMode
from app.client_bot.user_interface.views import callbacks
from app.client_bot.user_interface.views.messages.main_adv_setting_menu.adv_setting_menu import (
    AdvSettingMenu,
)
from app.client_bot.user_interface.views.messages.main_adv_setting_menu.keyboard.keyboard import (
    get_adv_setting_keyboard,
)
from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.common_slaves.wildberries.models.models import BidderCoroutineType


def _build_adv(*, bot_active: bool) -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        adv_id=101,
        bot_active=bot_active,
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


def _button_texts(markup: object) -> list[str]:
    rows = getattr(markup, "inline_keyboard")
    return [button.text for row in rows for button in row]


def _first_button_callback(markup: object) -> str:
    rows = getattr(markup, "inline_keyboard")
    return rows[0][0].callback_data


@pytest.mark.unit
def test_free_keyboard_keeps_manual_buttons_and_hides_autopilot_controls() -> None:
    markup = get_adv_setting_keyboard(
        wb_user_cabinet=SimpleNamespace(id=55, wb_cabinet_id=155),
        adv_setting=_build_adv(bot_active=False),
        in_favorites=False,
        ui_access=UiAccessMode.FREE,
    )

    texts = _button_texts(markup)

    assert texts[0] == "🔴 Автоуправление выключено / подключить"
    assert _first_button_callback(markup) == callbacks.AutoManagementLanding(
        action="open",
        adv_setting_original_id=1,
        wb_user_cabinet_original_id=55,
    ).pack()
    assert "➡ Контроль ключевых слов по кампании" in texts
    assert "Анализ Динамики Ранжирования" in texts
    assert "Управление активностью РК" in texts
    assert "⏰ Ограничения показов по времени" in texts
    assert "Управление ставкой" in texts
    assert "Изменить ставку в Авто" in texts
    assert "Поставить общую ставку для Поисковой РК" in texts
    assert "Обновить минус-слова" in texts
    assert "Выгрузить ключи в csv-файл" in texts
    assert "История позиций ключевых слов" in texts
    assert "Последние действия с ключами" in texts

    assert "Режимы Управления Белым Списком" not in texts
    assert "Стратегия РК" not in texts
    assert "Управление ставкой в полках" not in texts
    assert "Применить дефолтные настройки" not in texts
    assert "Переключить на кластерный биддер" not in texts
    assert "Включить автоуправление целевой позицией (платно, см. тарифы)" not in texts
    assert "Включить управление общей ставкой в Аукционе" not in texts
    assert "Версия АвтоАпдейтера (сейчас V3)" not in texts
    assert "V3 cal. шаг: 4" not in texts
    assert "V3 агр.: 2" not in texts


@pytest.mark.unit
def test_paid_keyboard_shows_autopilot_controls_and_top_auto_button() -> None:
    markup = get_adv_setting_keyboard(
        wb_user_cabinet=SimpleNamespace(id=55, wb_cabinet_id=155),
        adv_setting=_build_adv(bot_active=True),
        in_favorites=False,
        ui_access=UiAccessMode.PAID,
    )

    texts = _button_texts(markup)

    assert texts[0] == "🟢 Автоуправление включено"
    assert _first_button_callback(markup) == callbacks.AutoManagementLanding(
        action="open",
        adv_setting_original_id=1,
        wb_user_cabinet_original_id=55,
    ).pack()
    assert "Стратегия РК" in texts
    assert "Управление ставкой в полках" in texts
    assert "Применить дефолтные настройки" in texts
    assert "Переключить на кластерный биддер" in texts
    assert "$ Выключить автоуправление целевой позицией" not in texts
    assert "Включить автоуправление целевой позицией (платно, см. тарифы)" in texts
    assert "Включить управление общей ставкой в Аукционе" in texts
    assert "Режимы Управления Белым Списком" in texts
    assert "Версия АвтоАпдейтера (сейчас V3)" in texts
    assert "V3 cal. шаг: 4" in texts
    assert "V3 агр.: 2" in texts


@pytest.mark.unit
def test_search_common_bid_button_hidden_without_search_campaign() -> None:
    adv = _build_adv(bot_active=False)
    adv.search_adv_id = None

    markup = get_adv_setting_keyboard(
        wb_user_cabinet=SimpleNamespace(id=55, wb_cabinet_id=155),
        adv_setting=adv,
        in_favorites=False,
        ui_access=UiAccessMode.FREE,
    )

    texts = _button_texts(markup)

    assert "Поставить общую ставку для Поисковой РК" not in texts


@pytest.mark.asyncio
async def test_adv_setting_menu_resolve_ui_access_uses_resolver_result_free() -> None:
    menu = AdvSettingMenu.__new__(AdvSettingMenu)
    menu.adv = SimpleNamespace(bot_active=True)
    menu._chat_id = 373435337
    menu._ui_access_resolver = SimpleNamespace(
        resolve_adv_ui_access=AsyncMock(return_value=UiAccessMode.FREE)
    )

    access = await menu._resolve_ui_access()  # type: ignore[attr-defined]

    assert access == UiAccessMode.FREE
    menu._ui_access_resolver.resolve_adv_ui_access.assert_awaited_once_with(  # type: ignore[attr-defined]
        373435337, menu.adv
    )


@pytest.mark.asyncio
async def test_adv_setting_menu_resolve_ui_access_uses_resolver_result_paid() -> None:
    menu = AdvSettingMenu.__new__(AdvSettingMenu)
    menu.adv = SimpleNamespace(bot_active=False)
    menu._chat_id = 373435337
    menu._ui_access_resolver = SimpleNamespace(
        resolve_adv_ui_access=AsyncMock(return_value=UiAccessMode.PAID)
    )

    access = await menu._resolve_ui_access()  # type: ignore[attr-defined]

    assert access == UiAccessMode.PAID
    menu._ui_access_resolver.resolve_adv_ui_access.assert_awaited_once_with(  # type: ignore[attr-defined]
        373435337, menu.adv
    )
