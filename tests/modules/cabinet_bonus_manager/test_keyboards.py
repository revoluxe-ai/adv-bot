from app.modules.cabinet_bonus_manager.keyboards import get_shop_bonus_keyboard


def test_shop_bonus_keyboard_contains_balance_actions():
    markup = get_shop_bonus_keyboard(wb_cabinet_original_id=42)
    rows = markup.inline_keyboard
    all_buttons = [button for row in rows for button in row]

    callbacks = [button.callback_data for button in all_buttons]
    texts = [button.text for button in all_buttons]

    assert any("add_balance" in data for data in callbacks)
    assert any("subtract_balance" in data for data in callbacks)
    assert any("reset_balance" in data for data in callbacks)
    assert any("subtract_priority" in data for data in callbacks)
    assert any("Баланс" in text for text in texts)
