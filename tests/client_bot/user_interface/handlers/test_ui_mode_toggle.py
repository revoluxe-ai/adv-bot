"""Unit tests for admin UI mode toggle callback."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers.ui_mode_toggle import toggle_ui_mode
from app.client_bot.user_interface.views.callbacks import UiModeToggle

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_toggle_ui_mode_rejects_regular_user() -> None:
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()
    callback = SimpleNamespace(
        message=SimpleNamespace(chat=SimpleNamespace(id=10)),
        from_user=SimpleNamespace(id=999999),
    )

    await toggle_ui_mode(
        callback_query=callback,
        callback_data=UiModeToggle(wb_user_cabinet_original_id=42),
        bot=bot,
        state=state,
        redis_client=MagicMock(),
    )

    bot.send_message.assert_awaited_once()
    state.clear.assert_not_awaited()


@pytest.mark.asyncio
async def test_toggle_ui_mode_toggles_and_rerenders_menu() -> None:
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()
    callback = SimpleNamespace(
        message=SimpleNamespace(chat=SimpleNamespace(id=10)),
        from_user=SimpleNamespace(id=373435337),
    )
    redis_client = MagicMock()
    redis_client.get = AsyncMock(return_value="paid")
    redis_client.set = AsyncMock(return_value=True)

    shop_menu_instance = AsyncMock()
    with patch(
        "app.client_bot.user_interface.handlers.ui_mode_toggle.ShopMenu",
        return_value=shop_menu_instance,
    ) as shop_menu_cls:
        await toggle_ui_mode(
            callback_query=callback,
            callback_data=UiModeToggle(wb_user_cabinet_original_id=42),
            bot=bot,
            state=state,
            redis_client=redis_client,
        )

    redis_client.set.assert_awaited_once_with("ui_mode:user:373435337", "free")
    bot.send_message.assert_awaited_once()
    state.clear.assert_awaited_once()
    shop_menu_cls.assert_called_once()
    shop_menu_instance.assert_awaited_once()
