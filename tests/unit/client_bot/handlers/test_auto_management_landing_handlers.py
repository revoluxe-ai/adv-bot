"""Unit tests for auto-management landing handlers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers.adv_setting import (
    back_from_auto_management_landing,
    open_auto_management_how_it_works,
    open_auto_management_landing,
)
from app.client_bot.user_interface.views import callbacks

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _callback(chat_id: int = 404) -> SimpleNamespace:
    return SimpleNamespace(message=SimpleNamespace(chat=SimpleNamespace(id=chat_id)))


def _callback_data() -> callbacks.AutoManagementLanding:
    return callbacks.AutoManagementLanding(
        action="open",
        adv_setting_original_id=77,
        wb_user_cabinet_original_id=55,
    )


async def test_open_status_button_shows_landing_and_does_not_toggle_bot_active() -> None:
    bot = AsyncMock()
    wb_user_cabinet = SimpleNamespace(id=55, wb_cabinet_id=155)
    adv_setting = SimpleNamespace(id=77, bot_active=False)
    landing_call = AsyncMock()

    with (
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting._get_wb_user_cabinet_or_none",
            AsyncMock(return_value=wb_user_cabinet),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting._get_adv_setting_or_none",
            AsyncMock(return_value=adv_setting),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.AutoManagementLanding",
            MagicMock(return_value=landing_call),
        ) as landing_ctor,
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.AdvSettingMenu",
        ) as adv_menu_ctor,
    ):
        await open_auto_management_landing(_callback(), _callback_data(), bot)

    assert adv_setting.bot_active is False
    landing_ctor.assert_called_once_with(bot, 404, wb_user_cabinet, adv_setting)
    landing_call.assert_awaited_once()
    adv_menu_ctor.assert_not_called()


async def test_how_it_works_handler_opens_details_screen() -> None:
    bot = AsyncMock()
    wb_user_cabinet = SimpleNamespace(id=55, wb_cabinet_id=155)
    adv_setting = SimpleNamespace(id=77, bot_active=True)
    screen_call = AsyncMock()

    with (
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting._get_wb_user_cabinet_or_none",
            AsyncMock(return_value=wb_user_cabinet),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting._get_adv_setting_or_none",
            AsyncMock(return_value=adv_setting),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.AutoManagementHowItWorks",
            MagicMock(return_value=screen_call),
        ) as screen_ctor,
    ):
        await open_auto_management_how_it_works(
            _callback(),
            callbacks.AutoManagementLanding(
                action="how",
                adv_setting_original_id=77,
                wb_user_cabinet_original_id=55,
            ),
            bot,
        )

    screen_ctor.assert_called_once_with(bot, 404, wb_user_cabinet, adv_setting)
    screen_call.assert_awaited_once()


async def test_back_handler_returns_to_campaign_menu() -> None:
    bot = AsyncMock()
    wb_user_cabinet = SimpleNamespace(id=55, wb_cabinet_id=155)
    adv_setting = SimpleNamespace(id=77, bot_active=True)
    menu_call = AsyncMock()

    with (
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting._get_wb_user_cabinet_or_none",
            AsyncMock(return_value=wb_user_cabinet),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting._get_adv_setting_or_none",
            AsyncMock(return_value=adv_setting),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.AdvSettingMenu",
            MagicMock(return_value=menu_call),
        ) as menu_ctor,
    ):
        await back_from_auto_management_landing(
            _callback(),
            callbacks.AutoManagementLanding(
                action="back",
                adv_setting_original_id=77,
                wb_user_cabinet_original_id=55,
            ),
            bot,
        )

    menu_ctor.assert_called_once_with(bot, 404, wb_user_cabinet, adv_setting)
    menu_call.assert_awaited_once()


async def test_back_from_how_it_works_returns_to_landing() -> None:
    bot = AsyncMock()
    wb_user_cabinet = SimpleNamespace(id=55, wb_cabinet_id=155)
    adv_setting = SimpleNamespace(id=77, bot_active=False)
    landing_call = AsyncMock()
    how_it_works_call = AsyncMock()

    with (
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting._get_wb_user_cabinet_or_none",
            AsyncMock(return_value=wb_user_cabinet),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting._get_adv_setting_or_none",
            AsyncMock(return_value=adv_setting),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.AutoManagementLanding",
            MagicMock(return_value=landing_call),
        ) as landing_ctor,
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.AutoManagementHowItWorks",
            MagicMock(return_value=how_it_works_call),
        ) as how_ctor,
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.AdvSettingMenu",
        ) as adv_menu_ctor,
    ):
        await open_auto_management_how_it_works(
            _callback(),
            callbacks.AutoManagementLanding(
                action="how",
                adv_setting_original_id=77,
                wb_user_cabinet_original_id=55,
            ),
            bot,
        )
        await open_auto_management_landing(
            _callback(),
            callbacks.AutoManagementLanding(
                action="open",
                adv_setting_original_id=77,
                wb_user_cabinet_original_id=55,
            ),
            bot,
        )

    assert landing_ctor.call_count == 1
    landing_ctor.assert_called_once_with(bot, 404, wb_user_cabinet, adv_setting)
    how_ctor.assert_called_once_with(bot, 404, wb_user_cabinet, adv_setting)
    landing_call.assert_awaited_once()
    how_it_works_call.assert_awaited_once()
    adv_menu_ctor.assert_not_called()


async def test_open_status_button_raises_runtime_error_when_cabinet_missing() -> None:
    """Проверяет, что ошибка реального резолвера доходит до UI без рендера."""
    bot = AsyncMock()

    with (
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting._get_wb_user_cabinet",
            AsyncMock(
                side_effect=RuntimeError(
                    "WBUserCabinet not found for original_id=55"
                )
            ),
        ) as cabinet_resolver,
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.AutoManagementLanding"
        ) as landing_ctor,
    ):
        with pytest.raises(
            RuntimeError,
            match=r"^WBUserCabinet not found for original_id=55$",
        ):
            await open_auto_management_landing(_callback(), _callback_data(), bot)

    cabinet_resolver.assert_awaited_once_with(55)
    landing_ctor.assert_not_called()
    bot.send_message.assert_not_awaited()


async def test_back_handler_raises_runtime_error_when_adv_missing() -> None:
    """Проверяет, что ошибка реального резолвера не открывает меню кампании."""
    bot = AsyncMock()
    wb_user_cabinet = SimpleNamespace(id=55, wb_cabinet_id=155)

    with (
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting._get_wb_user_cabinet",
            AsyncMock(return_value=wb_user_cabinet),
        ) as cabinet_resolver,
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting._get_adv_setting",
            AsyncMock(
                side_effect=RuntimeError("AdvSetting not found for original_id=77")
            ),
        ) as adv_resolver,
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.AdvSettingMenu"
        ) as menu_ctor,
    ):
        with pytest.raises(
            RuntimeError,
            match=r"^AdvSetting not found for original_id=77$",
        ):
            await back_from_auto_management_landing(
                _callback(),
                callbacks.AutoManagementLanding(
                    action="back",
                    adv_setting_original_id=77,
                    wb_user_cabinet_original_id=55,
                ),
                bot,
            )

    cabinet_resolver.assert_awaited_once_with(55)
    adv_resolver.assert_awaited_once_with(77)
    menu_ctor.assert_not_called()
    bot.send_message.assert_not_awaited()
