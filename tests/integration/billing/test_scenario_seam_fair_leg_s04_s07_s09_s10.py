"""Scenario seams S4/S7/S9/S10: fair leg-pause billing через Pricer и charge loop.

Evidence class: ``scenario_seam`` (integration, destructive PG).
Causal path: production ``leg_metering`` → ``Pricer`` / ``billing.__process_single_cabinet``.
"""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fakeredis.aioredis import FakeRedis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing import billing
from app.modules.billing.leg_latch import LegLatchManager
from app.modules.billing.leg_metering import (
    compute_anchor_billables,
    resolve_metering_anchors,
)
from app.modules.billing.models import AdvPayment, AdvPaymentLegType
from app.modules.billing.pricer.pricer import Pricer, TariffMode
from app.modules.billing.pricer.tariffs import tariffs_for_auto_setting
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from tests.integration.billing.fair_leg_scenario_contract import (
    CONTRACT_ID as FAIR_LEG_SCENARIO_CONTRACT_ID,
    FAIR_LEG_SCENARIO_CASES,
    legacy_full_active_day_total,
    tier_price_for_units,
)

assert FAIR_LEG_SCENARIO_CONTRACT_ID == "fair_leg.billing.metering_scenario.v1"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
    pytest.mark.destructive_local,
]

_CASE_BY_ID = {c.case_id: c for c in FAIR_LEG_SCENARIO_CASES}


class _FakeRedisBillingManager:
    """Redis billing flags + leg latch на fakeredis (thin end после orchestration)."""

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


async def _assert_pricer_half(
    async_session: AsyncSession,
    shop_id: str,
    *,
    expected_count: float,
) -> None:
    details = await Pricer().get_tariff_details(async_session, shop_id)
    legacy_day = legacy_full_active_day_total()
    assert details.count == expected_count
    assert details.mode == TariffMode.AUTO
    assert details.total_per_day == pytest.approx(legacy_day * expected_count)


async def _charge_and_fetch_payments(
    async_session: AsyncSession,
    wb_cabinet: WBCabinet,
    anchor: AdvSetting,
    *,
    charge_date: datetime.date,
) -> tuple[dict[str, object], list[AdvPayment]]:
    redis_mgr = _FakeRedisBillingManager()
    charge_dt = datetime.datetime.combine(charge_date, datetime.time(12, 0, 0))
    with patch.object(billing, "_safe_commit", new=AsyncMock(return_value=True)):
        result = await billing.__process_single_cabinet(
            session=async_session,
            cabinet_id=wb_cabinet.id,
            current_dt=charge_dt,
            pricer=Pricer(),
            redis_manager=redis_mgr,  # type: ignore[arg-type]
        )
    await async_session.flush()
    stmt = select(AdvPayment).where(
        AdvPayment.adv_setting_id == anchor.id,
        AdvPayment.date == charge_date,
    )
    payments = (await async_session.execute(stmt)).scalars().all()
    return result, list(payments)


async def test_scenario_seam_s04_unresolved_search_link_anchor_only(
    async_session: AsyncSession,
    wb_cabinet: WBCabinet,
) -> None:
    """S4 / GAP-S4-SEAM: unresolved search_adv_id → только Auto-слот, 0.5."""
    case = _CASE_BY_ID["s04_unresolved_search_link"]
    auto = _make_auto_adv(
        adv_id=92001,
        wb_cabinet_id=wb_cabinet.id,
        search_adv_id=99999,
        active_status="started",
    )
    async_session.add(auto)
    await async_session.flush()
    await async_session.refresh(auto)

    anchors = resolve_metering_anchors([auto])
    assert len(anchors) == 1
    assert anchors[0].search_row is None
    billables = await compute_anchor_billables(anchors)
    assert billables[0].has_search_slot is case.expect_search_slot
    assert billables[0].total == case.expected_effective_count

    await _assert_pricer_half(
        async_session, wb_cabinet.shop_id, expected_count=case.expected_effective_count
    )

    charge_date = datetime.date(2024, 7, 1)
    result, payments = await _charge_and_fetch_payments(
        async_session, wb_cabinet, auto, charge_date=charge_date
    )
    assert result["payment_successful"] is True
    assert len(payments) == 1
    assert payments[0].type == AdvPaymentLegType.AUTO_LEG.value
    assert payments[0].amount == pytest.approx(legacy_full_active_day_total() / 2)


