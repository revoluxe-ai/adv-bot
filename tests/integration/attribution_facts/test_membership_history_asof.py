"""As-of membership через history port (in-memory repository shape)."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from app.modules.attribution_facts.membership.resolver import MembershipSnapshotResolver
from app.modules.attribution_facts.ports.campaign_settings_history import (
    HistorySnapshotView,
)

pytestmark = pytest.mark.integration


class _HistoryRepoShape:
    """Имитация ClickHouseCampaignSettingsHistoryRepository.timeline rows."""

    def __init__(self, rows: tuple[HistorySnapshotView, ...]) -> None:
        self._rows = rows

    async def snapshots_covering(
        self,
        adv_setting_id: int,
        *,
        range_start: datetime,
        range_end: datetime,
    ) -> tuple[HistorySnapshotView, ...]:
        return tuple(
            row for row in self._rows if range_start <= row.observed_at < range_end
        )


@pytest.mark.asyncio
async def test_history_as_of_selects_latest_before_event_day_end() -> None:
    """B.6: as-of выбирает latest snapshot до конца event_date."""
    day = date(2026, 9, 7)
    rows = (
        HistorySnapshotView(
            snapshot_id="early",
            observed_at=datetime(2026, 9, 6, 23, 0),
            payload_json='{"campaign":{"nmids":[1]}}',
        ),
        HistorySnapshotView(
            snapshot_id="late",
            observed_at=datetime(2026, 9, 7, 18, 0),
            payload_json='{"campaign":{"nmids":[2]}}',
        ),
        HistorySnapshotView(
            snapshot_id="future",
            observed_at=datetime(2026, 9, 8, 1, 0),
            payload_json='{"campaign":{"nmids":[3]}}',
        ),
    )
    resolver = MembershipSnapshotResolver(
        shop_id="s",
        adv_setting_id=10,
        physical_adv_id=99,
        history_port=_HistoryRepoShape(rows),
        inventory_port=None,
    )
    resolved = await resolver.resolve(day)
    assert resolved.snapshot is not None
    assert resolved.snapshot.snapshot_id == "late"
    assert resolved.snapshot.promoted_nm_ids == frozenset({2})
