"""Unit-тесты проверки возраста кеша."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.snapshot_data_updater.cache_freshness import (
    CacheStaleError,
    cache_age_sec,
    enforce_cache_max_age,
    enforce_cache_max_age_from_meta,
    parse_warmed_at,
)


@pytest.mark.unit
def test_enforce_disabled_when_max_age_zero() -> None:
    old = datetime.now(tz=UTC) - timedelta(hours=1)
    enforce_cache_max_age(old, 0.0, context="test")


@pytest.mark.unit
def test_enforce_raises_when_cache_too_old() -> None:
    old = datetime.now(tz=UTC) - timedelta(seconds=100)
    with pytest.raises(CacheStaleError, match="exceeds max"):
        enforce_cache_max_age(old, 60.0, context="keywords adv_id=1")


@pytest.mark.unit
def test_enforce_raises_when_timestamp_missing() -> None:
    with pytest.raises(CacheStaleError, match="timestamp missing"):
        enforce_cache_max_age(None, 60.0, context="keywords adv_id=1")


@pytest.mark.unit
def test_enforce_from_meta() -> None:
    warmed = (datetime.now(tz=UTC) - timedelta(seconds=120)).isoformat()
    with pytest.raises(CacheStaleError):
        enforce_cache_max_age_from_meta(
            {"warmed_at": warmed},
            60.0,
            context="adv_id=2",
        )


@pytest.mark.unit
def test_parse_warmed_at() -> None:
    ts = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)
    meta = {"warmed_at": ts.isoformat()}
    assert parse_warmed_at(meta) == ts
    assert cache_age_sec(ts) >= 0
