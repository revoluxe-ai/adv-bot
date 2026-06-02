from __future__ import annotations

import pytest

from app.snapshot_data_updater.config import (
    SnapshotUpdaterConfig,
    get_snapshot_config,
    reload_snapshot_config,
)


@pytest.mark.unit
def test_reload_snapshot_config_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNAPSHOT_UPDATER_USE_LIVE", "1")
    monkeypatch.setenv("SNAPSHOT_REFRESH_INTERVAL_SEC", "120")
    monkeypatch.delenv("SNAPSHOT_ADV_STALE_SEC", raising=False)
    monkeypatch.setenv("SNAPSHOT_CACHE_MAX_AGE_SEC", "300")
    cfg = reload_snapshot_config()
    assert cfg.use_live_updater is True
    assert cfg.refresh_interval_sec == 120.0
    assert cfg.snapshot_adv_policy.stale_sec == 300.0
    assert cfg.cache_max_age_sec == 300.0


@pytest.mark.unit
def test_freshness_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNAPSHOT_KEYWORDS_SKIP_REFRESH_SEC", "300")
    monkeypatch.setenv("SNAPSHOT_KEYWORDS_STALE_SEC", "900")
    cfg = reload_snapshot_config()
    assert cfg.keywords_policy.skip_refresh_sec == 300.0
    assert cfg.keywords_policy.stale_sec == 900.0


@pytest.mark.unit
def test_get_snapshot_config_cached_until_reload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SNAPSHOT_UPDATER_USE_LIVE", "0")
    reload_snapshot_config()
    first = get_snapshot_config()
    monkeypatch.setenv("SNAPSHOT_UPDATER_USE_LIVE", "1")
    # без reload — старое значение
    second = get_snapshot_config()
    assert second.use_live_updater == first.use_live_updater
    third = reload_snapshot_config()
    assert third.use_live_updater is True


@pytest.mark.unit
def test_postgres_task_timeout_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNAPSHOT_RESOURCE_TASK_TIMEOUT_SEC", "30")
    monkeypatch.setenv("SNAPSHOT_PG_TASK_TIMEOUT_SEC", "120")
    cfg = reload_snapshot_config()
    assert cfg.resource_task_timeout_sec == 30.0
    assert cfg.postgres_task_timeout_sec == 120.0


@pytest.mark.unit
def test_default_config_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.snapshot_data_updater.config import DEFAULT_CONFIG

    monkeypatch.setenv("SNAPSHOT_TICK_POLICY", "wait")
    reload_snapshot_config()
    assert DEFAULT_CONFIG.tick_policy == "wait"
