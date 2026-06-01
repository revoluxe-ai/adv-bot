from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.client_bot.user_interface.helpers.wb_user_cabinet import (
    get_wb_user_cabinet_for_adv_and_telegram,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_get_wb_user_cabinet_for_adv_and_telegram_returns_single_row() -> None:
    adv_setting = MagicMock()
    adv_setting.wb_cabinet_id = 42
    expected = MagicMock()
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: expected))

    result = await get_wb_user_cabinet_for_adv_and_telegram(
        session,
        adv_setting,
        user_telegram_id=777,
    )

    assert result is expected
    session.execute.assert_awaited_once()
