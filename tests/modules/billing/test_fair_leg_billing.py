"""Orchestration unit-тесты fair leg billing: AdvPayment split и legacy dedup (tasks 6.3–6.4)."""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fakeredis.aioredis import FakeRedis
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing import billing
from app.modules.billing.leg_latch import LegLatchManager
from app.modules.billing.models import AdvPayment, AdvPaymentLegType
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


class _FakeRedisBillingManager:
    """Минимальный Redis manager: billing flags + реальный leg latch на fakeredis."""

    def __init__(self) -> None:
        self._client = FakeRedis()

    async def get_billing_process_for_day(
        self, cabinet_id: int, current_dt: datetime.datetime
    ) -> bool:
        return False

    async def set_billing_process_for_day(
        self, cabinet_id: int, current_dt: datetime.datetime
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


def _full_active_pair() -> tuple[MagicMock, MagicMock]:
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
    return anchor, search


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


def _collect_adv_payments(mock_session: AsyncMock) -> list[AdvPayment]:
    return [
        call.args[0]
        for call in mock_session.add.call_args_list
        if isinstance(call.args[0], AdvPayment)
    ]


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


async def test_adv_payment_split_two_slots_when_both_billable(
    mock_session: AsyncMock, mock_pricer: AsyncMock
) -> None:
    """6.3 / 7.4: оба billable слота → auto_leg + search_leg, сумма = total_per_day."""
    anchor, search = _full_active_pair()
    cab = _make_cabinet(advs=[anchor, search])
    redis_mgr = _FakeRedisBillingManager()

    with patch.object(
        billing, "_load_cabinet_with_relations", new=AsyncMock(return_value=cab)
    ), patch.object(billing, "_safe_commit", new=AsyncMock(return_value=True)):
        result = await billing.__process_single_cabinet(
            session=mock_session,
            cabinet_id=cab.id,
            current_dt=datetime.datetime(2024, 6, 15, 10, 0, 0),
            pricer=mock_pricer,
            redis_manager=redis_mgr,  # type: ignore[arg-type]
        )

    assert result["payment_successful"] is True
    payments = _collect_adv_payments(mock_session)
    assert len(payments) == 2
    types = {p.type for p in payments}
    assert types == {AdvPaymentLegType.AUTO_LEG.value, AdvPaymentLegType.SEARCH_LEG.value}
    assert sum(p.amount for p in payments) == pytest.approx(100.0)
    assert all(p.adv_setting_id == anchor.id for p in payments)


async def test_adv_payment_single_auto_leg_when_search_paused(
    mock_session: AsyncMock, mock_pricer: AsyncMock
) -> None:
    """6.3 / 7.4 / 7.5: только якорь started → одна auto_leg строка, половина суммы."""
    search = _adv_setting(
        id_=2, adv_id=200, bot_active=False, active_status="paused"
    )
    anchor = _adv_setting(
        id_=1,
        adv_id=100,
        bot_active=True,
        active_status="started",
        search_adv_id=200,
    )
    cab = _make_cabinet(advs=[anchor, search])
    mock_pricer.get_tariff_details.return_value = _tariff_details(50.0, count=0.5)
    redis_mgr = _FakeRedisBillingManager()

    with patch.object(
        billing, "_load_cabinet_with_relations", new=AsyncMock(return_value=cab)
    ), patch.object(billing, "_safe_commit", new=AsyncMock(return_value=True)):
        result = await billing.__process_single_cabinet(
            session=mock_session,
            cabinet_id=cab.id,
            current_dt=datetime.datetime(2024, 6, 15, 10, 0, 0),
            pricer=mock_pricer,
            redis_manager=redis_mgr,  # type: ignore[arg-type]
        )

    assert result["payment_successful"] is True
    payments = _collect_adv_payments(mock_session)
    assert len(payments) == 1
    assert payments[0].type == AdvPaymentLegType.AUTO_LEG.value
    assert payments[0].amount == pytest.approx(50.0)


async def test_legacy_null_adv_payment_blocks_duplicate_split(
    mock_session: AsyncMock,
) -> None:
    """6.4 / S16: legacy AdvPayment (type NULL) → _anchor_has_adv_payment_for_day True."""
    mock_session.scalar.return_value = 1
    has_legacy = await billing._anchor_has_adv_payment_for_day(
        mock_session, anchor_id=42, day=datetime.date(2024, 6, 15)
    )
    assert has_legacy is True


async def test_legacy_null_adv_payment_skips_new_split_rows(
    mock_session: AsyncMock, mock_pricer: AsyncMock
) -> None:
    """6.4: при legacy-записи за день новые split AdvPayment MUST NOT создаваться."""
    anchor, search = _full_active_pair()
    cab = _make_cabinet(advs=[anchor, search])
    redis_mgr = _FakeRedisBillingManager()

    async def _scalar_side_effect(stmt):  # noqa: ANN001
        sql_text = str(stmt)
        if "advpayment" in sql_text.lower():
            return 1
        return 0

    mock_session.scalar = AsyncMock(side_effect=_scalar_side_effect)

    with patch.object(
        billing, "_load_cabinet_with_relations", new=AsyncMock(return_value=cab)
    ), patch.object(billing, "_safe_commit", new=AsyncMock(return_value=True)):
        result = await billing.__process_single_cabinet(
            session=mock_session,
            cabinet_id=cab.id,
            current_dt=datetime.datetime(2024, 6, 15, 10, 0, 0),
            pricer=mock_pricer,
            redis_manager=redis_mgr,  # type: ignore[arg-type]
        )

    assert result["payment_successful"] is True
    payments = _collect_adv_payments(mock_session)
    assert payments == []
