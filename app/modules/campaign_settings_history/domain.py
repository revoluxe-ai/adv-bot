"""Domain ports/types для campaign settings history.

Spec: campaign-settings-history.
Ни один port не даёт collector права менять текущие PostgreSQL settings или WB.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.modules.campaign_settings_contract import CampaignSettingsSources


@dataclass(frozen=True, slots=True)
class CampaignSettingsRecord:
    adv_setting_id: int
    wb_cabinet_id: int
    shop_id: str
    adv_id: int | None
    search_adv_id: int | None
    sources: CampaignSettingsSources


@dataclass(frozen=True, slots=True)
class CabinetSettingsBatch:
    wb_cabinet_id: int
    shop_id: str
    campaigns: tuple[CampaignSettingsRecord, ...]


@dataclass(frozen=True, slots=True)
class HistorySnapshotRow:
    observed_at: datetime
    snapshot_id: str
    adv_setting_id: int
    wb_cabinet_id: int
    shop_id: str
    adv_id: int | None
    search_adv_id: int | None
    schema_version: int
    state_hash: str
    payload_json: str


@dataclass(frozen=True, slots=True)
class HistoryTimelineItem:
    observed_at: datetime
    snapshot_id: str
    schema_version: int
    state_hash: str
    payload_json: str


@dataclass(frozen=True, slots=True)
class CabinetCollectResult:
    wb_cabinet_id: int
    code: str
    campaigns_read: int = 0
    unchanged: int = 0
    inserted: int = 0
    invalid: int = 0


class SettingsReaderPort(Protocol):
    async def discover_cabinet_ids(self) -> tuple[int, ...]: ...

    async def load_cabinet(
        self,
        wb_cabinet_id: int,
    ) -> CabinetSettingsBatch: ...


class HistoryRepositoryPort(Protocol):
    async def latest_hashes(
        self,
        wb_cabinet_id: int,
        adv_setting_ids: Sequence[int],
    ) -> Mapping[int, str]: ...

    async def insert_snapshots(
        self,
        rows: Sequence[HistorySnapshotRow],
    ) -> None: ...

    async def timeline(
        self,
        adv_setting_id: int,
        *,
        start_at: datetime,
        end_at: datetime,
    ) -> tuple[HistoryTimelineItem, ...]: ...

    async def timeline_up_to(
        self,
        adv_setting_id: int,
        *,
        end_at: datetime,
    ) -> tuple[HistoryTimelineItem, ...]: ...


class CabinetCoordinatorPort(Protocol):
    async def transaction_alive(self) -> bool: ...
