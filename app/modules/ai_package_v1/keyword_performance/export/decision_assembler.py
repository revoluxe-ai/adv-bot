"""Assemble keyword_decisions.jsonl from CH bid_decision_log timeline."""

from __future__ import annotations

from datetime import datetime

from app.modules.ai_package_v1.keyword_performance.domain.enums import (
    SnapshotStatus,
)
from app.modules.ai_package_v1.keyword_performance.domain.models import (
    KeywordDecisionRowV1,
    RowCoverageV1,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_bid_decision_reader import (
    RawBidDecisionRow,
)


def _iso_dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def assemble_decision_rows(
    raw_rows: list[RawBidDecisionRow],
    *,
    manifest_shop_id: str,
) -> list[KeywordDecisionRowV1]:
    """Map timeline rows with source-derived DECISION class and provenance."""
    result: list[KeywordDecisionRowV1] = []
    for raw in raw_rows:
        ambiguous = raw.tuple_variants_at_max_version > 1
        status = SnapshotStatus.AMBIGUOUS if ambiguous else SnapshotStatus.OK
        observed: list[str] = []
        missing: list[str] = []
        reason_codes: list[str] = []
        if ambiguous:
            reason_codes.append("SNAPSHOT_CONFLICT")
            missing.extend(
                [
                    "cpm_curr",
                    "final_bid",
                    "decision_time",
                    "stats_max_timestamp",
                    "decision_source",
                ]
            )
        else:
            if raw.cpm_curr is not None:
                observed.append("cpm_curr")
            else:
                missing.append("cpm_curr")
            if raw.final_bid is not None:
                observed.append("final_bid")
            else:
                missing.append("final_bid")
            if raw.decision_time is not None:
                observed.append("decision_time")
            else:
                missing.append("decision_time")
        result.append(
            KeywordDecisionRowV1(
                shop_id=manifest_shop_id,
                adv_id=raw.adv_id,
                nmid=raw.nmid,
                norm_query=raw.norm_query,
                event_class=raw.event_class,
                source_kind=raw.source_kind,
                cpm_curr=raw.cpm_curr if not ambiguous else None,
                final_bid=raw.final_bid if not ambiguous else None,
                decision_time=_iso_dt(raw.decision_time) if not ambiguous else None,
                stats_max_timestamp=_iso_dt(raw.stats_max_timestamp)
                if not ambiguous
                else None,
                decision_source=raw.decision_source if not ambiguous else None,
                version=raw.version,
                snapshot_status=status,
                row_coverage=RowCoverageV1(
                    observed=tuple(observed),
                    missing=tuple(missing),
                    reason_codes=tuple(reason_codes),
                ),
            )
        )
    return result
