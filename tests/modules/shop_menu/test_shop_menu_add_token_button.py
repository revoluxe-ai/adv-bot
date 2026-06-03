"""
Unit-тесты кнопки «Добавить токен» в ShopMenu.

Проверяют `build_shop_main_keyboard` через свойство `keyboard` без `_load_all_data`
(без Postgres, Redis и TokenInfoService).
"""

from __future__ import annotations

import pytest
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from unittest.mock import AsyncMock, MagicMock

from app.client_bot.user_interface.views.callbacks import AddNewToken
from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.modules.shop_menu.message import ShopMenu
from app.utils.db.models import User

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_bot() -> MagicMock:
    """Мок Bot с async send_message."""
    bot = MagicMock(spec=Bot)
    bot.send_message = AsyncMock()
    return bot


@pytest.fixture
def mock_state() -> MagicMock:
    """Мок FSMContext."""
    state = MagicMock(spec=FSMContext)
    state.update_data = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    return state


@pytest.fixture
def mock_user() -> MagicMock:
    """Мок User."""
    user = MagicMock(spec=User)
    user.id = 1
    user.user_telegram_id = 12345
    return user


@pytest.fixture
def mock_wb_cabinet() -> MagicMock:
    """Мок WBCabinet (без spec — иначе SQLAlchemy hybrid-атрибуты)."""
    cabinet = MagicMock()
    cabinet.id = 1
    cabinet.shop_id = "test_shop_123"
    return cabinet


@pytest.fixture
def mock_wb_user_cabinet(mock_wb_cabinet: MagicMock, mock_user: MagicMock) -> MagicMock:
    """Мок WBUserCabinet, связанный с кабинетом и пользователем."""
    user_cabinet = MagicMock(spec=WBUserCabinet)
    user_cabinet.id = 1
    user_cabinet.name = "Test Shop"
    user_cabinet.wb_cabinet = mock_wb_cabinet
    user_cabinet.user = mock_user
    return user_cabinet


def _shop_menu_with_loaded_cabinets(
    mock_bot: MagicMock,
    mock_state: MagicMock,
    mock_wb_user_cabinet: MagicMock,
    *,
    chat_id: int = 12345,
    wb_user_cabinet_original_id: int | None = None,
) -> ShopMenu:
    """ShopMenu с подставленными кабинетами — как после загрузки данных, без I/O."""
    cabinet_id = wb_user_cabinet_original_id or mock_wb_user_cabinet.id
    shop_menu = ShopMenu(
        bot=mock_bot,
        chat_id=chat_id,
        state=mock_state,
        wb_user_cabinet_original_id=cabinet_id,
    )
    shop_menu._wb_user_cabinet = mock_wb_user_cabinet
    shop_menu._wb_cabinet = mock_wb_user_cabinet.wb_cabinet
    return shop_menu


def _iter_buttons(
    keyboard: InlineKeyboardMarkup,
) -> list[tuple[int, InlineKeyboardButton]]:
    """Плоский список (индекс_строки, кнопка)."""
    return [
        (row_idx, button)
        for row_idx, row in enumerate(keyboard.inline_keyboard)
        for button in row
    ]


def _find_add_token(
    keyboard: InlineKeyboardMarkup,
) -> tuple[int, InlineKeyboardButton, AddNewToken] | None:
    """Кнопка AddNewToken или None."""
    for row_idx, button in _iter_buttons(keyboard):
        try:
            callback_data = AddNewToken.unpack(button.callback_data)
        except Exception:
            continue
        return row_idx, button, callback_data
    return None


def _row_index_by_text(keyboard: InlineKeyboardMarkup, text_part: str) -> int | None:
    """Индекс строки с кнопкой, содержащей подстроку в text."""
    for row_idx, button in _iter_buttons(keyboard):
        if text_part in button.text:
            return row_idx
    return None


