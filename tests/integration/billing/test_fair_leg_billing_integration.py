"""Integration: fair leg-pause billing (tasks 7.1–7.5; destructive PG).

Требует ``ALLOW_DESTRUCTIVE_TEST_DB=1`` и ``@pytest.mark.destructive_local``.
"""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fakeredis.aioredis import FakeRedis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing import billing
from app.modules.billing.leg_latch import AdvPaymentLegSlot, LegLatchManager
from app.modules.billing.leg_metering import (
    record_anchor_latch_samples,
    resolve_metering_anchors,
)
from app.modules.billing.models import AdvPayment, AdvPaymentLegType
from app.modules.billing.pricer.pricer import Pricer, TariffMode
from app.modules.billing.pricer.tariffs import tariffs_for_auto_setting
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
    pytest.mark.destructive_local,
]


class _FakeRedisBillingManager:
    """Redis billing flags + leg latch на fakeredis для integration billing seam."""

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


@pytest.fixture
async def wb_cabinet(async_session: AsyncSession) -> WBCabinet:
    row = await async_session.get(WBCabinet, 1)
    assert row is not None
    row.bonus = 10_000.0
    row.balance = 0.0
    await async_session.flush()
    return row


def _make_search_adv(*, adv_id: int, wb_cabinet_id: int, active_status: str) -> AdvSetting:
    return AdvSetting(
        adv_id=adv_id,
        name=f"search_{adv_id}",
        wb_cabinet_id=wb_cabinet_id,
        active_status=active_status,
        bot_active=False,
    )


def _make_auto_adv(
    *,
    adv_id: int,
    wb_cabinet_id: int,
    search_adv_id: int | None,
    active_status: str,
    wl: bool = True,
    tp: bool = False,
    bot_active: bool = True,
) -> AdvSetting:
    return AdvSetting(
        adv_id=adv_id,
        name=f"auto_{adv_id}",
        wb_cabinet_id=wb_cabinet_id,
        bot_active=bot_active,
        active_status=active_status,
        _search_adv_id=search_adv_id,  # noqa: SLF001
        automatic_version=2,
        auto_update_white_list=wl,
        auto_update_target_place=tp,
    )


def _legacy_full_active_day_total() -> float:
    return Pricer.get_tariff_for_day(float(tariffs_for_auto_setting[1]))


async def test_integration_full_active_matches_legacy_daily_total(
    async_session: AsyncSession,
    wb_cabinet: WBCabinet,
) -> None:
    """7.1 / S15 LEGACY_BASELINE: full-active → дневная сумма = legacy total."""
    search = _make_search_adv(
        adv_id=91001, wb_cabinet_id=wb_cabinet.id, active_status="started"
    )
    auto = _make_auto_adv(
        adv_id=91002,
        wb_cabinet_id=wb_cabinet.id,
        search_adv_id=91001,
        active_status="started",
    )
    async_session.add_all([search, auto])
    await async_session.flush()

    details = await Pricer().get_tariff_details(async_session, wb_cabinet.shop_id)

    assert details.count == 1.0
    assert details.mode == TariffMode.AUTO
    assert details.total_per_day == _legacy_full_active_day_total()


async def test_integration_one_leg_paused_half_tariff(
    async_session: AsyncSession,
    wb_cabinet: WBCabinet,
) -> None:
    """7.2: Search paused весь день → effective_count=0.5, половина месячного тарифа."""
    search = _make_search_adv(
        adv_id=91101, wb_cabinet_id=wb_cabinet.id, active_status="paused"
    )
    auto = _make_auto_adv(
        adv_id=91102,
        wb_cabinet_id=wb_cabinet.id,
        search_adv_id=91101,
        active_status="started",
    )
    async_session.add_all([search, auto])
    await async_session.flush()

    details = await Pricer().get_tariff_details(async_session, wb_cabinet.shop_id)
    legacy_day = _legacy_full_active_day_total()

    assert details.count == 0.5
    assert details.total_per_day == pytest.approx(legacy_day / 2)


