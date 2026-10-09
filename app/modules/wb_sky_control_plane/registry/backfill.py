"""Idempotent safe backfill registry rows from AdvSetting anchors."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.wb_sky_control_plane.registry.anchor import (
    build_anchor_fingerprint,
    generate_resource_id,
)
from app.modules.wb_sky_control_plane.registry.model import WbSkyCampaignResourceRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BackfillStats:
    """Статистика backfill (read-only insert, no AdvSetting mutation)."""

    inserted: int = 0
    skipped_shadow: int = 0
    skipped_ambiguous: int = 0
    skipped_existing: int = 0


def _physical_search_adv_id(row: AdvSetting) -> int | None:
    """Physical _search_adv_id only — never name-derived search_adv_id property."""
    return row._search_adv_id  # pyright: ignore[reportPrivateUsage]


@dataclass(frozen=True, slots=True)
class _RowAnchor:
    """Normalized anchor view for topology checks."""

    row_id: int
    wb_cabinet_id: int
    auto_adv_id: int
    search_adv_id: int | None
    nm_ids: list[int]


def _collect_row_anchors(rows: list[AdvSetting]) -> list[_RowAnchor]:
    out: list[_RowAnchor] = []
    for row in rows:
        adv_id = row.adv_id
        assert adv_id is not None  # filtered by AdvSetting.adv_id.is_not(None)
        out.append(
            _RowAnchor(
                row_id=row.id,
                wb_cabinet_id=row.wb_cabinet_id,
                auto_adv_id=adv_id,
                search_adv_id=_physical_search_adv_id(row),
                nm_ids=list(row.nmids or []),
            )
        )
    return out


def _is_search_shadow_row(anchor: _RowAnchor, search_ids_by_cabinet: dict[int, set[int]]) -> bool:
    """Legacy Search shadow: adv_id equals a Search WB campaign ID owned elsewhere."""
    owned_search_ids = search_ids_by_cabinet.get(anchor.wb_cabinet_id, set())
    return anchor.search_adv_id is None and anchor.auto_adv_id in owned_search_ids


def _detect_ambiguity(anchors: list[_RowAnchor]) -> set[int]:
    """Return row_ids that must be skipped (shared search, self-ref, cross-cabinet, cycle)."""
    ambiguous: set[int] = set()

    search_owner: dict[tuple[int, int], int] = {}
    for anchor in anchors:
        if anchor.search_adv_id is None:
            continue
        key = (anchor.wb_cabinet_id, anchor.search_adv_id)
        owner = search_owner.get(key)
        if owner is not None and owner != anchor.row_id:
            ambiguous.add(anchor.row_id)
            ambiguous.add(owner)
        else:
            search_owner[key] = anchor.row_id

    for anchor in anchors:
        if (
            anchor.search_adv_id is not None
            and anchor.auto_adv_id == anchor.search_adv_id
        ):
            ambiguous.add(anchor.row_id)

    auto_owner: dict[int, tuple[int, int]] = {}
    for anchor in anchors:
        existing = auto_owner.get(anchor.auto_adv_id)
        if existing is not None:
            existing_cab, existing_row = existing
            if existing_cab != anchor.wb_cabinet_id:
                ambiguous.add(anchor.row_id)
                ambiguous.add(existing_row)
            elif existing_row != anchor.row_id:
                ambiguous.add(anchor.row_id)
                ambiguous.add(existing_row)
        else:
            auto_owner[anchor.auto_adv_id] = (anchor.wb_cabinet_id, anchor.row_id)

    graph: dict[int, int] = {}
    for anchor in anchors:
        if anchor.search_adv_id is not None:
            graph[anchor.row_id] = anchor.search_adv_id

    for start in graph:
        visited: set[int] = set()
        current = start
        while current in graph.values():
            next_rows = [row_id for row_id, search_id in graph.items() if search_id == current]
            if not next_rows:
                break
            if len(next_rows) > 1:
                ambiguous.update(next_rows)
                break
            nxt = next_rows[0]
            if nxt in visited:
                ambiguous.add(nxt)
                ambiguous.add(start)
                break
            visited.add(nxt)
            current = nxt

    return ambiguous


async def backfill_campaign_resource_registry(
    session: AsyncSession,
    *,
    wb_cabinet_id: int | None = None,
    dry_run: bool = False,
) -> BackfillStats:
    """Idempotent backfill: exclude shadow rows, skip ambiguous anchors.

    Uses physical AdvSetting._search_adv_id only. Reuses existing resource_id
    by adv_setting_id on rerun; new ids are random UUID-derived cmp_*.

    Args:
        session: Async SQLAlchemy session (caller controls commit).
        wb_cabinet_id: Optional cabinet filter.
        dry_run: If True, compute only — no INSERT.

    Returns:
        BackfillStats counters.
    """
    stmt = select(AdvSetting).where(AdvSetting.adv_id.is_not(None))
    if wb_cabinet_id is not None:
        stmt = stmt.where(AdvSetting.wb_cabinet_id == wb_cabinet_id)
    result = await session.execute(stmt)
    rows = list(result.scalars().all())

    anchors = _collect_row_anchors(rows)
    search_ids_by_cabinet: dict[int, set[int]] = {}
    for anchor in anchors:
        if anchor.search_adv_id is not None:
            search_ids_by_cabinet.setdefault(anchor.wb_cabinet_id, set()).add(
                anchor.search_adv_id
            )

    ambiguous_row_ids = _detect_ambiguity(anchors)
    stats = BackfillStats()

    for anchor in anchors:
        if anchor.row_id in ambiguous_row_ids:
            stats = BackfillStats(
                inserted=stats.inserted,
                skipped_shadow=stats.skipped_shadow,
                skipped_ambiguous=stats.skipped_ambiguous + 1,
                skipped_existing=stats.skipped_existing,
            )
            logger.warning(
                "registry backfill ambiguous anchor skipped adv_setting_id=%s",
                anchor.row_id,
            )
            continue

        if _is_search_shadow_row(anchor, search_ids_by_cabinet):
            stats = BackfillStats(
                inserted=stats.inserted,
                skipped_shadow=stats.skipped_shadow + 1,
                skipped_ambiguous=stats.skipped_ambiguous,
                skipped_existing=stats.skipped_existing,
            )
            continue

        fingerprint = build_anchor_fingerprint(
            wb_cabinet_id=anchor.wb_cabinet_id,
            auto_adv_id=anchor.auto_adv_id,
            search_adv_id=anchor.search_adv_id,
            nm_ids=anchor.nm_ids,
        )

        existing_by_adv = await session.execute(
            select(WbSkyCampaignResourceRegistry).where(
                WbSkyCampaignResourceRegistry.adv_setting_id == anchor.row_id
            )
        )
        existing_row = existing_by_adv.scalar_one_or_none()
        if existing_row is not None:
            stats = BackfillStats(
                inserted=stats.inserted,
                skipped_shadow=stats.skipped_shadow,
                skipped_ambiguous=stats.skipped_ambiguous,
                skipped_existing=stats.skipped_existing + 1,
            )
            continue

        existing_by_anchor = await session.execute(
            select(WbSkyCampaignResourceRegistry).where(
                WbSkyCampaignResourceRegistry.wb_cabinet_id == anchor.wb_cabinet_id,
                WbSkyCampaignResourceRegistry.anchor_fingerprint == fingerprint,
            )
        )
        if existing_by_anchor.scalar_one_or_none() is not None:
            stats = BackfillStats(
                inserted=stats.inserted,
                skipped_shadow=stats.skipped_shadow,
                skipped_ambiguous=stats.skipped_ambiguous,
                skipped_existing=stats.skipped_existing + 1,
            )
            continue

        if dry_run:
            stats = BackfillStats(
                inserted=stats.inserted + 1,
                skipped_shadow=stats.skipped_shadow,
                skipped_ambiguous=stats.skipped_ambiguous,
                skipped_existing=stats.skipped_existing,
            )
            continue

        session.add(
            WbSkyCampaignResourceRegistry(
                resource_id=generate_resource_id(),
                wb_cabinet_id=anchor.wb_cabinet_id,
                adv_setting_id=anchor.row_id,
                auto_adv_id=anchor.auto_adv_id,
                search_adv_id=anchor.search_adv_id,
                anchor_fingerprint=fingerprint,
                backfill_status="active",
            )
        )
        stats = BackfillStats(
            inserted=stats.inserted + 1,
            skipped_shadow=stats.skipped_shadow,
            skipped_ambiguous=stats.skipped_ambiguous,
            skipped_existing=stats.skipped_existing,
        )
    return stats
