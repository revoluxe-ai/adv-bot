"""Pure orchestration change-only collector.

Spec: campaign-settings-history.
Collector reads complete PostgreSQL-owned settings, canonicalizes, compares durable
ClickHouse hashes, and appends only changed snapshots.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from app.modules.campaign_settings_contract import (
    CanonicalizationError,
    build_canonical_settings_snapshot,
)

from .domain import (
    CabinetCollectResult,
    CabinetCoordinatorPort,
    HistoryRepositoryPort,
    HistorySnapshotRow,
    SettingsReaderPort,
)


async def collect_cabinet(
    *,
    wb_cabinet_id: int,
    reader: SettingsReaderPort,
    history: HistoryRepositoryPort,
    coordinator: CabinetCoordinatorPort,
    now: Callable[[], datetime] | None = None,
    new_snapshot_id: Callable[[], str] | None = None,
) -> CabinetCollectResult:
    """Collect one cabinet while caller owns its PG xact advisory lock."""
    now_fn = now or (lambda: datetime.now(UTC))
    id_fn = new_snapshot_id or (lambda: str(uuid4()))

    if not await coordinator.transaction_alive():
        return CabinetCollectResult(
            wb_cabinet_id=wb_cabinet_id,
            code="coordinator_lost",
        )

    batch = await reader.load_cabinet(wb_cabinet_id)
    if batch.wb_cabinet_id != wb_cabinet_id:
        return CabinetCollectResult(
            wb_cabinet_id=wb_cabinet_id,
            code="source_identity_mismatch",
        )

    snapshots: dict[int, object] = {}
    invalid = 0
    for campaign in batch.campaigns:
        try:
            snapshots[campaign.adv_setting_id] = build_canonical_settings_snapshot(
                campaign.sources
            )
        except CanonicalizationError:
            invalid += 1

    valid_ids = tuple(sorted(snapshots))
    latest = await history.latest_hashes(wb_cabinet_id, valid_ids)

    rows: list[HistorySnapshotRow] = []
    unchanged = 0
    by_id = {item.adv_setting_id: item for item in batch.campaigns}
    for adv_setting_id in valid_ids:
        snapshot = snapshots[adv_setting_id]
        # Runtime type is CanonicalSettingsSnapshot; avoid widening storage ports
        # with canonical implementation details.
        state_hash = getattr(snapshot, "state_hash")
        if latest.get(adv_setting_id) == state_hash:
            unchanged += 1
            continue
        campaign = by_id[adv_setting_id]
        rows.append(
            HistorySnapshotRow(
                observed_at=now_fn(),
                snapshot_id=id_fn(),
                adv_setting_id=adv_setting_id,
                wb_cabinet_id=wb_cabinet_id,
                shop_id=batch.shop_id,
                adv_id=campaign.adv_id,
                search_adv_id=campaign.search_adv_id,
                schema_version=getattr(snapshot, "schema_version"),
                state_hash=state_hash,
                payload_json=getattr(snapshot, "payload_json"),
            )
        )

    if rows:
        if not await coordinator.transaction_alive():
            return CabinetCollectResult(
                wb_cabinet_id=wb_cabinet_id,
                code="coordinator_lost",
                campaigns_read=len(batch.campaigns),
                unchanged=unchanged,
                invalid=invalid,
            )
        await history.insert_snapshots(rows)

    code = "ok" if invalid == 0 else "partial_invalid"
    return CabinetCollectResult(
        wb_cabinet_id=wb_cabinet_id,
        code=code,
        campaigns_read=len(batch.campaigns),
        unchanged=unchanged,
        inserted=len(rows),
        invalid=invalid,
    )