async def test_integration_both_legs_paused_zero_charge(
    async_session: AsyncSession,
    wb_cabinet: WBCabinet,
) -> None:
    """7.2: обе ноги paused → effective_count=0, дневная сумма 0."""
    search = _make_search_adv(
        adv_id=91201, wb_cabinet_id=wb_cabinet.id, active_status="paused"
    )
    auto = _make_auto_adv(
        adv_id=91202,
        wb_cabinet_id=wb_cabinet.id,
        search_adv_id=91201,
        active_status="paused",
    )
    async_session.add_all([search, auto])
    await async_session.flush()

    details = await Pricer().get_tariff_details(async_session, wb_cabinet.shop_id)

    assert details.count == 0.0
    assert details.total_per_day == 0.0


async def test_integration_gaming_latch_keeps_search_slot_half(
    async_session: AsyncSession,
    wb_cabinet: WBCabinet,
) -> None:
    """7.3 / S11: started утром → pause перед charge → latch оставляет Search 0.5."""
    search = _make_search_adv(
        adv_id=91301, wb_cabinet_id=wb_cabinet.id, active_status="paused"
    )
    auto = _make_auto_adv(
        adv_id=91302,
        wb_cabinet_id=wb_cabinet.id,
        search_adv_id=91301,
        active_status="started",
    )
    async_session.add_all([search, auto])
    await async_session.flush()

    utc_day = datetime.date(2024, 6, 15)
    latch = LegLatchManager(FakeRedis())
    await latch.record_sample(auto.id, AdvPaymentLegSlot.AUTO_LEG, 0.5, utc_day)
    await latch.record_sample(auto.id, AdvPaymentLegSlot.SEARCH_LEG, 0.5, utc_day)
    await latch.record_sample(auto.id, AdvPaymentLegSlot.SEARCH_LEG, 0.0, utc_day)

    details = await Pricer().get_tariff_details(
        async_session,
        wb_cabinet.shop_id,
        leg_latch=latch,
        utc_date=utc_day,
    )

    assert details.count == 1.0
    assert details.total_per_day == _legacy_full_active_day_total()


async def test_integration_adv_payment_split_two_rows(
    async_session: AsyncSession,
    wb_cabinet: WBCabinet,
) -> None:
    """7.4: billing charge → две AdvPayment (auto_leg + search_leg), сумма = legacy day."""
    search = _make_search_adv(
        adv_id=91401, wb_cabinet_id=wb_cabinet.id, active_status="started"
    )
    auto = _make_auto_adv(
        adv_id=91402,
        wb_cabinet_id=wb_cabinet.id,
        search_adv_id=91401,
        active_status="started",
    )
    async_session.add_all([search, auto])
    await async_session.flush()
    await async_session.refresh(auto)

    redis_mgr = _FakeRedisBillingManager()
    charge_dt = datetime.datetime(2024, 6, 15, 12, 0, 0)

    with patch.object(billing, "_safe_commit", new=AsyncMock(return_value=True)):
        result = await billing.__process_single_cabinet(
            session=async_session,
            cabinet_id=wb_cabinet.id,
            current_dt=charge_dt,
            pricer=Pricer(),
            redis_manager=redis_mgr,  # type: ignore[arg-type]
        )

    assert result["payment_successful"] is True
    await async_session.flush()

    stmt = select(AdvPayment).where(
        AdvPayment.adv_setting_id == auto.id,
        AdvPayment.date == charge_dt.date(),
    )
    payments = (await async_session.execute(stmt)).scalars().all()
    assert len(payments) == 2
    types = {p.type for p in payments}
    assert types == {AdvPaymentLegType.AUTO_LEG.value, AdvPaymentLegType.SEARCH_LEG.value}
    assert sum(p.amount or 0.0 for p in payments) == pytest.approx(
        _legacy_full_active_day_total()
    )


