"""Integration proof for the white-list mode PG WRITE seam.

Живой ``async_session`` используется для записи и повторного чтения
``AdvSetting.white_list_mode``. Запуск требует отдельной live-авторизации.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.ui_access import UiAccessMode
from app.client_bot.user_interface.handlers.white_list_mode_toggle import (
    toggle_white_list_mode_in_session,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from app.modules.common_slaves.wildberries.models.white_list_mode import WhiteListMode

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
    pytest.mark.destructive_local,
]


async def test_toggle_white_list_mode_in_session_persists_and_rereads(
    async_session: AsyncSession,
) -> None:
    """WRITE child updates the mode and a fresh query observes the persisted value."""
    cabinet = WBCabinet(
        shop_id=f"white_list_seam_{uuid.uuid4().hex[:10]}",
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
        expiration_time=datetime.utcnow() + timedelta(days=7),
    )
    async_session.add(cabinet)
    await async_session.flush()
    adv = AdvSetting(
        adv_id=991001,
        name="white-list-seam",
        wb_cabinet_id=cabinet.id,
        active_status="started",
        bot_active=False,
        plan_for_sales_for_day=1,
        target_price_for_order=100.0,
        max_price_for_order=150.0,
        max_cpm=1000,
        cpm=100,
    )
    async_session.add(adv)
    await async_session.flush()
    original_adv_id = adv.id

    callback = SimpleNamespace(
        message=SimpleNamespace(chat=SimpleNamespace(id=991001))
    )
    callback_data = SimpleNamespace(
        new_mode=WhiteListMode.ACTIVE_ONLY_WHITE_LIST.name,
        adv_setting_original_id=original_adv_id,
    )
    bot = AsyncMock()
    menu = MagicMock(return_value=AsyncMock())

    with (
        patch(
            "app.client_bot.user_interface.handlers.white_list_mode_toggle"
            "._resolve_white_list_mode_ui_access",
            return_value=UiAccessMode.FREE,
        ),
        patch(
            "app.client_bot.user_interface.handlers.white_list_mode_toggle"
            ".WhiteListModeMenuMessage",
            menu,
        ),
    ):
        await toggle_white_list_mode_in_session(
            async_session,
            callback,
            callback_data,
            bot,
        )

    await async_session.commit()
    async_session.expire_all()
    stored_mode = await async_session.scalar(
        select(AdvSetting.white_list_mode).where(AdvSetting.id == original_adv_id)
    )
    assert stored_mode == WhiteListMode.ACTIVE_ONLY_WHITE_LIST
