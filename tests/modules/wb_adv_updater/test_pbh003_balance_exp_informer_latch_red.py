"""PBH-003 RED: balance_exp_informer MUST use latch-backed daily spend preview."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.wb_adv_updater.modules.balance_exp_informer.service import (
    BalanceReminderService,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def test_balance_exp_informer_passes_leg_latch_and_utc_date() -> None:
    """PBH-003 / TEST-PBH-003-003: informer daily spend MUST thread latch+utc_date."""
    service = BalanceReminderService(
        session_factory=MagicMock(),
        event_manager=MagicMock(),
    )
    captured: dict[str, object] = {}
    fixed_date = date(2025, 6, 15)

    async def _spy_get_price_for_day(
        session: object,
        shop_id: str,
        *,
        leg_latch: object | None = None,
        utc_date: date | None = None,
    ) -> float:
        captured["shop_id"] = shop_id
        captured["leg_latch"] = leg_latch
        captured["utc_date"] = utc_date
        return 10.0

    service._pricer = MagicMock()
    service._pricer.get_price_for_day_for_shop = AsyncMock(
        side_effect=_spy_get_price_for_day
    )

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    async def _one_batch(session: object, batch_size: int = 10):
        yield [(1, 123456789, 100, "shop_latch", "Test Shop")]

    with patch(
        "app.modules.wb_adv_updater.modules.balance_exp_informer.service.iter_user_cabinets_batches",
        side_effect=_one_batch,
    ), patch(
        "app.modules.wb_adv_updater.modules.balance_exp_informer.service.get_cabinet_balance",
        new_callable=AsyncMock,
        return_value=(50.0, 0.0),
    ):
        await service._create_pending(mock_session, fixed_date)

    assert captured["shop_id"] == "shop_latch"
    assert captured["leg_latch"] is not None
    assert captured["utc_date"] == fixed_date
    service._pricer.get_price_for_day_for_shop.assert_awaited_once()
