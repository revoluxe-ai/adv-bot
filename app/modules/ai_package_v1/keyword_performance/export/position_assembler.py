"""Assemble keyword_positions.jsonl from CH position reader."""

from __future__ import annotations

from app.modules.ai_package_v1.keyword_performance.domain.enums import (
    NormQueryProvenance,
    PositionType,
    SnapshotStatus,
)
from app.modules.ai_package_v1.keyword_performance.domain.models import (
    KeywordPositionRowV1,
    RowCoverageV1,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_position_reader import (
    RawPositionRow,
)


def assemble_position_rows(
    raw_rows: list[RawPositionRow],
    *,
    manifest_shop_id: int,
    daily_norm_queries: frozenset[tuple[int, str, str]],
) -> list[KeywordPositionRowV1]:
    """Map raw position rows; norm_query only when proven equal to daily cluster key."""
    result: list[KeywordPositionRowV1] = []
    for raw in raw_rows:
        ambiguous = raw.tuple_variants_at_max_version > 1
        status = SnapshotStatus.AMBIGUOUS if ambiguous else SnapshotStatus.OK
        norm_query: str | None = None
        provenance = NormQueryProvenance.NORMALIZATION_UNPROVEN
        if (raw.nmid, raw.stat_date.isoformat(), raw.text) in daily_norm_queries:
            norm_query = raw.text
            provenance = NormQueryProvenance.PROVEN_EQUAL
        observed: list[str] = []
        missing: list[str] = []
        reason_codes: list[str] = []
        if ambiguous:
            reason_codes.append("SNAPSHOT_CONFLICT")
            missing.append("avr_position")
        elif raw.avr_position is not None:
            observed.append("avr_position")
        else:
            missing.append("avr_position")
        result.append(
            KeywordPositionRowV1(
                shop_id=manifest_shop_id,
                adv_id=None,
                nmid=raw.nmid,
                norm_query=norm_query,
                norm_query_provenance=provenance,
                source_query_text=raw.text,
                date=raw.stat_date.isoformat(),
                position_type=PositionType.WB_KEYWORD_POSITION_API,
                source_version=raw.version,
                avr_position=raw.avr_position if not ambiguous else None,
                total_views=raw.total_views if not ambiguous else None,
                orders=raw.orders if not ambiguous else None,
                snapshot_status=status,
                source="keyword_position_from_api",
                row_coverage=RowCoverageV1(
                    observed=tuple(observed),
                    missing=tuple(missing),
                    reason_codes=tuple(reason_codes),
                ),
            )
        )
    return result
