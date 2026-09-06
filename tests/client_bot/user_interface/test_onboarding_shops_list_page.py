"""Unit tests for ShopsListPage and get_shops_list_keyboard."""

from unittest.mock import MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers.shop_choice_message import (
    SHOPS_LIST_PAGE_TITLE,
    ShopsListPage,
    get_shops_list_keyboard,
)
from app.client_bot.user_interface.views import callbacks

pytestmark = pytest.mark.unit


def _make_wb_user_cabinet(
    name: str,
    id: int,
    shop_id: str,
    active: bool = True,
):
    """Create mock WBUserCabinet with wb_cabinet."""
    wb_cabinet = MagicMock()
    wb_cabinet.shop_id = shop_id
    wb_cabinet.active = active
    uc = MagicMock()
    uc.name = name
    uc.id = id
    uc.wb_cabinet = wb_cabinet
    return uc


def test_shops_list_page_text_equals_title() -> None:
    """ShopsListPage.text equals SHOPS_LIST_PAGE_TITLE."""
    page = ShopsListPage(bot=None, chat_id=1, all_shops=[])  # type: ignore[arg-type]
    assert page.text == SHOPS_LIST_PAGE_TITLE
    assert "Добавить магазин" in page.text
    assert "✅" in page.text
    assert "❌" in page.text
    assert "[Каб][Ток]" in page.text


@patch("app.client_bot.user_interface.handlers.shop_choice_message.settings")
def test_get_shops_list_keyboard_empty_list(mock_settings) -> None:
    """Empty shops with invite_gate on: Add, balance, invite, Back."""
    mock_settings.invite_gate = True
    kb = get_shops_list_keyboard([], 123)
    rows = kb.inline_keyboard
    assert len(rows) == 4
    assert rows[0][0].text == "➕Добавить магазин"
    assert rows[0][0].callback_data == callbacks.ShopNew().pack()
    assert rows[1][0].text == "Мой баланс"
    assert rows[1][0].callback_data == callbacks.UserBalanceMenu().pack()
    assert rows[2][0].text == "Показать инвайт"
    assert rows[2][0].callback_data == callbacks.InviteShow().pack()
    assert rows[3][0].text == "Назад"
    assert rows[3][0].callback_data == callbacks.Start().pack()


@patch("app.client_bot.user_interface.handlers.shop_choice_message.settings")
def test_get_shops_list_keyboard_empty_hides_invite_when_invite_gate_off(
    mock_settings,
) -> None:
    """INVITE_GATE=false hides partner-invite on shops list."""
    mock_settings.invite_gate = False
    kb = get_shops_list_keyboard([], 123)
    rows = kb.inline_keyboard
    assert len(rows) == 3
    assert rows[0][0].text == "➕Добавить магазин"
    assert rows[1][0].text == "Мой баланс"
    assert rows[2][0].text == "Назад"
    texts = [btn.text for row in rows for btn in row]
    assert "Показать инвайт" not in texts


@patch("app.client_bot.user_interface.handlers.shop_choice_message.settings")
def test_get_shops_list_keyboard_shop_active_token(mock_settings) -> None:
    """active=True and active token -> button has '[Каб][Ток] Name' prefix."""
    mock_settings.invite_gate = True
    uc = _make_wb_user_cabinet("Shop1", 1, "shop_1", active=True)
    kb = get_shops_list_keyboard([uc], 123, shop_ids_with_active_tokens={"shop_1"})
    rows = kb.inline_keyboard
    assert rows[1][0].text.strip() == "✅✅ Shop1"
    assert (
        rows[1][0].callback_data
        == callbacks.Shop(action="select", wb_user_cabinet_original_id=1).pack()
    )


@patch("app.client_bot.user_interface.handlers.shop_choice_message.settings")
def test_get_shops_list_keyboard_shop_inactive_token(mock_settings) -> None:
    """Without active token -> token icon is ❌ in '[Каб][Ток] Name'."""
    mock_settings.invite_gate = True
    uc = _make_wb_user_cabinet("Shop2", 2, "shop_2", active=True)
    kb = get_shops_list_keyboard([uc], 123, shop_ids_with_active_tokens=set())
    rows = kb.inline_keyboard
    assert rows[1][0].text.strip() == "✅❌ Shop2"


@patch("app.client_bot.user_interface.handlers.shop_choice_message.settings")
def test_get_shops_list_keyboard_shop_ids_none_uses_only_active(mock_settings) -> None:
    """shop_ids_with_active_tokens=None: only active flag checked."""
    mock_settings.invite_gate = True
    uc = _make_wb_user_cabinet("Shop3", 3, "shop_3", active=True)
    kb = get_shops_list_keyboard([uc], 123, shop_ids_with_active_tokens=None)
    rows = kb.inline_keyboard
    assert rows[1][0].text.strip() == "✅✅ Shop3"

    uc_inactive = _make_wb_user_cabinet("Shop4", 4, "shop_4", active=False)
    kb2 = get_shops_list_keyboard([uc_inactive], 123, shop_ids_with_active_tokens=None)
    assert kb2.inline_keyboard[1][0].text.strip() == "❌✅ Shop4"


