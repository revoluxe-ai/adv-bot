"""Integration tests for DB effects of rebind_adv_campaign_ids handlers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.user_interface.handlers import rebind_adv_campaign_ids
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

MODULE = "app.client_bot.user_interface.handlers.rebind_adv_campaign_ids"


class MockSessionMaker:
    """Mock session maker so handler uses the integration session."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def __call__(self, read_only: bool = False) -> "MockSessionMaker":
        return self

    async def __aenter__(self) -> AsyncSession:
        return self.session

    async def __aexit__(self, *args: object) -> None:
        pass


async def test_apply_search_adv_id_creates_search_row(
    async_session: AsyncSession,
) -> None:
    """Rebinding search_adv_id creates the missing legacy search row."""
    wb_cabinet = WBCabinet(
        shop_id="test_rebind_search_row",
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
        default_max_cpm=500,
    )
    async_session.add(wb_cabinet)
    await async_session.flush()

    main_adv = AdvSetting(
        adv_id=37848355,
        name="Main campaign",
        max_place=1,
        max_cpm=500,
        active_status="started",
        wb_cabinet_id=wb_cabinet.id,
        bidder_active=False,
        parsing_active=False,
        bot_active=True,
        reset_place=True,
        type=8,
        nmids=[1096147565],
        hard_min_ctr=0.1,
        _search_adv_id=None,
    )
    async_session.add(main_adv)
    await async_session.commit()

    state = MagicMock()
    state.get_data = AsyncMock(
        return_value={
            "adv_setting_original_id": main_adv.id,
            "wb_user_cabinet_original_id": 777,
        }
    )
    state.clear = AsyncMock()

    message = MagicMock()
    message.chat.id = 1001
    message.text = "37848369"
    message.from_user.id = 999
    message.answer = AsyncMock()

    bot = MagicMock()

    mock_sm = MockSessionMaker(async_session)
    with (
        patch(f"{MODULE}.sm", mock_sm),
        patch(
            f"{MODULE}._validate_wb_campaign_kind",
            new=AsyncMock(return_value=(True, "")),
        ),
        patch(f"{MODULE}._get_wb_user_cabinet_for_adv_and_telegram", new=AsyncMock(return_value=None)),
        patch(f"{MODULE}._reload_adv_setting_menu", new=AsyncMock()),
    ):
        await rebind_adv_campaign_ids.apply_search_adv_id(message, bot, state)

    refreshed_main = await async_session.get(AdvSetting, main_adv.id)
    assert refreshed_main is not None
    assert refreshed_main.search_adv_id == 37848369

    search_result = await async_session.execute(
        select(AdvSetting).where(AdvSetting.adv_id == 37848369)
    )
    search_row = search_result.scalar_one_or_none()
    assert search_row is not None
    assert search_row.wb_cabinet_id == wb_cabinet.id
    assert search_row.nmids == [1096147565]
    assert search_row.active_status == "unknown"
