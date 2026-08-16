"""PBH-001: billing:processed / redis short-circuit must not block mid-UTC-day charge.

Invariant INV/BUGCASE-FAIR-LEG-REDIS-PBH-001:
- no_active_campaigns and zero_price MUST NOT set billing:processed for the UTC day
- stale redis accelerator MUST NOT skip latch sampling or charge when DB has no debit
"""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fakeredis.aioredis import FakeRedis
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing import billing
from app.modules.billing.leg_latch import LegLatchManager
from app.modules.billing.pricer import Pricer
from app.modules.billing.pricer.pricer import TariffDetails, TariffMode
from app.modules.common_slaves.wildberries.models import AdvSetting

pytestmark = pytest.mark.asyncio


def _tariff_details(total_per_day: float, count: float = 1.0) -> TariffDetails:
    return TariffDetails(
        mode=TariffMode.AUTO,
        count=count,
        price_per_adv=100.0,
        total_per_month=100.0,
        total_per_day=total_per_day,
    )


class _TrackingRedisBillingManager:
    """Fake Redis manager tracking billing:processed writes and optional stale flag."""

    def __init__(self, *, stale_flag: bool = False) -> None:
        self._client = FakeRedis()
        self._stale_flag = stale_flag
        self.set_billing_calls: list[tuple[int, datetime.datetime]] = []

    async def get_billing_process_for_day(
        self, cabinet_id: int, current_dt: datetime.datetime
    ) -> bool:
        return self._stale_flag

    async def set_billing_process_for_day(
        self, cabinet_id: int, current_dt: datetime.datetime
    ) -> None:
        self.set_billing_calls.append((cabinet_id, current_dt))

    async def set_last_charge_at(
        self, shop_id: str, current_dt: datetime.datetime
    ) -> None:
        return None

    def leg_latch(self) -> LegLatchManager:
        return LegLatchManager(self._client)


def _adv_setting(
    *,
    id_: int,
    adv_id: int,
    bot_active: bool,
    active_status: str,
    search_adv_id: int | None = None,
) -> MagicMock:
    adv = MagicMock(spec=AdvSetting)
    adv.id = id_
    adv.adv_id = adv_id
    adv.search_adv_id = search_adv_id
    adv.active_status = active_status
    adv.bot_active = bot_active
    adv.auto_update_white_list = True
    adv.auto_update_target_place = True
    adv.wb_cabinet_id = 100
    adv.payments = []
    return adv


def _make_cabinet(*, advs: list[MagicMock], bonus: float = 500.0) -> MagicMock:
    cab = MagicMock()
    cab.id = 100
    cab.shop_id = "test_shop_id"
    cab.calculated_bonus = bonus
    cab.calculated_balance = 0.0
    cab.balance_payments = []
    cab.bonus_payments = []
    cab.adv_settings = advs
    cab.balance_went_negative_at = None
    return cab


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = 0
    return session


@pytest.fixture
def mock_pricer() -> AsyncMock:
    pr = AsyncMock(spec=Pricer)
    pr.get_tariff_details.return_value = _tariff_details(100.0, count=1.0)
    return pr


async def test_pbh001_zero_price_does_not_set_billing_processed(
    mock_session: AsyncMock, mock_pricer: AsyncMock
) -> None:
    """Early zero_price pass must leave billing:processed unset for later hourly passes."""
    anchor = _adv_setting(
        id_=1, adv_id=100, bot_active=True, active_status="paused"
    )
    cab = _make_cabinet(advs=[anchor])
    mock_pricer.get_tariff_details.return_value = _tariff_details(0.0, count=0.0)
    redis_mgr = _TrackingRedisBillingManager()

    with patch.object(
        billing, "_load_cabinet_with_relations", new=AsyncMock(return_value=cab)
    ), patch.object(billing, "_safe_commit", new=AsyncMock(return_value=True)):
        result = await billing.__process_single_cabinet(
            session=mock_session,
            cabinet_id=cab.id,
            current_dt=datetime.datetime(2024, 6, 15, 8, 0, 0),
            pricer=mock_pricer,
            redis_manager=redis_mgr,  # type: ignore[arg-type]
        )

    assert result["reason"] == "zero_price"
    assert redis_mgr.set_billing_calls == []


async def test_pbh001_no_active_campaigns_does_not_set_billing_processed(
    mock_session: AsyncMock, mock_pricer: AsyncMock
) -> None:
    """bot_active=False early pass must not latch billing:processed before bot connects."""
    search = _adv_setting(
        id_=2, adv_id=200, bot_active=False, active_status="started"
    )
    anchor = _adv_setting(
        id_=1,
        adv_id=100,
        bot_active=False,
        active_status="started",
        search_adv_id=200,
    )
    cab = _make_cabinet(advs=[anchor, search])
    redis_mgr = _TrackingRedisBillingManager()

    with patch.object(
        billing, "_load_cabinet_with_relations", new=AsyncMock(return_value=cab)
    ), patch.object(billing, "_safe_commit", new=AsyncMock(return_value=True)):
        result = await billing.__process_single_cabinet(
            session=mock_session,
            cabinet_id=cab.id,
            current_dt=datetime.datetime(2024, 6, 15, 8, 0, 0),
            pricer=mock_pricer,
            redis_manager=redis_mgr,  # type: ignore[arg-type]
        )

    assert result["reason"] == "no_active_campaigns"
    assert redis_mgr.set_billing_calls == []


async def test_pbh001_stale_redis_flag_does_not_block_charge_same_utc_day(
    mock_session: AsyncMock, mock_pricer: AsyncMock
) -> None:
    """Stale billing:processed from zero_price must not redis_flag_skip a later charge."""
    search = _adv_setting(
        id_=2, adv_id=200, bot_active=False, active_status="started"
    )
    anchor = _adv_setting(
        id_=1,
        adv_id=100,
        bot_active=True,
        active_status="started",
        search_adv_id=200,
    )
    cab = _make_cabinet(advs=[anchor, search])
    redis_mgr = _TrackingRedisBillingManager(stale_flag=True)

    with patch.object(
        billing, "_load_cabinet_with_relations", new=AsyncMock(return_value=cab)
    ), patch.object(billing, "_safe_commit", new=AsyncMock(return_value=True)):
        result = await billing.__process_single_cabinet(
            session=mock_session,
            cabinet_id=cab.id,
            current_dt=datetime.datetime(2024, 6, 15, 14, 0, 0),
            pricer=mock_pricer,
            redis_manager=redis_mgr,  # type: ignore[arg-type]
        )

    assert result["reason"] != "redis_flag_skip"
    assert result["payment_successful"] is True
