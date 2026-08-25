"""Unit-тесты leg_latch: UTC-day max per slot (spec anti-gaming)."""

from __future__ import annotations

from datetime import date

import pytest
from fakeredis.aioredis import FakeRedis

from app.modules.billing.leg_latch import AdvPaymentLegSlot, LegLatchManager

pytestmark = pytest.mark.unit


@pytest.fixture
def latch() -> LegLatchManager:
    return LegLatchManager(FakeRedis())


@pytest.mark.asyncio
async def test_record_sample_accumulates_max(latch: LegLatchManager) -> None:
    """S11: record_sample накапливает max за UTC-день."""
    utc_day = date(2024, 6, 15)
    await latch.record_sample(10, AdvPaymentLegSlot.AUTO_LEG, 0.0, utc_day)
    await latch.record_sample(10, AdvPaymentLegSlot.AUTO_LEG, 0.5, utc_day)
    weight = await latch.get_billable_weight(10, AdvPaymentLegSlot.AUTO_LEG, utc_day)
    assert weight == 0.5


@pytest.mark.asyncio
async def test_gaming_pause_before_charge_keeps_latch(latch: LegLatchManager) -> None:
    """S11 gaming: started ранее, pause перед charge → latch 0.5."""
    utc_day = date(2024, 6, 15)
    await latch.record_sample(10, AdvPaymentLegSlot.SEARCH_LEG, 0.5, utc_day)
    await latch.record_sample(10, AdvPaymentLegSlot.SEARCH_LEG, 0.0, utc_day)
    weight = await latch.get_billable_weight(
        10, AdvPaymentLegSlot.SEARCH_LEG, utc_day
    )
    assert weight == 0.5


@pytest.mark.asyncio
async def test_never_started_stays_zero(latch: LegLatchManager) -> None:
    """S12: нога не была started → latch 0."""
    utc_day = date(2024, 6, 15)
    await latch.record_sample(10, AdvPaymentLegSlot.SEARCH_LEG, 0.0, utc_day)
    weight = await latch.get_billable_weight(
        10, AdvPaymentLegSlot.SEARCH_LEG, utc_day
    )
    assert weight == 0.0


@pytest.mark.asyncio
async def test_latch_not_from_bot_active_alone(latch: LegLatchManager) -> None:
    """Latch обновляется только весом слота, не bot_active."""
    utc_day = date(2024, 6, 15)
    await latch.record_sample(10, AdvPaymentLegSlot.AUTO_LEG, 0.0, utc_day)
    weight = await latch.get_billable_weight(10, AdvPaymentLegSlot.AUTO_LEG, utc_day)
    assert weight == 0.0
