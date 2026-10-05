"""Updater/config tests for campaign-settings-history."""

from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager
from types import ModuleType

import pytest

import app.modules.campaign_settings_history.updater as updater_module
from app.modules.campaign_settings_history.config import CampaignSettingsHistoryConfig
from app.modules.campaign_settings_history.domain import CabinetCollectResult
from app.modules.campaign_settings_history.updater import (
    DEFAULT_INTERVAL_SECONDS,
    CampaignSettingsHistoryUpdater,
)

pytestmark = pytest.mark.unit


def test_config_defaults_disabled_at_300_seconds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec campaign-settings-history: default runtime cannot write accidentally."""
    monkeypatch.delenv("CAMPAIGN_SETTINGS_HISTORY_ENABLED", raising=False)
    monkeypatch.delenv(
        "CAMPAIGN_SETTINGS_HISTORY_INTERVAL_SECONDS",
        raising=False,
    )

    cfg = CampaignSettingsHistoryConfig.from_env()

    assert cfg.enabled is False
    assert cfg.interval_seconds == DEFAULT_INTERVAL_SECONDS == 300


def test_config_reads_explicit_enable_and_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec campaign-settings-history: cadence is configurable only explicitly."""
    monkeypatch.setenv("CAMPAIGN_SETTINGS_HISTORY_ENABLED", "true")
    monkeypatch.setenv("CAMPAIGN_SETTINGS_HISTORY_INTERVAL_SECONDS", "420")

    cfg = CampaignSettingsHistoryConfig.from_env()

    assert cfg.enabled is True
    assert cfg.interval_seconds == 420


@pytest.mark.parametrize("bad", ["0", "-1"])
def test_config_rejects_non_positive_interval(
    monkeypatch: pytest.MonkeyPatch,
    bad: str,
) -> None:
    """Spec campaign-settings-history: invalid cadence fails closed."""
    monkeypatch.setenv("CAMPAIGN_SETTINGS_HISTORY_INTERVAL_SECONDS", bad)

    with pytest.raises(ValueError, match="must be positive"):
        CampaignSettingsHistoryConfig.from_env()


@pytest.mark.asyncio
async def test_disabled_run_once_does_not_discover_or_open_clickhouse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec campaign-settings-history: disabled path performs zero external I/O."""

    async def fail_discovery() -> tuple[int, ...]:
        raise AssertionError("disabled updater must not discover PostgreSQL")

    monkeypatch.setattr(
        updater_module,
        "discover_history_cabinet_ids",
        fail_discovery,
    )
    updater = CampaignSettingsHistoryUpdater(enabled=False)

    result = await updater.run_once()

    assert result.code == "disabled"
    assert result.cabinets_discovered == 0
    assert result.inserted == 0


def _install_fake_clickhouse_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = ModuleType("app.utils.click_house.client")

    @asynccontextmanager
    async def client_factory():
        yield object()

    fake.get_clickhouse_client = client_factory  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "app.utils.click_house.client", fake)


@pytest.mark.asyncio
async def test_enabled_tick_aggregates_results_and_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec campaign-settings-history: tick exposes structured collection outcome."""
    _install_fake_clickhouse_module(monkeypatch)

    async def discover() -> tuple[int, ...]:
        return (1, 2, 3)

    async def collect(*, wb_cabinet_id: int, clickhouse_client: object):
        assert clickhouse_client is not None
        if wb_cabinet_id == 1:
            return CabinetCollectResult(
                wb_cabinet_id=1,
                code="ok",
                campaigns_read=4,
                unchanged=2,
                inserted=2,
            )
        if wb_cabinet_id == 2:
            return CabinetCollectResult(
                wb_cabinet_id=2,
                code="lock_contended",
            )
        raise RuntimeError("synthetic cabinet failure")

    monkeypatch.setattr(
        updater_module,
        "discover_history_cabinet_ids",
        discover,
    )
    monkeypatch.setattr(
        updater_module,
        "collect_one_locked_cabinet",
        collect,
    )

    result = await CampaignSettingsHistoryUpdater(
        enabled=True,
        interval_seconds=300,
    ).run_once()

    assert result.code == "degraded"
    assert result.cabinets_discovered == 3
    assert result.cabinets_ok == 1
    assert result.lock_contended == 1
    assert result.campaigns_read == 4
    assert result.unchanged == 2
    assert result.inserted == 2
    assert result.failures == 1


@pytest.mark.asyncio
async def test_overlapping_same_process_tick_is_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec campaign-settings-history: in-process overlap cannot start second collection."""
    _install_fake_clickhouse_module(monkeypatch)
    entered = asyncio.Event()
    release = asyncio.Event()

    async def discover() -> tuple[int, ...]:
        entered.set()
        await release.wait()
        return ()

    monkeypatch.setattr(
        updater_module,
        "discover_history_cabinet_ids",
        discover,
    )
    updater = CampaignSettingsHistoryUpdater(enabled=True)

    first = asyncio.create_task(updater.run_once())
    await entered.wait()
    second = await updater.run_once()
    release.set()
    first_result = await first

    assert second.code == "overlap_skipped"
    assert first_result.code == "ok"
