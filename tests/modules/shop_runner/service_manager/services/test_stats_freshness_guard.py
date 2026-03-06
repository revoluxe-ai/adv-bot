from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pytest

from app.modules.shop_runner.service_manager.services.stats_freshness_guard import (
    StatsFreshnessGuard,
)

MODULE = "app.modules.shop_runner.service_manager.services.stats_freshness_guard"


@pytest.mark.asyncio
async def test_stats_freshness_guard_returns_fresh(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    keyword_dt = now - timedelta(minutes=5)
    common_dt = now - timedelta(minutes=3)
    cluster_dt = now - timedelta(minutes=2)

    async def get_full(*_args: object, **_kwargs: object) -> datetime | None:
        return keyword_dt

    async def get_common(*_args: object, **_kwargs: object) -> datetime | None:
        return common_dt

    async def get_cluster(*_args: object, **_kwargs: object) -> datetime | None:
        return cluster_dt

    monkeypatch.setattr(f"{MODULE}.get_last_full_stat_update_from_db", get_full)
    monkeypatch.setattr(f"{MODULE}.get_last_common_stat_update_from_db", get_common)
    monkeypatch.setattr(f"{MODULE}.get_last_cluster_stat_update_from_db", get_cluster)
    monkeypatch.setattr(
        f"{MODULE}.settings",
        SimpleNamespace(UPDATE_FULL_ADV_STAT_PERIOD=3600),
    )

    guard = StatsFreshnessGuard()
    adv = SimpleNamespace(adv_id=101, nmids=[1])
    state = await guard.evaluate(adv)  # type: ignore[arg-type]

    assert state.is_fresh is True
    assert state.is_stale_over_6h is False


@pytest.mark.asyncio
async def test_stats_freshness_guard_missing_timestamp_not_emergency(monkeypatch) -> None:
    """Missing timestamp = not yet collected (e.g. new campaign). Must not trigger emergency."""
    now = datetime.now(timezone.utc)

    async def get_full(*_args: object, **_kwargs: object) -> datetime | None:
        return now

    async def get_common(*_args: object, **_kwargs: object) -> datetime | None:
        return None

    async def get_cluster(*_args: object, **_kwargs: object) -> datetime | None:
        return now

    monkeypatch.setattr(f"{MODULE}.get_last_full_stat_update_from_db", get_full)
    monkeypatch.setattr(f"{MODULE}.get_last_common_stat_update_from_db", get_common)
    monkeypatch.setattr(f"{MODULE}.get_last_cluster_stat_update_from_db", get_cluster)
    monkeypatch.setattr(
        f"{MODULE}.settings",
        SimpleNamespace(UPDATE_FULL_ADV_STAT_PERIOD=3600),
    )

    guard = StatsFreshnessGuard()
    adv = SimpleNamespace(adv_id=101, nmids=[1])
    state = await guard.evaluate(adv)  # type: ignore[arg-type]

    assert state.is_fresh is False
    assert state.is_stale_over_6h is False
    assert "not yet collected" in (state.reason or "")


@pytest.mark.asyncio
async def test_stats_freshness_guard_all_timestamps_missing_not_emergency(monkeypatch) -> None:
    """New campaign with no stats in DB yet must not be classified as emergency-stale."""

    async def get_none(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(f"{MODULE}.get_last_full_stat_update_from_db", get_none)
    monkeypatch.setattr(f"{MODULE}.get_last_common_stat_update_from_db", get_none)
    monkeypatch.setattr(f"{MODULE}.get_last_cluster_stat_update_from_db", get_none)
    monkeypatch.setattr(
        f"{MODULE}.settings",
        SimpleNamespace(UPDATE_FULL_ADV_STAT_PERIOD=3600),
    )

    guard = StatsFreshnessGuard()
    adv = SimpleNamespace(adv_id=101, nmids=[])
    state = await guard.evaluate(adv)  # type: ignore[arg-type]

    assert state.is_fresh is False
    assert state.is_stale_over_6h is False
    assert state.reason is not None and "not yet collected" in state.reason


@pytest.mark.asyncio
async def test_stats_freshness_guard_stale_but_not_emergency(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    keyword_dt = now - timedelta(hours=2)
    common_dt = now - timedelta(minutes=10)
    cluster_dt = now - timedelta(minutes=9)

    async def get_full(*_args: object, **_kwargs: object) -> datetime | None:
        return keyword_dt

    async def get_common(*_args: object, **_kwargs: object) -> datetime | None:
        return common_dt

    async def get_cluster(*_args: object, **_kwargs: object) -> datetime | None:
        return cluster_dt

    monkeypatch.setattr(f"{MODULE}.get_last_full_stat_update_from_db", get_full)
    monkeypatch.setattr(f"{MODULE}.get_last_common_stat_update_from_db", get_common)
    monkeypatch.setattr(f"{MODULE}.get_last_cluster_stat_update_from_db", get_cluster)
    monkeypatch.setattr(
        f"{MODULE}.settings",
        SimpleNamespace(UPDATE_FULL_ADV_STAT_PERIOD=3600),
    )

    guard = StatsFreshnessGuard()
    adv = SimpleNamespace(adv_id=101, nmids=[1])
    state = await guard.evaluate(adv)  # type: ignore[arg-type]

    assert state.is_fresh is False
    assert state.is_stale_over_6h is False


@pytest.mark.asyncio
async def test_stats_freshness_guard_emergency_when_older_than_6h(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    keyword_dt = now - timedelta(hours=7)
    common_dt = now - timedelta(minutes=10)
    cluster_dt = now - timedelta(minutes=10)

    async def get_full(*_args: object, **_kwargs: object) -> datetime | None:
        return keyword_dt

    async def get_common(*_args: object, **_kwargs: object) -> datetime | None:
        return common_dt

    async def get_cluster(*_args: object, **_kwargs: object) -> datetime | None:
        return cluster_dt

    monkeypatch.setattr(f"{MODULE}.get_last_full_stat_update_from_db", get_full)
    monkeypatch.setattr(f"{MODULE}.get_last_common_stat_update_from_db", get_common)
    monkeypatch.setattr(f"{MODULE}.get_last_cluster_stat_update_from_db", get_cluster)
    monkeypatch.setattr(
        f"{MODULE}.settings",
        SimpleNamespace(UPDATE_FULL_ADV_STAT_PERIOD=3600),
    )

    guard = StatsFreshnessGuard()
    adv = SimpleNamespace(adv_id=101, nmids=[1])
    state = await guard.evaluate(adv)  # type: ignore[arg-type]

    assert state.is_fresh is False
    assert state.is_stale_over_6h is True
