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

    async def snapshots_as_of(
        self,
        adv_setting_id: int,
        *,
        as_of_exclusive: datetime,
    ) -> tuple[HistorySnapshotView, ...]:
        """
        Все snapshots с observed_at < as_of_exclusive (обычно конец event_date).

        Caller выбирает latest eligible (см. ``select_as_of_snapshot``).

        Args:
            adv_setting_id: PG adv_setting id.
            as_of_exclusive: Верхняя граница observed_at (exclusive).
        """
        ...
