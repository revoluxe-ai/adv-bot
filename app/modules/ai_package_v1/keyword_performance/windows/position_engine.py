"""Position window/latest engine at API source grain (shop × nmid × source_query_text)."""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import date

from app.modules.ai_package_v1.keyword_performance.domain.models import (
    KeywordPositionLatestRowV1,
    KeywordPositionRowV1,
    KeywordPositionWindowRowV1,
    RowCoverageV1,
)
from app.modules.ai_package_v1.keyword_performance.domain.enums import SnapshotStatus
from app.modules.ai_package_v1.keyword_performance.windows.engine import (
    WindowSpec,
    build_window_catalog,
)
from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff


def _position_identity_key(
    row: KeywordPositionRowV1,
) -> tuple[str, int, str, str]:
    return (
        row.shop_id,
        row.nmid,
        row.source_query_text,
        row.position_type.value,
    )


def _rows_in_window(
    rows: list[KeywordPositionRowV1],
    start: date,
    end: date,
) -> list[KeywordPositionRowV1]:
    result: list[KeywordPositionRowV1] = []
    for row in rows:
        d = date.fromisoformat(row.date)
        if start <= d <= end and row.snapshot_status == SnapshotStatus.OK:
            result.append(row)
    return result


def _aggregate_position_window(
    rows: list[KeywordPositionRowV1],
    spec: WindowSpec,
    identity: KeywordPositionRowV1,
) -> KeywordPositionWindowRowV1:
    observed_days = len({r.date for r in rows})
    requested = max(spec.requested_days, 0)
    missing_days = max(requested - observed_days, 0) if requested else 0
    partial = observed_days < requested if requested else False
    sorted_rows = sorted(rows, key=lambda r: r.date)
    positions = [
        (r.date, r.avr_position)
        for r in sorted_rows
        if r.avr_position is not None
    ]
    pos_start = positions[0][1] if positions else None
    pos_end = positions[-1][1] if positions else None
    pos_values = [p for _, p in positions]
    pos_best = min(pos_values) if pos_values else None
    pos_worst = max(pos_values) if pos_values else None
    pos_delta = (
        float(pos_end) - float(pos_start)
        if pos_start is not None and pos_end is not None
        else None
    )
    mean_pos = statistics.mean(pos_values) if pos_values else None
    median_pos = statistics.median(pos_values) if pos_values else None
    return KeywordPositionWindowRowV1(
        shop_id=identity.shop_id,
        adv_id=identity.adv_id,
        nmid=identity.nmid,
        norm_query=identity.norm_query,
        norm_query_provenance=identity.norm_query_provenance,
        source_query_text=identity.source_query_text,
        position_type=identity.position_type,
        window_id=spec.window_id,
        window_start=spec.start.isoformat(),
        window_end=spec.end.isoformat(),
        observed_days=observed_days,
        missing_days=missing_days,
        requested_days=requested,
        partial=partial,
        position_start=pos_start,
        position_end=pos_end,
        position_delta=pos_delta,
        position_best=pos_best,
        position_worst=pos_worst,
        position_mean=mean_pos,
        position_median=median_pos,
        window_coverage={
            "partial": partial,
            "observed_days": observed_days,
            "missing_days": missing_days,
        },
    )


def compute_position_windows(
    position_rows: list[KeywordPositionRowV1],
    cutoff: PackageCutoff,
    first_available: date | None,
    last_available: date | None,
) -> list[KeywordPositionWindowRowV1]:
    """Compute position windows per API source identity."""
    grouped: dict[tuple[str, int, str, str], list[KeywordPositionRowV1]] = (
        defaultdict(list)
    )
    for row in position_rows:
        grouped[_position_identity_key(row)].append(row)
    catalog = build_window_catalog(cutoff, first_available, last_available)
    export_specs = [s for s in catalog if not s.window_id.startswith("prev_")]
    windows: list[KeywordPositionWindowRowV1] = []
    for _key, rows in sorted(grouped.items()):
        identity = rows[0]
        for spec in export_specs:
            in_window = _rows_in_window(rows, spec.start, spec.end)
            windows.append(_aggregate_position_window(in_window, spec, identity))
    return windows


def compute_position_latest(
    position_rows: list[KeywordPositionRowV1],
) -> list[KeywordPositionLatestRowV1]:
    """Latest position per identity; never use stale when latest is NULL/conflict."""
    best: dict[tuple[str, int, str, str], KeywordPositionRowV1] = {}
    for row in position_rows:
        key = _position_identity_key(row)
        existing = best.get(key)
        if existing is None:
            best[key] = row
            continue
        if row.date > existing.date:
            best[key] = row
            continue
        if row.date == existing.date:
            row_ver = row.source_version or 0
            existing_ver = existing.source_version or 0
            if row_ver > existing_ver:
                best[key] = row
    result: list[KeywordPositionLatestRowV1] = []
    for row in sorted(best.values(), key=lambda r: (r.nmid, r.source_query_text, r.date)):
        ambiguous = row.snapshot_status == SnapshotStatus.AMBIGUOUS
        observed: list[str] = []
        missing: list[str] = []
        reason_codes: list[str] = []
        if ambiguous:
            reason_codes.append("SNAPSHOT_CONFLICT")
            missing.append("avr_position")
        elif row.avr_position is not None:
            observed.append("avr_position")
        else:
            missing.append("avr_position")
        result.append(
            KeywordPositionLatestRowV1(
                shop_id=row.shop_id,
                adv_id=row.adv_id,
                nmid=row.nmid,
                norm_query=row.norm_query,
                norm_query_provenance=row.norm_query_provenance,
                source_query_text=row.source_query_text,
                position_type=row.position_type,
                observation_date=row.date,
                source_version=row.source_version,
                avr_position=row.avr_position if not ambiguous else None,
                snapshot_status=row.snapshot_status,
                source=row.source,
                row_coverage=RowCoverageV1(
                    observed=tuple(observed),
                    missing=tuple(missing),
                    reason_codes=tuple(reason_codes),
                ),
            )
        )
    return result
