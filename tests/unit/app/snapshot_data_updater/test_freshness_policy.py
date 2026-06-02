"""Двухпороговая политика свежести."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.snapshot_data_updater.cache_freshness import CacheStaleError
from app.snapshot_data_updater.freshness_policy import (
    FreshnessPolicy,
    classify_age_sec,
    enforce_cache_stale,
    should_skip_refresh,
)


@pytest.mark.unit
def test_classify_age_sec() -> None:
    policy = FreshnessPolicy(skip_refresh_sec=300.0, stale_sec=900.0)
    assert classify_age_sec(100.0, policy) == "too_fresh"
    assert classify_age_sec(500.0, policy) == "acceptable"
    assert classify_age_sec(1000.0, policy) == "stale"


@pytest.mark.unit
def test_enforce_cache_stale_raises_after_stale_sec() -> None:
    policy = FreshnessPolicy(skip_refresh_sec=300.0, stale_sec=900.0)
    old = datetime.now(tz=UTC) - timedelta(seconds=1000)
    with pytest.raises(CacheStaleError, match="exceeds stale"):
        enforce_cache_stale(old, policy, context="test")


@pytest.mark.unit
def test_should_skip_refresh() -> None:
    policy = FreshnessPolicy(skip_refresh_sec=300.0, stale_sec=900.0)
    assert should_skip_refresh(100.0, policy) is True
    assert should_skip_refresh(500.0, policy) is False
