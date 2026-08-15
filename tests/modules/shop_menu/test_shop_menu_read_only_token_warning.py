"""Unit tests for read-only token warning in the shop menu."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.client_bot.ui_access import UiAccessMode
from app.modules.shop_menu.message import ShopMenu, build_shop_main_keyboard
from app.modules.token_monitoring.services.token_info_service import (
    TokenInfo,
    TokenStatusReport,
)
from tests.helpers.telegram_message_asserts import (
    assert_html_is_telegram_safe,
    assert_keyboard_has_buttons,
    assert_message_contains_required_phrases,
    assert_message_within_telegram_limit,
    assert_no_raw_technical_text,
)

pytestmark = pytest.mark.unit


def _build_shop_menu(token_status: TokenStatusReport) -> ShopMenu:
    """Create a ShopMenu instance with preloaded cabinet and token data."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.update_data = AsyncMock()

    shop_menu = ShopMenu(
        bot=bot,
        chat_id=123,
        state=state,
        wb_user_cabinet_original_id=1,
        redis_client=None,
    )
    shop_menu._balance = 1000.0
    shop_menu._bonus = 0.0
    shop_menu.count_active_advs = 1
    shop_menu._total_active_advs_count = 1
    shop_menu.price_for_month_for_shop = 500
    shop_menu.total_amount_for_day = 50.0
    shop_menu._tariff_details = None
    shop_menu._shop_balance_snapshot = None
    shop_menu._wb_user_cabinet = MagicMock()
    shop_menu._wb_user_cabinet.name = "Test Shop"
    shop_menu._wb_user_cabinet.user = MagicMock()
    shop_menu._wb_user_cabinet.user.user_telegram_id = 373435337
    shop_menu._wb_cabinet = MagicMock()
    shop_menu._wb_cabinet.shop_id = "shop_123"
    shop_menu._wb_cabinet.active = True
    shop_menu._token_status_loaded = True
    shop_menu._token_status = token_status
    return shop_menu


def _build_token(*, is_read_only: bool) -> TokenInfo:
    """Create a token for menu text scenarios."""
    return TokenInfo(
        id=1,
        api_key="key",
        user_id=1,
        shop_id="shop_123",
        expires=datetime.now(UTC) + timedelta(days=30),
        categories={"Контент", "Статистика", "Аналитика", "Продвижение"},
        is_read_only=is_read_only,
        is_valid=True,
        is_expired=False,
        is_personal=True,
    )


def test_shop_menu_shows_ui_mode_toggle_for_admin() -> None:
    """Admin shop menu includes a UI mode toggle button."""
    read_only_token = _build_token(is_read_only=True)
    token_status = TokenStatusReport(
        shop_id="shop_123",
        shop_name="Test Shop",
        status="Insufficient",
        all_tokens=[read_only_token],
        valid_tokens=[],
        expired_tokens=[],
        available_permissions=set(),
        missing_permissions={"Продвижение"},
        has_all_required_permissions=False,
        expiring_tokens=[],
    )

    keyboard = _build_shop_menu(token_status).keyboard
    texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
    assert "Режим интерфейса: FREE" in texts


def test_shop_menu_hides_ui_mode_toggle_for_non_admin() -> None:
    """Non-admin shop menu does not include the UI mode toggle."""
    read_only_token = _build_token(is_read_only=True)
    token_status = TokenStatusReport(
        shop_id="shop_123",
        shop_name="Test Shop",
        status="Insufficient",
        all_tokens=[read_only_token],
        valid_tokens=[],
        expired_tokens=[],
        available_permissions=set(),
        missing_permissions={"Продвижение"},
        has_all_required_permissions=False,
        expiring_tokens=[],
    )

    shop_menu = _build_shop_menu(token_status)
    shop_menu._wb_user_cabinet.user.user_telegram_id = 999999
    texts = [btn.text for row in shop_menu.keyboard.inline_keyboard for btn in row]
    assert "Режим интерфейса: FREE" not in texts