async def test_scenario_seam_s07_only_search_started_half_tariff(
    async_session: AsyncSession,
    wb_cabinet: WBCabinet,
) -> None:
    """S7 / GAP-S7-SEAM: anchor paused + Search started → effective_count=0.5."""
    case = _CASE_BY_ID["s07_only_search_started"]
    search = _make_search_adv(
        adv_id=92101, wb_cabinet_id=wb_cabinet.id, active_status="started"
    )
    auto = _make_auto_adv(
        adv_id=92102,
        wb_cabinet_id=wb_cabinet.id,
        search_adv_id=92101,
        active_status="paused",
    )
    async_session.add_all([search, auto])
    await async_session.flush()
    await async_session.refresh(auto)

    anchors = resolve_metering_anchors([search, auto])
    billables = await compute_anchor_billables(anchors)
    assert billables[0].has_search_slot is case.expect_search_slot
    assert billables[0].total == case.expected_effective_count

    await _assert_pricer_half(
        async_session, wb_cabinet.shop_id, expected_count=case.expected_effective_count
    )

    charge_date = datetime.date(2024, 7, 2)
    result, payments = await _charge_and_fetch_payments(
        async_session, wb_cabinet, auto, charge_date=charge_date
    )
    assert result["payment_successful"] is True
    assert len(payments) == 1
    assert payments[0].type == AdvPaymentLegType.SEARCH_LEG.value
    assert payments[0].amount == pytest.approx(legacy_full_active_day_total() / 2)


async def test_scenario_seam_s09_no_search_anchor_half_tariff(
    async_session: AsyncSession,
    wb_cabinet: WBCabinet,
) -> None:
    """S9 / GAP-S9-SEAM: single-anchor без Search → 0.5 charge."""
    case = _CASE_BY_ID["s09_no_search_anchor_half"]
    auto = _make_auto_adv(
        adv_id=92201,
        wb_cabinet_id=wb_cabinet.id,
        search_adv_id=None,
        active_status="started",
    )
    async_session.add(auto)
    await async_session.flush()
    await async_session.refresh(auto)

    anchors = resolve_metering_anchors([auto])
    assert anchors[0].search_row is None
    billables = await compute_anchor_billables(anchors)
    assert billables[0].has_search_slot is case.expect_search_slot
    assert billables[0].total == case.expected_effective_count

    await _assert_pricer_half(
        async_session, wb_cabinet.shop_id, expected_count=case.expected_effective_count
    )

    charge_date = datetime.date(2024, 7, 3)
    result, payments = await _charge_and_fetch_payments(
        async_session, wb_cabinet, auto, charge_date=charge_date
    )
    assert result["payment_successful"] is True
    assert len(payments) == 1
    assert payments[0].type == AdvPaymentLegType.AUTO_LEG.value
    assert payments[0].amount == pytest.approx(legacy_full_active_day_total() / 2)


async def test_scenario_seam_s10_two_half_units_tier_bracket(
    async_session: AsyncSession,
    wb_cabinet: WBCabinet,
) -> None:
    """S10 / GAP-S10-SEAM: два комплекта × 0.5 → tier bracket count=1.0."""
    case = _CASE_BY_ID["s10_two_half_units_one_tier"]
    search_a = _make_search_adv(
        adv_id=92301, wb_cabinet_id=wb_cabinet.id, active_status="paused"
    )
    auto_a = _make_auto_adv(
        adv_id=92302,
        wb_cabinet_id=wb_cabinet.id,
        search_adv_id=92301,
        active_status="started",
    )
    search_b = _make_search_adv(
        adv_id=92303, wb_cabinet_id=wb_cabinet.id, active_status="started"
    )
    auto_b = _make_auto_adv(
        adv_id=92304,
        wb_cabinet_id=wb_cabinet.id,
        search_adv_id=92303,
        active_status="paused",
    )
    async_session.add_all([search_a, auto_a, search_b, auto_b])
    await async_session.flush()

    billables = await compute_anchor_billables(
        resolve_metering_anchors([search_a, auto_a, search_b, auto_b])
    )
    total = sum(b.total for b in billables)
    assert total == case.expected_effective_count

    details = await Pricer().get_tariff_details(async_session, wb_cabinet.shop_id)
    assert details.count == case.tier_bracket_units
    assert details.mode == TariffMode.AUTO
    assert details.price_per_adv == float(tariffs_for_auto_setting[1])
    assert details.total_per_month == pytest.approx(tier_price_for_units(1.0))
    assert details.total_per_day == pytest.approx(
        Pricer.get_tariff_for_day(tier_price_for_units(1.0))
    )