@patch("app.client_bot.user_interface.handlers.shop_choice_message.settings")
def test_get_shops_list_keyboard_missing_active_falls_back_to_token_state(
    mock_settings,
) -> None:
    """Отсутствующий wb_cabinet.active обрабатывается как active=True (fallback)."""
    mock_settings.invite_gate = True
    uc = _make_wb_user_cabinet("ShopFallback", 5, "shop_5", active=True)
    del uc.wb_cabinet.active
    kb = get_shops_list_keyboard([uc], 123, shop_ids_with_active_tokens={"shop_5"})
    assert kb.inline_keyboard[1][0].text.strip() == "ShopFallback ✅"


@patch("app.client_bot.user_interface.handlers.shop_choice_message.settings")
def test_get_shops_list_keyboard_pagination_25_shops_page1(mock_settings) -> None:
    """25 shops, page=1: no ⬅️, has ➡️; 20 shops on page."""
    mock_settings.invite_gate = True
    shops = [_make_wb_user_cabinet(f"Shop{i}", i, f"shop_{i}") for i in range(25)]
    kb = get_shops_list_keyboard(shops, 123, page=1)
    rows = kb.inline_keyboard
    # Add shop + 20 shops + paginator + Мой баланс + Показать инвайт + Назад
    assert len(rows) == 25
    paginator_idx = 21
    assert rows[paginator_idx][0].text == "Вперёд ➡️"
    assert (
        rows[paginator_idx][0].callback_data
        == callbacks.ShopsListPaginator(page=2).pack()
    )
    assert rows[1][0].text.strip() == "✅✅ Shop0"


@patch("app.client_bot.user_interface.handlers.shop_choice_message.settings")
def test_get_shops_list_keyboard_pagination_45_shops_page2(mock_settings) -> None:
    """45 shops, page=2: ⬅️ and ➡️ both; 20 shops on page 2."""
    mock_settings.invite_gate = True
    shops = [_make_wb_user_cabinet(f"Shop{i}", i, f"shop_{i}") for i in range(45)]
    kb = get_shops_list_keyboard(shops, 123, page=2)
    rows = kb.inline_keyboard
    assert len(rows) == 25
    paginator_row = rows[21]
    assert len(paginator_row) == 2
    assert paginator_row[0].text == "⬅️ Назад"
    assert paginator_row[1].text == "Вперёд ➡️"
    assert rows[1][0].text.strip() == "✅✅ Shop20"


@patch("app.client_bot.user_interface.handlers.shop_choice_message.settings")
def test_get_shops_list_keyboard_no_pagination_20_shops(mock_settings) -> None:
    """20 shops, page=1: no pagination."""
    mock_settings.invite_gate = True
    shops = [_make_wb_user_cabinet(f"Shop{i}", i, f"shop_{i}") for i in range(20)]
    kb = get_shops_list_keyboard(shops, 123, page=1)
    rows = kb.inline_keyboard
    assert len(rows) == 24
    assert rows[-1][0].text == "Назад"


@patch("app.client_bot.user_interface.handlers.shop_choice_message.settings")
def test_get_shops_list_keyboard_shop_name_truncated_to_100(mock_settings) -> None:
    """Shop button text truncated to 100 chars."""
    mock_settings.invite_gate = True
    long_name = "A" * 150
    uc = _make_wb_user_cabinet(long_name, 1, "shop_1")
    kb = get_shops_list_keyboard([uc], 123, shop_ids_with_active_tokens=None)
    btn_text = kb.inline_keyboard[1][0].text
    assert len(btn_text) == 100
    assert btn_text.startswith("✅✅ A")  # status prefix + truncated long name


@patch("app.client_bot.user_interface.handlers.shop_choice_message.settings")
def test_get_shops_list_keyboard_back_button_start_callback(mock_settings) -> None:
    """Back button uses callbacks.Start().pack()."""
    mock_settings.invite_gate = True
    kb = get_shops_list_keyboard([], 123)
    back_btn = kb.inline_keyboard[-1][0]
    assert back_btn.callback_data == callbacks.Start().pack()


@pytest.mark.asyncio
@patch("app.client_bot.user_interface.handlers.shop_choice_message.settings")
async def test_shops_list_page_calls_bot_send_message(mock_settings) -> None:
    """ShopsListPage(...)() calls bot.send_message with text and reply_markup."""
    from unittest.mock import AsyncMock

    mock_settings.invite_gate = True
    bot = AsyncMock()
    uc = _make_wb_user_cabinet("TestShop", 1, "shop_1")
    page = ShopsListPage(bot, 999, [uc], shop_ids_with_active_tokens={"shop_1"})
    await page()
    bot.send_message.assert_awaited_once()
    call_kw = bot.send_message.call_args[1]
    assert call_kw["chat_id"] == 999
    assert call_kw["text"] == SHOPS_LIST_PAGE_TITLE
    km = call_kw["reply_markup"]
    assert km is not None
    assert len(km.inline_keyboard) >= 5  # Add, shop, balance, invite, back
    assert km.inline_keyboard[1][0].text.strip() == "✅✅ TestShop"
