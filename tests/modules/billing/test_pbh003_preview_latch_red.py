"""PBH-003 RED: tariff preview paths MUST thread leg_latch+utc_date like shop_menu.

Invariant: get_price_for_day_for_shop and latch-backed get_tariff_details MUST agree
after same UTC-day leg started then paused; preview without latch underestimates.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fakeredis.aioredis import FakeRedis

from app.modules.billing.leg_latch import AdvPaymentLegSlot, LegLatchManager
from app.modules.billing.pricer.pricer import Pricer, TariffDetails, TariffMode
from tests.modules.billing.test_pricer_tariffs import DummyAdv, _patch_metering_advs

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _tariff_details(*, count: float, total_per_day: float) -> TariffDetails:
    return TariffDetails(
        mode=TariffMode.AUTO,
        count=count,
        price_per_adv=100.0,
        total_per_month=count * 100.0,
        total_per_day=total_per_day,
    )


async def test_get_price_for_day_for_shop_forwards_latch_to_get_tariff_details() -> None:
    """PBH-003 / TEST-PBH-003-001: daily price wrapper MUST pass latch+utc_date."""
    pricer = Pricer()
    mock_session = AsyncMock()
    captured: dict[str, object] = {}

    async def _spy_get_tariff_details(
        session: object,
        shop_id: str,
        **kwargs: object,
    ) -> TariffDetails:
        captured["shop_id"] = shop_id
        captured["leg_latch"] = kwargs.get("leg_latch")
        captured["utc_date"] = kwargs.get("utc_date")
        return _tariff_details(count=1.0, total_per_day=3.33)

    with patch.object(pricer, "get_tariff_details", side_effect=_spy_get_tariff_details):
        await pricer.get_price_for_day_for_shop(mock_session, "shop_latch")

    assert captured["shop_id"] == "shop_latch"
    assert captured["leg_latch"] is not None
    assert captured["utc_date"] is not None


async def test_preview_with_latch_higher_than_instant_after_same_day_pause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PBH-003 / TEST-PBH-003-002: latch preview > instant-only after pause same UTC-day."""
    utc_day = date(2024, 6, 15)
    latch = LegLatchManager(FakeRedis())

    search = DummyAdv(
        id=2,
        adv_id=200,
        bot_active=False,
        active_status="paused",
        search_adv_id=None,
        auto_update_white_list=True,
    )
    anchor = DummyAdv(
        id=1,
        adv_id=100,
        bot_active=True,
        active_status="started",
        search_adv_id=200,
        auto_update_white_list=True,
    )
    _patch_metering_advs(monkeypatch, [anchor, search])

    await latch.record_sample(1, AdvPaymentLegSlot.AUTO_LEG, 0.5, utc_day)
    await latch.record_sample(1, AdvPaymentLegSlot.SEARCH_LEG, 0.5, utc_day)

    pricer = Pricer()
    instant_details = await pricer.get_tariff_details(None, "shop_pause")  # type: ignore[arg-type]
    latch_details = await pricer.get_tariff_details(
        None,
        "shop_pause",
        leg_latch=latch,
        utc_date=utc_day,
    )  # type: ignore[arg-type]
    preview_day_price = await pricer.get_price_for_day_for_shop(
        None,
        "shop_pause",
    )  # type: ignore[arg-type]

    assert instant_details.count == pytest.approx(0.5)
    assert latch_details.count == pytest.approx(1.0)
    assert latch_details.count > instant_details.count
    assert preview_day_price == pytest.approx(latch_details.total_per_day)
