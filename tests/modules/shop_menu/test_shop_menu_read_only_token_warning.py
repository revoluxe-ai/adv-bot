"""Unit tests for read-only token warning in the shop menu."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_menu.message import ShopMenu
from app.modules.token_monitoring.services.token_info_service import (
    TokenInfo,
    TokenStatusReport,
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
        categories={
            "Контент",
            "Статистика",
            "Аналитика",
            "Продвижение",
        },
        is_read_only=is_read_only,
        is_valid=True,
        is_expired=False,
        is_personal=True,
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

    assert "доступны только права чтения" in text
    assert "Бот работает в режиме аналитики" in text
    assert "Автоуправление ставками и кампаниями недоступно" in text


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
