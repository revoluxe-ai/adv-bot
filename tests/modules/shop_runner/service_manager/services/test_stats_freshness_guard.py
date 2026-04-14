from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_runner.service_manager.services.clickhouse_freshness_reader import (
    ClickHouseStatsFreshnessReader,
)
from app.modules.shop_runner.service_manager.services.stats_freshness_guard import (
    StatsFreshnessGuard,
)


def _make_guard(
    *,
    common_dt: datetime | None,
    full_adv_dt: datetime | None,
    cluster_dt: datetime | None,
) -> StatsFreshnessGuard:
    reader = MagicMock(spec=ClickHouseStatsFreshnessReader)
    reader.get_common_updated_at = AsyncMock(return_value=common_dt)
    reader.get_full_adv_updated_at = AsyncMock(return_value=full_adv_dt)
    reader.get_cluster_updated_at = AsyncMock(return_value=cluster_dt)
    guard = StatsFreshnessGuard(ch_freshness_reader=reader)
    guard._ch_reader = reader
    return guard


def _complex_adv(
    adv_id: int = 101, main_nmid: int = 1, all_adv_ids: set[int] | None = None
) -> SimpleNamespace:
    if all_adv_ids is None:
        all_adv_ids = {adv_id}
    return SimpleNamespace(
        original_adv_setting_id=adv_id,
        main_nmid=main_nmid,
        all_adv_ids=all_adv_ids,
    )


@pytest.mark.asyncio
async def test_stats_freshness_guard_returns_fresh() -> None:
    now = datetime.now(timezone.utc)
    common_dt = now - timedelta(minutes=5)
    full_adv_dt = now - timedelta(minutes=3)
    cluster_dt = now - timedelta(minutes=2)

    guard = _make_guard(
        common_dt=common_dt,
        full_adv_dt=full_adv_dt,
        cluster_dt=cluster_dt,
    )
    adv = _complex_adv()
    state = await guard.evaluate(adv)  # type: ignore[arg-type]

    assert state.is_fresh is True
    assert state.is_stale_over_6h is False


@pytest.mark.asyncio
async def test_stats_freshness_guard_missing_timestamp_not_emergency() -> None:
    """Missing timestamp = not yet collected (e.g. new campaign). Must not trigger emergency."""
    now = datetime.now(timezone.utc)

    guard = _make_guard(
        common_dt=None,
        full_adv_dt=now,
        cluster_dt=now,
    )
    adv = _complex_adv()
    state = await guard.evaluate(adv)  # type: ignore[arg-type]

    assert state.is_fresh is False
    assert state.is_stale_over_6h is False
    assert "not yet collected" in (state.reason or "")


@pytest.mark.asyncio
async def test_stats_freshness_guard_all_timestamps_missing_not_emergency() -> None:
    """New campaign with no stats in DB yet must not be classified as emergency-stale."""
    guard = _make_guard(
        common_dt=None,
        full_adv_dt=None,
        cluster_dt=None,
    )
    adv = _complex_adv()
    state = await guard.evaluate(adv)  # type: ignore[arg-type]

    assert state.is_fresh is False
    assert state.is_stale_over_6h is False
    assert state.reason is not None and "not yet collected" in state.reason


@pytest.mark.asyncio
async def test_stats_freshness_guard_stale_but_not_emergency() -> None:
    """Fixed stale threshold: age > 1h on one source => stale; < 6h => not emergency."""
    now = datetime.now(timezone.utc)
    common_dt = now - timedelta(hours=2)
    full_adv_dt = now - timedelta(minutes=10)
    cluster_dt = now - timedelta(minutes=9)

    guard = _make_guard(
        common_dt=common_dt,
        full_adv_dt=full_adv_dt,
        cluster_dt=cluster_dt,
    )
    adv = _complex_adv()
    state = await guard.evaluate(adv)  # type: ignore[arg-type]

    assert state.is_fresh is False
    assert state.is_stale_over_6h is False


@pytest.mark.asyncio
async def test_stats_freshness_guard_all_sources_stale_over_fixed_1h_not_emergency() -> None:
    """Fixed stale threshold: all sources > 1h and < 6h => stale, not emergency."""
    now = datetime.now(timezone.utc)
    common_dt = now - timedelta(hours=3)
    full_adv_dt = now - timedelta(hours=2)
    cluster_dt = now - timedelta(hours=2, minutes=30)

    guard = _make_guard(
        common_dt=common_dt,
        full_adv_dt=full_adv_dt,
        cluster_dt=cluster_dt,
    )
    adv = _complex_adv()
    state = await guard.evaluate(adv)  # type: ignore[arg-type]

    assert state.is_fresh is False
    assert state.is_stale_over_6h is False


@pytest.mark.asyncio
async def test_stats_freshness_guard_emergency_when_older_than_6h() -> None:
    now = datetime.now(timezone.utc)
    common_dt = now - timedelta(hours=7)
    full_adv_dt = now - timedelta(minutes=10)
    cluster_dt = now - timedelta(minutes=10)

    guard = _make_guard(
        common_dt=common_dt,
        full_adv_dt=full_adv_dt,
        cluster_dt=cluster_dt,
    )
    adv = _complex_adv()
    state = await guard.evaluate(adv)  # type: ignore[arg-type]

    assert state.is_fresh is False
    assert state.is_stale_over_6h is True
