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


def test_shop_menu_keyboard_mass_ops_button_and_hidden_bulk_buttons() -> None:
    """ShopMenu main keyboard has mass ops entry and hides moved bulk buttons."""
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
    wb_cabinet.white_list_update_active = False
    wb_cabinet.default_max_cpm = 100
    wb_user_cabinet = MagicMock()
    wb_user_cabinet.id = cabinet_id
    wb_user_cabinet.wb_cabinet = wb_cabinet
    menu._wb_user_cabinet = wb_user_cabinet
    menu._wb_cabinet = wb_cabinet
    menu._user_telegram_id = 123

    kb = menu.keyboard
    all_texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "Массовые операции с РК" in all_texts
    assert "Отключить все кампании" not in all_texts
    assert "Применить дефолты всем кампаниям" not in all_texts
    assert not any(text.startswith("Дефолтная максимальная ставка (CPM)") for text in all_texts)


def test_shop_mass_adv_ops_keyboard_buttons() -> None:
    """Mass operations keyboard has 3 actions and back button."""
    from app.modules.shop_menu.message import build_shop_mass_adv_ops_keyboard

    cabinet_id = 42
    wb_cabinet = MagicMock()
    wb_cabinet.default_max_cpm = 100
    wb_user_cabinet = MagicMock()
    wb_user_cabinet.id = cabinet_id
    wb_user_cabinet.wb_cabinet = wb_cabinet

    kb = build_shop_mass_adv_ops_keyboard(wb_user_cabinet, wb_cabinet)
    expected_callbacks = {
        "Отключить все кампании": callbacks.TurnBot(
            action="off_all", wb_user_cabinet_original_id=cabinet_id
        ).pack(),
        "Применить дефолты всем кампаниям": callbacks.ApplyDefaultsForShop(
            wb_user_cabinet_original_id=cabinet_id
        ).pack(),
        "Назад": callbacks.ShopMassAdvOpsBack(
            wb_user_cabinet_original_id=cabinet_id
        ).pack(),
    }
    found = {btn.text: btn.callback_data for row in kb.inline_keyboard for btn in row}

    assert found["Отключить все кампании"] == expected_callbacks["Отключить все кампании"]
    assert found["Применить дефолты всем кампаниям"] == expected_callbacks["Применить дефолты всем кампаниям"]
    assert found["Назад"] == expected_callbacks["Назад"]
    assert any(text.startswith("Дефолтная максимальная ставка (CPM) (100)") for text in found)