async def test_integration_e2e_half_charge_single_auto_leg_row(
    async_session: AsyncSession,
    wb_cabinet: WBCabinet,
) -> None:
    """7.5 / S18: Search не started весь день → debit 0.5, одна auto_leg строка."""
    search = _make_search_adv(
        adv_id=91501, wb_cabinet_id=wb_cabinet.id, active_status="paused"
    )
    auto = _make_auto_adv(
        adv_id=91502,
        wb_cabinet_id=wb_cabinet.id,
        search_adv_id=91501,
        active_status="started",
    )
    async_session.add_all([search, auto])
    await async_session.flush()
    await async_session.refresh(auto)

    redis_mgr = _FakeRedisBillingManager()
    charge_dt = datetime.datetime(2024, 6, 16, 12, 0, 0)
    legacy_half = _legacy_full_active_day_total() / 2

    with patch.object(billing, "_safe_commit", new=AsyncMock(return_value=True)):
        result = await billing.__process_single_cabinet(
            session=async_session,
            cabinet_id=wb_cabinet.id,
            current_dt=charge_dt,
            pricer=Pricer(),
            redis_manager=redis_mgr,  # type: ignore[arg-type]
        )

    assert result["payment_successful"] is True
    assert result["price_for_day"] == pytest.approx(legacy_half)
    await async_session.flush()

    stmt = select(AdvPayment).where(
        AdvPayment.adv_setting_id == auto.id,
        AdvPayment.date == charge_dt.date(),
    )
    payments = (await async_session.execute(stmt)).scalars().all()
    assert len(payments) == 1
    assert payments[0].type == AdvPaymentLegType.AUTO_LEG.value
    assert payments[0].amount == pytest.approx(legacy_half)


async def test_integration_bot_inactive_no_charge(
    async_session: AsyncSession,
    wb_cabinet: WBCabinet,
) -> None:
    """S1: bot_active=False на якоре → нет списания и AdvPayment."""
    search = _make_search_adv(
        adv_id=91601, wb_cabinet_id=wb_cabinet.id, active_status="started"
    )
    auto = _make_auto_adv(
        adv_id=91602,
        wb_cabinet_id=wb_cabinet.id,
        search_adv_id=91601,
        active_status="started",
        bot_active=False,
    )
    async_session.add_all([search, auto])
    await async_session.flush()
    await async_session.refresh(auto)

    redis_mgr = _FakeRedisBillingManager()
    charge_dt = datetime.datetime(2024, 6, 18, 12, 0, 0)

    with patch.object(billing, "_safe_commit", new=AsyncMock(return_value=True)):
        result = await billing.__process_single_cabinet(
            session=async_session,
            cabinet_id=wb_cabinet.id,
            current_dt=charge_dt,
            pricer=Pricer(),
            redis_manager=redis_mgr,  # type: ignore[arg-type]
        )

    assert result["payment_successful"] is False
    assert result["reason"] == "no_active_campaigns"
    assert result["price_for_day"] is None

    stmt = select(AdvPayment).where(AdvPayment.adv_setting_id == auto.id)
    payments = (await async_session.execute(stmt)).scalars().all()
    assert payments == []


async def test_integration_billing_gaming_latch_through_charge_loop(
    async_session: AsyncSession,
    wb_cabinet: WBCabinet,
) -> None:
    """S11: started утром → production latch sample → pause → charge держит Search 0.5."""
    search = _make_search_adv(
        adv_id=91701, wb_cabinet_id=wb_cabinet.id, active_status="started"
    )
    auto = _make_auto_adv(
        adv_id=91702,
        wb_cabinet_id=wb_cabinet.id,
        search_adv_id=91701,
        active_status="started",
    )
    async_session.add_all([search, auto])
    await async_session.flush()
    await async_session.refresh(auto)

    redis_mgr = _FakeRedisBillingManager()
    latch = redis_mgr.leg_latch()
    utc_day = datetime.date(2024, 6, 19)
    charge_dt = datetime.datetime(2024, 6, 19, 23, 0, 0)

    # Утром Search была started — latch через production record_anchor_latch_samples.
    anchors = resolve_metering_anchors([search, auto])
    await record_anchor_latch_samples(anchors, latch, utc_day)

    search.active_status = "paused"
    await async_session.flush()

    with patch.object(billing, "_safe_commit", new=AsyncMock(return_value=True)):
        result = await billing.__process_single_cabinet(
            session=async_session,
            cabinet_id=wb_cabinet.id,
            current_dt=charge_dt,
            pricer=Pricer(),
            redis_manager=redis_mgr,  # type: ignore[arg-type]
        )

    assert result["payment_successful"] is True
    assert result["price_for_day"] == _legacy_full_active_day_total()

    stmt = select(AdvPayment).where(
        AdvPayment.adv_setting_id == auto.id,
        AdvPayment.date == utc_day,
    )
    payments = (await async_session.execute(stmt)).scalars().all()
    assert len(payments) == 2
    search_row = next(p for p in payments if p.type == AdvPaymentLegType.SEARCH_LEG.value)
    auto_row = next(p for p in payments if p.type == AdvPaymentLegType.AUTO_LEG.value)
    half = _legacy_full_active_day_total() / 2
    assert search_row.amount == pytest.approx(half)
    assert auto_row.amount == pytest.approx(half)


