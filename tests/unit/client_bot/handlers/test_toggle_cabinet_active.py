from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers.start.start import (
    CABINET_DEACTIVATED_NOTIFICATION_TYPE,
    toggle_cabinet_active_handler,
)


class _MockSessionMaker:
    def __init__(self, session: MagicMock) -> None:
        self._session = session

    def __call__(self, read_only: bool = False) -> "_MockSessionMaker":
        return self

    async def __aenter__(self) -> MagicMock:
        return self._session

    async def __aexit__(self, *args: object) -> None:
        return None


def _build_callback(user_id: int = 101, chat_id: int = 202) -> SimpleNamespace:
    return SimpleNamespace(
        from_user=SimpleNamespace(id=user_id),
        message=SimpleNamespace(chat=SimpleNamespace(id=chat_id)),
    )


def _build_callback_data(wb_user_cabinet_original_id: int = 77) -> SimpleNamespace:
    return SimpleNamespace(wb_user_cabinet_original_id=wb_user_cabinet_original_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_toggle_cabinet_active_deactivates_and_opens_shop_menu() -> None:
    callback = _build_callback()
    callback_data = _build_callback_data()
    bot = AsyncMock()
    state = AsyncMock()

    wb_user_cabinet = SimpleNamespace(
        wb_cabinet=SimpleNamespace(shop_id="shop_1", active=True)
    )
    result = MagicMock()
    result.unique.return_value.scalar_one_or_none.return_value = wb_user_cabinet
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)

    mock_sm = _MockSessionMaker(session)
    deactivate = AsyncMock(return_value=True)
    activate = AsyncMock()
    shop_menu_call = AsyncMock()
    shop_menu_ctor = MagicMock(return_value=shop_menu_call)

    with (
        patch("app.client_bot.user_interface.handlers.start.start.sm", mock_sm),
        patch(
            "app.client_bot.user_interface.handlers.start.start.deactivate_cabinet_atomic_with_user_trackers",
            deactivate,
        ),
        patch("app.client_bot.user_interface.handlers.start.start.activate_cabinet", activate),
        patch("app.client_bot.user_interface.handlers.start.start.ShopMenu", shop_menu_ctor),
    ):
        await toggle_cabinet_active_handler(callback, callback_data, bot, state)

    deactivate.assert_awaited_once_with(
        "shop_1",
        notification_type=CABINET_DEACTIVATED_NOTIFICATION_TYPE,
    )
    activate.assert_not_awaited()
    shop_menu_ctor.assert_called_once_with(bot, 202, state, 77)
    shop_menu_call.assert_awaited_once()
    bot.send_message.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_toggle_cabinet_active_activates_and_opens_shop_menu() -> None:
    callback = _build_callback()
    callback_data = _build_callback_data()
    bot = AsyncMock()
    state = AsyncMock()

    wb_user_cabinet = SimpleNamespace(
        wb_cabinet=SimpleNamespace(shop_id="shop_2", active=False)
    )
    result = MagicMock()
    result.unique.return_value.scalar_one_or_none.return_value = wb_user_cabinet
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)

    mock_sm = _MockSessionMaker(session)
    deactivate = AsyncMock()
    activate = AsyncMock(return_value=True)
    shop_menu_call = AsyncMock()
    shop_menu_ctor = MagicMock(return_value=shop_menu_call)

    with (
        patch("app.client_bot.user_interface.handlers.start.start.sm", mock_sm),
        patch(
            "app.client_bot.user_interface.handlers.start.start.deactivate_cabinet_atomic_with_user_trackers",
            deactivate,
        ),
        patch("app.client_bot.user_interface.handlers.start.start.activate_cabinet", activate),
        patch("app.client_bot.user_interface.handlers.start.start.ShopMenu", shop_menu_ctor),
    ):
        await toggle_cabinet_active_handler(callback, callback_data, bot, state)

    activate.assert_awaited_once_with("shop_2")
    deactivate.assert_not_awaited()
    shop_menu_call.assert_awaited_once()
    bot.send_message.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_toggle_cabinet_active_sends_not_found_when_access_missing() -> None:
    callback = _build_callback()
    callback_data = _build_callback_data()
    bot = AsyncMock()
    state = AsyncMock()

    result = MagicMock()
    result.unique.return_value.scalar_one_or_none.return_value = None
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    mock_sm = _MockSessionMaker(session)

    with patch("app.client_bot.user_interface.handlers.start.start.sm", mock_sm):
        await toggle_cabinet_active_handler(callback, callback_data, bot, state)

    bot.send_message.assert_awaited_once_with(202, "Магазин не найден или нет доступа.")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_toggle_cabinet_active_sends_error_when_deactivate_failed() -> None:
    callback = _build_callback()
    callback_data = _build_callback_data()
    bot = AsyncMock()
    state = AsyncMock()

    wb_user_cabinet = SimpleNamespace(
        wb_cabinet=SimpleNamespace(shop_id="shop_3", active=True)
    )
    result = MagicMock()
    result.unique.return_value.scalar_one_or_none.return_value = wb_user_cabinet
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    mock_sm = _MockSessionMaker(session)

    deactivate = AsyncMock(return_value=False)
    shop_menu_ctor = MagicMock()
    with (
        patch("app.client_bot.user_interface.handlers.start.start.sm", mock_sm),
        patch(
            "app.client_bot.user_interface.handlers.start.start.deactivate_cabinet_atomic_with_user_trackers",
            deactivate,
        ),
        patch("app.client_bot.user_interface.handlers.start.start.ShopMenu", shop_menu_ctor),
    ):
        await toggle_cabinet_active_handler(callback, callback_data, bot, state)

    bot.send_message.assert_awaited_once_with(202, "Не удалось деактивировать магазин.")
    shop_menu_ctor.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_toggle_cabinet_active_sends_error_when_activate_failed() -> None:
    callback = _build_callback()
    callback_data = _build_callback_data()
    bot = AsyncMock()
    state = AsyncMock()

    wb_user_cabinet = SimpleNamespace(
        wb_cabinet=SimpleNamespace(shop_id="shop_4", active=False)
    )
    result = MagicMock()
    result.unique.return_value.scalar_one_or_none.return_value = wb_user_cabinet
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    mock_sm = _MockSessionMaker(session)

    activate = AsyncMock(return_value=False)
    shop_menu_ctor = MagicMock()
    with (
        patch("app.client_bot.user_interface.handlers.start.start.sm", mock_sm),
        patch("app.client_bot.user_interface.handlers.start.start.activate_cabinet", activate),
        patch("app.client_bot.user_interface.handlers.start.start.ShopMenu", shop_menu_ctor),
    ):
        await toggle_cabinet_active_handler(callback, callback_data, bot, state)

    bot.send_message.assert_awaited_once_with(202, "Не удалось активировать магазин.")
    shop_menu_ctor.assert_not_called()

