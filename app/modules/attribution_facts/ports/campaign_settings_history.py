"""Порт as-of чтения campaign settings history для membership."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class HistorySnapshotView:
    """Снимок history, пригодный для membership resolver."""

    snapshot_id: str
    observed_at: datetime
    payload_json: str


class CampaignSettingsHistoryAsOfPort(Protocol):
    """Read-only as-of snapshots по adv_setting_id."""

    async def snapshots_covering(
        self,
        adv_setting_id: int,
        *,
        range_start: datetime,
        range_end: datetime,
    ) -> tuple[HistorySnapshotView, ...]:
        """
        Вернуть snapshots в [range_start, range_end) в порядке observed_at.

        Args:
            adv_setting_id: PG adv_setting id.
            range_start: Нижняя граница observed_at (inclusive).
            range_end: Верхняя граница observed_at (exclusive).
        """
        ...
