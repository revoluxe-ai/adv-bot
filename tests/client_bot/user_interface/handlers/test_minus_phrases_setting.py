"""Integration tests for the campaign minus-phrase settings handlers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.user_interface.handlers.adv_setting import (
    back_from_minus_phrases_setting,
    open_minus_phrases_setting_screen,
    toggle_minus_phrases_setting,
)
from app.client_bot.user_interface.views import callbacks
from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet
from app.utils.db.models import User
from tests.factories import AdvSettingFactory, WBCabinetFactory

_MINUS_PHRASES_OWNER_TELEGRAM_ID = 9_200_002

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.destructive_local]


class _MockSessionMaker:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def __call__(self, read_only: bool = False) -> "_MockSessionMaker":
        return self

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(self, *args: object) -> None:
        pass


def _callback(
    chat_id: int = 404,
    telegram_user_id: int = _MINUS_PHRASES_OWNER_TELEGRAM_ID,
) -> SimpleNamespace:
    return SimpleNamespace(
        message=SimpleNamespace(chat=SimpleNamespace(id=chat_id)),
        from_user=SimpleNamespace(id=telegram_user_id),
    )


async def _create_adv_with_owner(
    async_session: AsyncSession,
) -> tuple[AdvSetting, WBUserCabinet]:
    wb_cabinet = WBCabinetFactory.build(shop_id="shop-minus-setting", active=True, demo=False)
    user = User(
        user_telegram_id=_MINUS_PHRASES_OWNER_TELEGRAM_ID,
        username="minus_phrases_owner",
        passed_gate=True,
    )
    async_session.add(user)
    await async_session.flush()
    wb_user_cabinet = WBUserCabinet(
        user_id=user.id,
        wb_cabinet=wb_cabinet,
        name="minus-setting-shop",
    )
    adv = AdvSettingFactory.build(
        id=4040,
        adv_id=987654321,
        name="minus-setting-adv",
        wb_cabinet=wb_cabinet,
        active_status="started",
        bot_active=False,
        bidder_active=True,
        bidder_for_auto=True,
        auto_update_white_list=True,
        auto_update_target_place=True,
        auto_update_minus_phrases=False,
    )
    async_session.add_all([wb_cabinet, wb_user_cabinet, adv])
    await async_session.flush()
    return adv, wb_user_cabinet


@pytest.mark.asyncio
async def test_open_minus_phrases_setting_screen_renders_dedicated_view(
    async_session: AsyncSession,
) -> None:
    adv, wb_user_cabinet = await _create_adv_with_owner(async_session)
    bot = AsyncMock()
    screen_call = AsyncMock()

    with (
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting._get_wb_user_cabinet_or_none",
            AsyncMock(return_value=wb_user_cabinet),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting._get_adv_setting",
            AsyncMock(return_value=adv),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.MinusPhrasesSettingScreen",
            MagicMock(return_value=screen_call),
        ) as screen_ctor,
    ):
        await open_minus_phrases_setting_screen(
            _callback(),
            callbacks.MinusPhrasesSetting(
                action="open",
                adv_setting_original_id=adv.id,
                wb_user_cabinet_original_id=wb_user_cabinet.id,
            ),
            bot,
        )

    screen_ctor.assert_called_once()
    screen_call.assert_awaited_once()


@pytest.mark.asyncio
async def test_toggle_minus_phrases_setting_changes_only_dedicated_flag(
    async_session: AsyncSession,
) -> None:
    adv, wb_user_cabinet = await _create_adv_with_owner(async_session)
    adv_id = adv.id
    bot = AsyncMock()
    screen_call = AsyncMock()

    with (
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.sm",
            _MockSessionMaker(async_session),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.MinusPhrasesSettingScreen",
            MagicMock(return_value=screen_call),
        ),
    ):
        await toggle_minus_phrases_setting(
            _callback(),
            callbacks.MinusPhrasesSetting(
                action="on",
                adv_setting_original_id=adv.id,
                wb_user_cabinet_original_id=wb_user_cabinet.id,
            ),
            bot,
        )

    async_session.expire_all()
    updated = (
        await async_session.execute(select(AdvSetting).where(AdvSetting.id == adv_id))
    ).scalar_one()

    assert updated.auto_update_minus_phrases is True
    assert updated.bot_active is False
    assert updated.bidder_active is True
    assert updated.bidder_for_auto is True
    assert updated.auto_update_white_list is True
    assert updated.auto_update_target_place is True
    screen_call.assert_awaited_once()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_back_from_minus_phrases_setting_returns_to_campaign_menu(
    async_session: AsyncSession,
) -> None:
    adv, wb_user_cabinet = await _create_adv_with_owner(async_session)
    bot = AsyncMock()
    menu_call = AsyncMock()

    with (
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting._get_wb_user_cabinet_or_none",
            AsyncMock(return_value=wb_user_cabinet),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting._get_adv_setting",
            AsyncMock(return_value=adv),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.AdvSettingMenu",
            MagicMock(return_value=menu_call),
        ) as menu_ctor,
    ):
        await back_from_minus_phrases_setting(
            _callback(),
            callbacks.MinusPhrasesSetting(
                action="back",
                adv_setting_original_id=adv.id,
                wb_user_cabinet_original_id=wb_user_cabinet.id,
            ),
            bot,
        )

    menu_ctor.assert_called_once_with(bot, 404, wb_user_cabinet, adv)
    menu_call.assert_awaited_once()