def test_shop_menu_hides_paid_controls_in_free_mode() -> None:
    """Free mode hides management/export buttons but keeps navigation."""
    shop = _build_shop_menu(
        TokenStatusReport(
            shop_id="shop_123",
            shop_name="Test Shop",
            status="Complete",
            all_tokens=[],
            valid_tokens=[],
            expired_tokens=[],
            available_permissions=set(),
            missing_permissions=set(),
            has_all_required_permissions=True,
            expiring_tokens=[],
        )
    )
    keyboard = build_shop_main_keyboard(
        shop._wb_user_cabinet,
        shop._wb_cabinet,
        ui_access=UiAccessMode.FREE,
    )
    texts = [btn.text for row in keyboard.inline_keyboard for btn in row]

    assert_keyboard_has_buttons(
        keyboard,
        [
            "Автоматические рекламные кампании",
            "Пополнить баланс",
            "Вернуться к списку магазинов",
        ],
    )
    assert "Массовые операции с РК" not in texts
    assert "Выгрузить все РК в Excel" not in texts
    assert "Загрузить настройки из Excel" not in texts
    assert "Подключить существующие кампании" in texts


def test_shop_menu_shows_paid_controls_in_paid_mode() -> None:
    """Paid mode keeps management/export buttons visible."""
    shop = _build_shop_menu(
        TokenStatusReport(
            shop_id="shop_123",
            shop_name="Test Shop",
            status="Complete",
            all_tokens=[],
            valid_tokens=[],
            expired_tokens=[],
            available_permissions=set(),
            missing_permissions=set(),
            has_all_required_permissions=True,
            expiring_tokens=[],
        )
    )
    keyboard = build_shop_main_keyboard(
        shop._wb_user_cabinet,
        shop._wb_cabinet,
        ui_access=UiAccessMode.PAID,
    )
    assert_keyboard_has_buttons(
        keyboard,
        ["Массовые операции с РК", "Выгрузить все РК в Excel", "Загрузить настройки из Excel"],
    )


def test_shop_menu_shows_read_only_token_warning() -> None:
    """Shop menu shows analytics-only warning for read-only tokens."""
    read_only_token = _build_token(is_read_only=True)
    token_status = TokenStatusReport(
        shop_id="shop_123",
        shop_name="Test Shop",
        status="Insufficient",
        all_tokens=[read_only_token],
        valid_tokens=[],
        expired_tokens=[],
        available_permissions=set(),
        missing_permissions={"Продвижение"},
        has_all_required_permissions=False,
        expiring_tokens=[],
    )

    text = _build_shop_menu(token_status).text
    assert_message_within_telegram_limit(text)
    assert_html_is_telegram_safe(text)
    assert_message_contains_required_phrases(
        text,
        [
            "доступны только права чтения",
            "Бот работает в режиме аналитики",
            "Автоуправление ставками и кампаниями недоступно",
            "токен с возможностью изменений в кабинете",
            "Нужные права токена: Контент, Статистика, Аналитика, Продвижение.",
        ],
    )
    assert "права продвижения" not in text
    assert "free" not in text.lower()
    assert_no_raw_technical_text(text)


def test_shop_menu_hides_read_only_warning_for_normal_token() -> None:
    """Shop menu does not show the read-only warning when write permissions exist."""
    normal_token = _build_token(is_read_only=False)
    token_status = TokenStatusReport(
        shop_id="shop_123",
        shop_name="Test Shop",
        status="Complete",
        all_tokens=[normal_token],
        valid_tokens=[normal_token],
        expired_tokens=[],
        available_permissions=normal_token.categories,
        missing_permissions=set(),
        has_all_required_permissions=True,
        expiring_tokens=[],
    )

    text = _build_shop_menu(token_status).text
    assert "доступны только права чтения" not in text
    assert "Токены" in text


def test_shop_menu_hides_read_only_warning_for_mixed_tokens() -> None:
    """Shop menu does not show analytics-only warning when a write-capable token exists."""
    read_only_token = _build_token(is_read_only=True)
    normal_token = _build_token(is_read_only=False)
    token_status = TokenStatusReport(
        shop_id="shop_123",
        shop_name="Test Shop",
        status="Complete",
        all_tokens=[read_only_token, normal_token],
        valid_tokens=[normal_token],
        expired_tokens=[],
        available_permissions=normal_token.categories,
        missing_permissions=set(),
        has_all_required_permissions=True,
        expiring_tokens=[],
    )

    text = _build_shop_menu(token_status).text
    assert "доступны только права чтения" not in text
    assert "Бот работает в режиме аналитики" not in text