class TestShopMenuAddTokenButton:
    """Кнопка «Добавить токен» в главном меню магазина."""

    def test_add_token_button_exists_in_keyboard(
        self,
        mock_bot: MagicMock,
        mock_state: MagicMock,
        mock_wb_user_cabinet: MagicMock,
    ) -> None:
        """Кнопка Add New Token есть в клавиатуре с корректным callback."""
        shop_menu = _shop_menu_with_loaded_cabinets(
            mock_bot, mock_state, mock_wb_user_cabinet
        )
        found = _find_add_token(shop_menu.keyboard)

        assert found is not None, "Add New Token button not found in keyboard"
        _, _, callback_data = found
        assert callback_data.wb_user_cabinet_original_id == 1

    def test_add_token_button_positioned_before_balance(
        self,
        mock_bot: MagicMock,
        mock_state: MagicMock,
        mock_wb_user_cabinet: MagicMock,
    ) -> None:
        """Кнопка токена выше кнопки «Пополнить баланс» (меньший индекс строки)."""
        shop_menu = _shop_menu_with_loaded_cabinets(
            mock_bot, mock_state, mock_wb_user_cabinet
        )
        keyboard = shop_menu.keyboard

        add_token_row = _find_add_token(keyboard)
        balance_row = _row_index_by_text(keyboard, "Пополнить баланс")

        assert balance_row is not None, "Balance button not found"
        assert add_token_row is not None, "Add Token button not found"
        assert add_token_row[0] < balance_row, (
            "Add Token button should be positioned before Balance button"
        )

    def test_add_token_button_callback_data_format(
        self,
        mock_bot: MagicMock,
        mock_state: MagicMock,
        mock_wb_user_cabinet: MagicMock,
    ) -> None:
        """callback_data начинается с add_new_token: и содержит id кабинета."""
        mock_wb_user_cabinet.id = 42
        shop_menu = _shop_menu_with_loaded_cabinets(
            mock_bot,
            mock_state,
            mock_wb_user_cabinet,
            wb_user_cabinet_original_id=42,
        )
        found = _find_add_token(shop_menu.keyboard)

        assert found is not None, "Add New Token button not found"
        _, button, callback_data = found
        assert callback_data.wb_user_cabinet_original_id == 42
        assert button.callback_data.startswith("add_new_token:")

    def test_add_token_button_for_admin_user(
        self,
        mock_bot: MagicMock,
        mock_state: MagicMock,
        mock_wb_user_cabinet: MagicMock,
    ) -> None:
        """Кнопка видна админу (клавиатура не скрывает её по роли)."""
        mock_wb_user_cabinet.user.user_telegram_id = 12345
        shop_menu = _shop_menu_with_loaded_cabinets(
            mock_bot, mock_state, mock_wb_user_cabinet
        )

        assert _find_add_token(shop_menu.keyboard) is not None, (
            "Add New Token button should be visible for admins"
        )

    def test_add_token_button_for_regular_user(
        self,
        mock_bot: MagicMock,
        mock_state: MagicMock,
        mock_wb_user_cabinet: MagicMock,
    ) -> None:
        """Кнопка видна обычному пользователю."""
        mock_wb_user_cabinet.user.user_telegram_id = 99999
        shop_menu = _shop_menu_with_loaded_cabinets(
            mock_bot,
            mock_state,
            mock_wb_user_cabinet,
            chat_id=99999,
        )

        assert _find_add_token(shop_menu.keyboard) is not None, (
            "Add New Token button should be visible for regular users"
        )

    def test_keyboard_structure_integrity(
        self,
        mock_bot: MagicMock,
        mock_state: MagicMock,
        mock_wb_user_cabinet: MagicMock,
    ) -> None:
        """Клавиатура непустая; у каждой кнопки есть text и callback_data."""
        keyboard = _shop_menu_with_loaded_cabinets(
            mock_bot, mock_state, mock_wb_user_cabinet
        ).keyboard

        assert keyboard is not None
        assert len(keyboard.inline_keyboard) > 0

        for row in keyboard.inline_keyboard:
            assert len(row) > 0
            for button in row:
                assert button.text is not None
                assert button.callback_data is not None
