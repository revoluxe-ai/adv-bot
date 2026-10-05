"""Collector tests for campaign-settings-history."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime

import pytest

from app.modules.campaign_settings_contract import (
    CampaignSettingsSources,
    HistoryPolicy,
    NormalizationPolicy,
    REGISTERED_SOURCES,
)
from app.modules.campaign_settings_history.collector import collect_cabinet
from app.modules.campaign_settings_history.domain import (
    CabinetSettingsBatch,
    CampaignSettingsRecord,
    HistorySnapshotRow,
)

pytestmark = pytest.mark.unit


def _value(policy, field_name: str):
    if policy.allowed_values:
        return policy.allowed_values[0]
    norm = policy.normalization
    if norm is NormalizationPolicy.INT:
        return 1
    if norm is NormalizationPolicy.FLOAT:
        return 1.0
    if norm is NormalizationPolicy.BOOL:
        return False
    if norm is NormalizationPolicy.STRING:
        return "Europe/Moscow" if field_name == "timezone" else field_name
    if norm is NormalizationPolicy.INT_LIST:
        return [10, 20]
    if norm is NormalizationPolicy.STRING_LIST:
        return []
    if norm is NormalizationPolicy.JSON_OBJECT:
        return {}
    if norm is NormalizationPolicy.DATE:
        return date(2026, 1, 1)
    raise AssertionError(norm)


def _row(source: str, **overrides):
    data = {}
    for name, policy in REGISTERED_SOURCES[source].fields.items():
        if policy.history is not HistoryPolicy.EXCLUDED:
            data[name] = _value(policy, name)
    data.update(overrides)
    return data


def _campaign(
    adv_setting_id: int = 1,
    *,
    max_cpm: int | None = 100,
    invalid: bool = False,
) -> CampaignSettingsRecord:
    adv = _row(
        "AdvSetting",
        id=adv_setting_id,
        adv_id=1000 + adv_setting_id,
        wb_cabinet_id=77,
        _search_adv_id=2000 + adv_setting_id,
        name=f"adv-{adv_setting_id}",
        nmids=[11, 22],
        max_cpm=max_cpm,
    )
    if invalid:
        del adv["bot_active"]
    return CampaignSettingsRecord(
        adv_setting_id=adv_setting_id,
        wb_cabinet_id=77,
        shop_id="shop-77",
        adv_id=1000 + adv_setting_id,
        search_adv_id=2000 + adv_setting_id,
        sources=CampaignSettingsSources(
            adv_setting=adv,
            keyword_settings=[_row("KeywordSetting", text="alpha")],
            auto_shelf_settings=[],
            adv_time_settings=None,
            adv_time_week_masks=[],
        ),
    )


class FakeReader:
    def __init__(self, campaigns: Sequence[CampaignSettingsRecord]) -> None:
        self.batch = CabinetSettingsBatch(
            wb_cabinet_id=77,
            shop_id="shop-77",
            campaigns=tuple(campaigns),
        )
        self.loads = 0

    async def discover_cabinet_ids(self) -> tuple[int, ...]:
        return (77,)

    async def load_cabinet(self, wb_cabinet_id: int) -> CabinetSettingsBatch:
        self.loads += 1
        assert wb_cabinet_id == 77
        return self.batch


class FakeHistory:
    def __init__(self, latest: Mapping[int, str] | None = None) -> None:
        self.latest = dict(latest or {})
        self.latest_calls: list[tuple[int, tuple[int, ...]]] = []
        self.inserted: list[HistorySnapshotRow] = []

    async def latest_hashes(
        self,
        wb_cabinet_id: int,
        adv_setting_ids: Sequence[int],
    ) -> Mapping[int, str]:
        self.latest_calls.append((wb_cabinet_id, tuple(adv_setting_ids)))
        return {key: self.latest[key] for key in adv_setting_ids if key in self.latest}

    async def insert_snapshots(self, rows: Sequence[HistorySnapshotRow]) -> None:
        self.inserted.extend(rows)

    async def timeline(self, *args, **kwargs):
        return ()


class FakeCoordinator:
    def __init__(self, alive: Sequence[bool] = (True, True)) -> None:
        self._states = list(alive)
        self.calls = 0

    async def transaction_alive(self) -> bool:
        self.calls += 1
        if self._states:
            return self._states.pop(0)
        return True


_NOW = datetime(2026, 10, 4, 0, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_first_observation_inserts_baseline_snapshot() -> None:
    reader = FakeReader([_campaign()])
    history = FakeHistory()

    result = await collect_cabinet(
        wb_cabinet_id=77,
        reader=reader,
        history=history,
        coordinator=FakeCoordinator(),
        now=lambda: _NOW,
        new_snapshot_id=lambda: "snap-1",
    )

    assert result.code == "ok"
    assert result.inserted == 1
    assert result.unchanged == 0
    assert len(history.inserted) == 1
    row = history.inserted[0]
    assert row.snapshot_id == "snap-1"
    assert row.shop_id == "shop-77"
    assert row.schema_version == 1
    assert len(row.state_hash) == 64
    assert '"schema_version":1' in row.payload_json


@pytest.mark.asyncio
async def test_same_latest_hash_skips_duplicate() -> None:
    reader = FakeReader([_campaign()])
    probe = FakeHistory()
    first = await collect_cabinet(
        wb_cabinet_id=77,
        reader=reader,
        history=probe,
        coordinator=FakeCoordinator(),
        now=lambda: _NOW,
        new_snapshot_id=lambda: "snap-1",
    )
    assert first.inserted == 1
    existing = probe.inserted[0]

    history = FakeHistory({1: existing.state_hash})
    result = await collect_cabinet(
        wb_cabinet_id=77,
        reader=FakeReader([_campaign()]),
        history=history,
        coordinator=FakeCoordinator(),
        now=lambda: _NOW,
    )

    assert result.inserted == 0
    assert result.unchanged == 1
    assert history.inserted == []


@pytest.mark.asyncio
async def test_changed_state_appends_new_snapshot() -> None:
    initial_history = FakeHistory()
    await collect_cabinet(
        wb_cabinet_id=77,
        reader=FakeReader([_campaign(max_cpm=100)]),
        history=initial_history,
        coordinator=FakeCoordinator(),
        now=lambda: _NOW,
        new_snapshot_id=lambda: "a",
    )
    prior = initial_history.inserted[0]

    changed = FakeHistory({1: prior.state_hash})
    result = await collect_cabinet(
        wb_cabinet_id=77,
        reader=FakeReader([_campaign(max_cpm=200)]),
        history=changed,
        coordinator=FakeCoordinator(),
        now=lambda: _NOW,
        new_snapshot_id=lambda: "b",
    )

    assert result.inserted == 1
    assert changed.inserted[0].state_hash != prior.state_hash


@pytest.mark.asyncio
async def test_invalid_campaign_does_not_block_valid_campaign() -> None:
    history = FakeHistory()

    result = await collect_cabinet(
        wb_cabinet_id=77,
        reader=FakeReader([_campaign(1), _campaign(2, invalid=True)]),
        history=history,
        coordinator=FakeCoordinator(),
        now=lambda: _NOW,
        new_snapshot_id=lambda: "valid-only",
    )

    assert result.code == "partial_invalid"
    assert result.campaigns_read == 2
    assert result.invalid == 1
    assert result.inserted == 1
    assert [row.adv_setting_id for row in history.inserted] == [1]


@pytest.mark.asyncio
async def test_coordinator_loss_before_insert_prevents_history_write() -> None:
    history = FakeHistory()

    result = await collect_cabinet(
        wb_cabinet_id=77,
        reader=FakeReader([_campaign()]),
        history=history,
        coordinator=FakeCoordinator((True, False)),
        now=lambda: _NOW,
    )

    assert result.code == "coordinator_lost"
    assert result.inserted == 0
    assert history.inserted == []


@pytest.mark.asyncio
async def test_coordinator_loss_before_read_does_not_touch_ports() -> None:
    reader = FakeReader([_campaign()])
    history = FakeHistory()

    result = await collect_cabinet(
        wb_cabinet_id=77,
        reader=reader,
        history=history,
        coordinator=FakeCoordinator((False,)),
    )

    assert result.code == "coordinator_lost"
    assert reader.loads == 0
    assert history.latest_calls == []
    assert history.inserted == []


@pytest.mark.asyncio
async def test_reverted_state_a_to_b_to_a_appends_new_a_observation() -> None:
    """Spec campaign-settings-history: polling history preserves a later reversion event."""
    first_history = FakeHistory()
    await collect_cabinet(
        wb_cabinet_id=77,
        reader=FakeReader([_campaign(max_cpm=100)]),
        history=first_history,
        coordinator=FakeCoordinator(),
        now=lambda: _NOW,
        new_snapshot_id=lambda: "a-first",
    )
    first_a = first_history.inserted[0]

    b_history = FakeHistory({1: first_a.state_hash})
    await collect_cabinet(
        wb_cabinet_id=77,
        reader=FakeReader([_campaign(max_cpm=200)]),
        history=b_history,
        coordinator=FakeCoordinator(),
        now=lambda: _NOW,
        new_snapshot_id=lambda: "b",
    )
    b_row = b_history.inserted[0]
    assert b_row.state_hash != first_a.state_hash

    reverted = FakeHistory({1: b_row.state_hash})
    result = await collect_cabinet(
        wb_cabinet_id=77,
        reader=FakeReader([_campaign(max_cpm=100)]),
        history=reverted,
        coordinator=FakeCoordinator(),
        now=lambda: _NOW,
        new_snapshot_id=lambda: "a-later",
    )

    assert result.inserted == 1
    assert reverted.inserted[0].state_hash == first_a.state_hash
    assert reverted.inserted[0].snapshot_id == "a-later"


@pytest.mark.asyncio
async def test_latest_hash_read_failure_causes_zero_history_inserts() -> None:
    """Spec campaign-settings-history: unknown durable comparison state fails closed."""

    class FailingLatestHistory(FakeHistory):
        async def latest_hashes(
            self,
            wb_cabinet_id: int,
            adv_setting_ids: Sequence[int],
        ) -> Mapping[int, str]:
            raise RuntimeError("synthetic latest-hash read failure")

    history = FailingLatestHistory()

    with pytest.raises(RuntimeError, match="latest-hash read failure"):
        await collect_cabinet(
            wb_cabinet_id=77,
            reader=FakeReader([_campaign()]),
            history=history,
            coordinator=FakeCoordinator(),
        )

    assert history.inserted == []


@pytest.mark.asyncio
async def test_insert_failure_is_retryable_and_never_mutates_source_settings() -> None:
    """Spec campaign-settings-history: CH insert failure leaves PG-owned input retryable."""

    class FailingInsertHistory(FakeHistory):
        async def insert_snapshots(
            self,
            rows: Sequence[HistorySnapshotRow],
        ) -> None:
            raise RuntimeError("synthetic history insert failure")

    campaign = _campaign(max_cpm=321)
    original_max_cpm = campaign.sources.adv_setting["max_cpm"]

    with pytest.raises(RuntimeError, match="history insert failure"):
        await collect_cabinet(
            wb_cabinet_id=77,
            reader=FakeReader([campaign]),
            history=FailingInsertHistory(),
            coordinator=FakeCoordinator(),
        )

    assert campaign.sources.adv_setting["max_cpm"] == original_max_cpm

    retry = FakeHistory()
    result = await collect_cabinet(
        wb_cabinet_id=77,
        reader=FakeReader([campaign]),
        history=retry,
        coordinator=FakeCoordinator(),
        new_snapshot_id=lambda: "retry-success",
    )

    assert result.inserted == 1
    assert retry.inserted[0].snapshot_id == "retry-success"