async def test_integration_legacy_null_adv_payment_dedup(
    async_session: AsyncSession,
    wb_cabinet: WBCabinet,
) -> None:
    """S16: legacy AdvPayment type=NULL блокирует split re-charge за якорь/день."""
    search = _make_search_adv(
        adv_id=91801, wb_cabinet_id=wb_cabinet.id, active_status="started"
    )
    auto = _make_auto_adv(
        adv_id=91802,
        wb_cabinet_id=wb_cabinet.id,
        search_adv_id=91801,
        active_status="started",
    )
    async_session.add_all([search, auto])
    await async_session.flush()
    await async_session.refresh(auto)

    utc_day = datetime.date(2024, 6, 20)
    legacy_amount = _legacy_full_active_day_total()
    async_session.add(
        AdvPayment(
            date=utc_day,
            adv_setting_id=auto.id,
            amount=legacy_amount,
            type=None,
        )
    )
    await async_session.flush()

    redis_mgr = _FakeRedisBillingManager()
    charge_dt = datetime.datetime(2024, 6, 20, 12, 0, 0)

    with patch.object(billing, "_safe_commit", new=AsyncMock(return_value=True)):
        result = await billing.__process_single_cabinet(
            session=async_session,
            cabinet_id=wb_cabinet.id,
            current_dt=charge_dt,
            pricer=Pricer(),
            redis_manager=redis_mgr,  # type: ignore[arg-type]
        )

    assert result["payment_successful"] is True

    stmt = select(AdvPayment).where(
        AdvPayment.adv_setting_id == auto.id,
        AdvPayment.date == utc_day,
    )
    payments = (await async_session.execute(stmt)).scalars().all()
    assert len(payments) == 1
    assert payments[0].type is None
    assert payments[0].amount == pytest.approx(legacy_amount)


async def test_integration_search_paused_no_billing_resume(
    async_session: AsyncSession,
    wb_cabinet: WBCabinet,
) -> None:
    """S17: Search paused (empty-keywords) → половина тарифа; billing не resume/pause WB."""
    search = _make_search_adv(
        adv_id=91901, wb_cabinet_id=wb_cabinet.id, active_status="paused"
    )
    auto = _make_auto_adv(
        adv_id=91902,
        wb_cabinet_id=wb_cabinet.id,
        search_adv_id=91901,
        active_status="started",
    )
    async_session.add_all([search, auto])
    await async_session.flush()
    await async_session.refresh(auto)

    redis_mgr = _FakeRedisBillingManager()
    charge_dt = datetime.datetime(2024, 6, 21, 12, 0, 0)
    legacy_half = _legacy_full_active_day_total() / 2

    resume_mock = AsyncMock()
    pause_intent_mock = AsyncMock()
    with (
        patch.object(billing, "_safe_commit", new=AsyncMock(return_value=True)),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.notify.notify_empty_keywords_resume",
            resume_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.apply_hook.maybe_set_empty_keywords_pause_intent",
            pause_intent_mock,
        ),
    ):
        result = await billing.__process_single_cabinet(
            session=async_session,
            cabinet_id=wb_cabinet.id,
            current_dt=charge_dt,
            pricer=Pricer(),
            redis_manager=redis_mgr,  # type: ignore[arg-type]
        )

    assert result["payment_successful"] is True
    assert result["price_for_day"] == pytest.approx(legacy_half)
    resume_mock.assert_not_called()
    pause_intent_mock.assert_not_called()

    stmt = select(AdvPayment).where(
        AdvPayment.adv_setting_id == auto.id,
        AdvPayment.date == charge_dt.date(),
    )
    payments = (await async_session.execute(stmt)).scalars().all()
    assert len(payments) == 1
    assert payments[0].type == AdvPaymentLegType.AUTO_LEG.value
