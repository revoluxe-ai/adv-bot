"""Paid regression: pricer учитывает только bot_active кампании."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.billing.pricer.pricer import Pricer

pytestmark = [pytest.mark.unit, pytest.mark.paid_regression, pytest.mark.asyncio]


@pytest.mark.asyncio
async def test_pricer_tariff_zero_when_no_bot_active_advs() -> None:
    session = AsyncMock()

    async def _fake_fetch(
        _session: object, _shop_id: str
    ) -> list[object]:
        return []

    with patch.object(
        Pricer, "fetch_bot_active_advs", staticmethod(_fake_fetch)
    ):
        details = await Pricer().get_tariff_details(session=session, shop_id="shop-1")

    assert details.count == 0
