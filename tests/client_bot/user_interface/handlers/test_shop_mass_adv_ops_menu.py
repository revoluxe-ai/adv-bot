from types import SimpleNamespace
from unittest.mock import AsyncMock, patch, Mock

import pytest

from app.client_bot.user_interface.handlers.start.start import (
    close_shop_mass_adv_ops_menu,
    open_shop_mass_adv_ops_menu,
)
from app.client_bot.user_interface.views import callbacks


@pytest.mark.asyncio
async def test_open_shop_mass_adv_ops_menu_edits_reply_markup() -> None:
    wb_user_cabinet_id = 42
    callback = SimpleNamespace(
        message=SimpleNamespace(edit_reply_markup=AsyncMock()),
    )
    callback_data = callbacks.ShopMassAdvOpsMenu(
        wb_user_cabinet_original_id=wb_user_cabinet_id
    )
    wb_cabinet = SimpleNamespace(default_max_cpm=123)
    wb_user_cabinet = SimpleNamespace(id=wb_user_cabinet_id, wb_cabinet=wb_cabinet)

    with patch(
        "app.client_bot.user_interface.handlers.start.start._get_wb_user_cabinet_for_shop_menu",
        AsyncMock(return_value=wb_user_cabinet),
    ):
        await open_shop_mass_adv_ops_menu(callback, callback_data)

    callback.message.edit_reply_markup.assert_awaited_once()
    reply_markup = callback.message.edit_reply_markup.await_args.kwargs["reply_markup"]
    texts = [btn.text for row in reply_markup.inline_keyboard for btn in row]
    assert "Полностью отключить бот от управления всех РК" in texts
    assert "Применить дефолты всем кампаниям" in texts
    assert "Сбросить все НРФ во всех РК" in texts
    assert "Назад" in texts


@pytest.mark.asyncio
async def test_close_shop_mass_adv_ops_menu_restores_main_keyboard() -> None:
    wb_user_cabinet_id = 42
    callback = SimpleNamespace(
        message=SimpleNamespace(edit_reply_markup=AsyncMock()),
    )
    callback_data = callbacks.ShopMassAdvOpsBack(
        wb_user_cabinet_original_id=wb_user_cabinet_id
    )
    wb_cabinet = SimpleNamespace(
        id=7,
        active=True,
        adv_settings=[SimpleNamespace(bot_active=True)],
    )
    user = Mock()

    # non-admin user: admin UI-mode toggle must not appear; .user must be present
    # so close → build_shop_main_keyboard matches production eager-loaded shape.
    wb_user_cabinet = SimpleNamespace(
        id=wb_user_cabinet_id,
        wb_cabinet=wb_cabinet,
        user=SimpleNamespace(user_telegram_id=1_000_001),
    )

    with patch(
        "app.client_bot.user_interface.handlers.start.start._get_wb_user_cabinet_for_shop_menu",
        AsyncMock(return_value=wb_user_cabinet),
    ):
        await close_shop_mass_adv_ops_menu(callback, callback_data)

    callback.message.edit_reply_markup.assert_awaited_once()
    reply_markup = callback.message.edit_reply_markup.await_args.kwargs["reply_markup"]
    texts = [btn.text for row in reply_markup.inline_keyboard for btn in row]
    assert "Массовые операции с РК" in texts
    assert "Полностью отключить бот от управления всех РК" not in texts
