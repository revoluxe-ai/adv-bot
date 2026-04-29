"""Unit tests for keyboards: buttons 'to shops list' use ShowShopsList."""

import datetime
from unittest.mock import MagicMock

from app.client_bot.user_interface.views import callbacks
from app.client_bot.user_interface.views.keyboards import (
    get_payment_keyboard,
    get_shop_menu_keyboard,
)


def _make_wb_user_cabinet(cabinet_id: int = 1) -> MagicMock:
    """Create mock WBUserCabinet with wb_cabinet."""
    wb_cabinet = MagicMock()
    wb_cabinet.id = cabinet_id
    wb_cabinet.expiration_time = datetime.datetime(2020, 1, 1)
    wb_cabinet.balance = 0
    wb_cabinet.bonus = 0
    uc = MagicMock()
    uc.id = 1
    uc.wb_cabinet = wb_cabinet
    return uc


def test_get_shop_menu_keyboard_back_to_shops_uses_show_shops_list() -> None:
    """get_shop_menu_keyboard: 'Вернуться к списку магазинов' has callback ShowShopsList."""
    uc = _make_wb_user_cabinet()
    kb = get_shop_menu_keyboard(uc, 1, is_active_adv=False)
    # Find the "Вернуться к списку магазинов" button
    expected_callback = callbacks.ShowShopsList().pack()
    found = False
    for row in kb.inline_keyboard:
        for btn in row:
            if btn.text == "Вернуться к списку магазинов":
                assert btn.callback_data == expected_callback
                found = True
                break
    assert found


def test_get_payment_keyboard_back_to_shops_uses_show_shops_list() -> None:
    """get_payment_keyboard: 'К списку магазинов' has callback ShowShopsList."""
    kb = get_payment_keyboard(wb_cabinet_original_id=1)
    expected_callback = callbacks.ShowShopsList().pack()
    found = False
    for row in kb.inline_keyboard:
        for btn in row:
            if btn.text == "К списку магазинов":
                assert btn.callback_data == expected_callback
                found = True
                break
    assert found


def test_shop_menu_keyboard_back_to_shops_uses_show_shops_list() -> None:
    """ShopMenu keyboard: 'Вернуться к списку магазинов' has callback ShowShopsList."""
    from app.modules.shop_menu.message import ShopMenu

    bot = MagicMock()
    state = MagicMock()
    state.update_data = MagicMock(return_value=None)
    menu = ShopMenu(
        bot=bot,
        chat_id=123,
        state=state,
        wb_user_cabinet_original_id=1,
        redis_client=None,
    )
    wb_cabinet = MagicMock()
    wb_cabinet.id = 1
    wb_cabinet.default_max_cpm = 100
    wb_user_cabinet = MagicMock()
    wb_user_cabinet.id = 1
    wb_user_cabinet.wb_cabinet = wb_cabinet
    menu._wb_user_cabinet = wb_user_cabinet
    menu._wb_cabinet = wb_cabinet
    menu._user_telegram_id = 123

    kb = menu.keyboard
    expected_callback = callbacks.ShowShopsList().pack()
    found = False
    for row in kb.inline_keyboard:
        for btn in row:
            if btn.text == "Вернуться к списку магазинов":
                assert btn.callback_data == expected_callback
                found = True
                break
    assert found


def test_shop_menu_keyboard_connect_existing_advs_button() -> None:
    """ShopMenu keyboard has 'Подключить существующие кампании' with ConnectExistingAdvs callback."""
    from app.modules.shop_menu.message import ShopMenu

    bot = MagicMock()
    state = MagicMock()
    state.update_data = MagicMock(return_value=None)
    cabinet_id = 42
    menu = ShopMenu(
        bot=bot,
        chat_id=123,
        state=state,
        wb_user_cabinet_original_id=cabinet_id,
        redis_client=None,
    )
    wb_cabinet = MagicMock()
    wb_cabinet.id = 1
    wb_cabinet.default_max_cpm = 100
    wb_user_cabinet = MagicMock()
    wb_user_cabinet.id = cabinet_id
    wb_user_cabinet.wb_cabinet = wb_cabinet
    menu._wb_user_cabinet = wb_user_cabinet
    menu._wb_cabinet = wb_cabinet
    menu._user_telegram_id = 123

    kb = menu.keyboard
    expected_callback = callbacks.ConnectExistingAdvs(
        wb_user_cabinet_original_id=cabinet_id
    ).pack()
    found = False
    for row in kb.inline_keyboard:
        for btn in row:
            if btn.text == "Подключить существующие кампании":
                assert btn.callback_data == expected_callback
                found = True
                break
    assert found
