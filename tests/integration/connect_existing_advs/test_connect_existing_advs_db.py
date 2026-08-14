"""Integration tests for connect_existing_advs: DB persistence of AdvSetting."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.user_interface.handlers import connect_existing_advs
from app.client_bot.user_interface.views.messages.main_adv_setting_menu import (
    adv_setting_menu,
)
from app.client_bot.user_interface.views import callbacks
from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.utils.db.models import User

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.destructive_local]

MODULE = "app.client_bot.user_interface.handlers.connect_existing_advs"


class MockSessionMaker:
    """Mock session maker so handler uses test session."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def __call__(self, read_only: bool = False) -> "MockSessionMaker":
        return self

    async def __aenter__(self) -> AsyncSession:
        return self.session

    async def __aexit__(self, *args: object) -> None:
        pass


@pytest.mark.integration
@pytest.mark.asyncio
async def  test_connect_existing_confirm_type2_creates_adv_setting_in_db(
    async_session: AsyncSession,
) -> None:
    """confirm_type2 persists rows even when the auction candidate has no name."""
    user = User(user_telegram_id=88881, username="ce_test_user", passed_gate=True)
    async_session.add(user)
    await async_session.flush()

    wb_cabinet = WBCabinet(
        shop_id=f"test_ce_{uuid.uuid4().hex}",
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
        default_max_cpm=500,
    )
    async_session.add(wb_cabinet)
    await async_session.flush()

    wb_user_cabinet = WBUserCabinet(
        user_id=user.id,
        wb_cabinet_id=wb_cabinet.id,
        name="CE Test Cabinet",
    )
    async_session.add(wb_user_cabinet)
    await async_session.flush()

    nmid = 100500
    chosen_auction_id = 10
    chosen_auto_id = 20

    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(
        return_value={
            "nmid": nmid,
            "wb_cabinet_id": wb_cabinet.id,
            "chosen_auction_adv_id": chosen_auction_id,
            "card_name": f"NM {nmid}",
            "auction_candidates": [{"id": chosen_auction_id, "status": 4}],
        }
    )
    state.clear = AsyncMock()
    callback = MagicMock()
    callback.message = MagicMock()
    callback.message.chat = MagicMock()
    callback.message.chat.id = 99999
    callback.answer = AsyncMock()
    callback_data = callbacks.ConnectExistingConfirmType2(adv_id=chosen_auto_id)

    mock_sm = MockSessionMaker(async_session)
    with patch(f"{MODULE}.sm", mock_sm), patch(
        "app.modules.adv_creator.backend.main_manager.sm", mock_sm
    ):
        await connect_existing_advs.connect_existing_confirm_type2(
            callback, callback_data, bot, state
        )

    main_stmt = select(AdvSetting).where(AdvSetting.adv_id == chosen_auto_id)
    main_result = await async_session.execute(main_stmt)
    row = main_result.scalar_one_or_none()
    assert row is not None
    assert row.adv_id == chosen_auto_id
    assert row.wb_cabinet_id == wb_cabinet.id
    assert row._search_adv_id == chosen_auction_id
    # name = get_name_for_adv(nmid, card_name, "complex") -> "100500 NM 100500" when card_name="NM 100500"
    assert row.name == f"{nmid} NM {nmid}"
    assert row.nmids == [nmid]
    assert row.active_status == "started"
    assert row.type == 8

    search_stmt = select(AdvSetting).where(AdvSetting.adv_id == chosen_auction_id)
    search_result = await async_session.execute(search_stmt)
    search_row = search_result.scalar_one_or_none()
    assert search_row is not None
    assert search_row.wb_cabinet_id == wb_cabinet.id
    assert search_row.nmids == [nmid]
    assert search_row.active_status == "ready_for_start"

    with patch.object(adv_setting_menu, "sm", mock_sm):
        status = await adv_setting_menu.AdvSettingMenu._get_status_auction(
            chosen_auction_id
        )
    assert status == "ready_for_start"
