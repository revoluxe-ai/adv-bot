from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.shop_runner.service_manager.services.stats_freshness_guard import (
    StatsFreshnessGuard,
)


@pytest.mark.asyncio
async def test_stats_freshness_guard_returns_fresh(monkeypatch) -> None:
    common_manager = SimpleNamespace(get=AsyncMock())
    cluster_manager = SimpleNamespace(get=AsyncMock())
    guard = StatsFreshnessGuard(
        common_stat_timestamp_manager=common_manager,
        cluster_stat_timestamp_manager=cluster_manager,
    )  # type: ignore[arg-type]

    now = datetime.now(timezone.utc)
    keyword_dt = now - timedelta(minutes=5)
    common_dt = now - timedelta(minutes=3)
    cluster_dt = now - timedelta(minutes=2)
    guard._keyword_stat_update_state = SimpleNamespace(  # type: ignore[assignment]
        get_one=AsyncMock(return_value=keyword_dt)
    )
    common_manager.get = AsyncMock(return_value=common_dt)
    cluster_manager.get = AsyncMock(return_value=cluster_dt)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.stats_freshness_guard.settings",
        SimpleNamespace(UPDATE_FULL_ADV_STAT_PERIOD=3600),
    )

    adv = SimpleNamespace(adv_id=101)
    state = await guard.evaluate(adv)  # type: ignore[arg-type]

    assert state.is_fresh is True
    assert state.is_stale_over_6h is False


@pytest.mark.asyncio
async def test_stats_freshness_guard_missing_timestamp_not_emergency(monkeypatch) -> None:
    """Missing timestamp = not yet collected (e.g. new campaign). Must not trigger emergency."""
    common_manager = SimpleNamespace(get=AsyncMock(return_value=None))
    cluster_manager = SimpleNamespace(get=AsyncMock(return_value=datetime.now(timezone.utc)))
    guard = StatsFreshnessGuard(
        common_stat_timestamp_manager=common_manager,
        cluster_stat_timestamp_manager=cluster_manager,
    )  # type: ignore[arg-type]

    now = datetime.now(timezone.utc)
    guard._keyword_stat_update_state = SimpleNamespace(  # type: ignore[assignment]
        get_one=AsyncMock(return_value=now)
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.stats_freshness_guard.settings",
        SimpleNamespace(UPDATE_FULL_ADV_STAT_PERIOD=3600),
    )

    adv = SimpleNamespace(adv_id=101)
    state = await guard.evaluate(adv)  # type: ignore[arg-type]

    assert state.is_fresh is False
    assert state.is_stale_over_6h is False
    assert "not yet collected" in (state.reason or "")


@pytest.mark.asyncio
async def test_stats_freshness_guard_all_timestamps_missing_not_emergency(monkeypatch) -> None:
    """New campaign with no stats in Redis yet must not be classified as emergency-stale."""
    common_manager = SimpleNamespace(get=AsyncMock(return_value=None))
    cluster_manager = SimpleNamespace(get=AsyncMock(return_value=None))
    guard = StatsFreshnessGuard(
        common_stat_timestamp_manager=common_manager,
        cluster_stat_timestamp_manager=cluster_manager,
    )  # type: ignore[arg-type]

    guard._keyword_stat_update_state = SimpleNamespace(  # type: ignore[assignment]
        get_one=AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.stats_freshness_guard.settings",
        SimpleNamespace(UPDATE_FULL_ADV_STAT_PERIOD=3600),
    )

    adv = SimpleNamespace(adv_id=101)
    state = await guard.evaluate(adv)  # type: ignore[arg-type]

    assert state.is_fresh is False
    assert state.is_stale_over_6h is False
    assert state.reason is not None and "not yet collected" in state.reason


@pytest.mark.asyncio
async def test_stats_freshness_guard_stale_but_not_emergency(monkeypatch) -> None:
    common_manager = SimpleNamespace(get=AsyncMock())
    cluster_manager = SimpleNamespace(get=AsyncMock())
    guard = StatsFreshnessGuard(
        common_stat_timestamp_manager=common_manager,
        cluster_stat_timestamp_manager=cluster_manager,
    )  # type: ignore[arg-type]

    now = datetime.now(timezone.utc)
    # stale for regular guard (2h > 1h), but not emergency (2h < 6h)
    keyword_dt = now - timedelta(hours=2)
    common_dt = now - timedelta(minutes=10)
    cluster_dt = now - timedelta(minutes=9)
    guard._keyword_stat_update_state = SimpleNamespace(  # type: ignore[assignment]
        get_one=AsyncMock(return_value=keyword_dt)
    )
    common_manager.get = AsyncMock(return_value=common_dt)
    cluster_manager.get = AsyncMock(return_value=cluster_dt)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.stats_freshness_guard.settings",
        SimpleNamespace(UPDATE_FULL_ADV_STAT_PERIOD=3600),
    )

    adv = SimpleNamespace(adv_id=101)
    state = await guard.evaluate(adv)  # type: ignore[arg-type]

    assert state.is_fresh is False
    assert state.is_stale_over_6h is False


@pytest.mark.asyncio
async def test_stats_freshness_guard_emergency_when_older_than_6h(monkeypatch) -> None:
    common_manager = SimpleNamespace(get=AsyncMock())
    cluster_manager = SimpleNamespace(get=AsyncMock())
    guard = StatsFreshnessGuard(
        common_stat_timestamp_manager=common_manager,
        cluster_stat_timestamp_manager=cluster_manager,
    )  # type: ignore[arg-type]

    now = datetime.now(timezone.utc)
    keyword_dt = now - timedelta(hours=7)
    common_dt = now - timedelta(minutes=10)
    cluster_dt = now - timedelta(minutes=10)
    guard._keyword_stat_update_state = SimpleNamespace(  # type: ignore[assignment]
        get_one=AsyncMock(return_value=keyword_dt)
    )
    common_manager.get = AsyncMock(return_value=common_dt)
    cluster_manager.get = AsyncMock(return_value=cluster_dt)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.stats_freshness_guard.settings",
        SimpleNamespace(UPDATE_FULL_ADV_STAT_PERIOD=3600),
    )

    adv = SimpleNamespace(adv_id=101)
    state = await guard.evaluate(adv)  # type: ignore[arg-type]

    assert state.is_fresh is False
    assert state.is_stale_over_6h is True
