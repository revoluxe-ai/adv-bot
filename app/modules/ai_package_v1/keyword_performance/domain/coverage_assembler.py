"""Package-level coverage.json for keyword performance family."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.modules.ai_package_v1.keyword_performance.domain.models import (
    KeywordDailyRowV1,
    KeywordPositionRowV1,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_bid_decision_probe import (
    BidDecisionAvailability,
    BidDecisionSourceStatus,
)
from app.modules.ai_package_v1.keyword_performance.scope.dto import KeywordExportScope

_DAILY_METRICS = (
    "views",
    "clicks",
    "add_to_cart",
    "orders",
    "spend_rub",
    "cpm",
    "cpc",
    "ctr",
    "cluster_avg_pos",
)


def _identity_day_keys(
    daily_rows: list[KeywordDailyRowV1],
) -> set[tuple[int, int, str, str]]:
    return {
        (r.adv_id, r.nmid, r.norm_query, r.date)
        for r in daily_rows
        if r.snapshot_status.value != "AMBIGUOUS"
    }


def _identity_day_coverage_pct(
    daily_rows: list[KeywordDailyRowV1],
    *,
    first_available: date | None,
    last_available: date | None,
) -> float | None:
    """Coverage at (adv_id, nmid, norm_query, date) grain."""
    if first_available is None or last_available is None:
        return None
    calendar_days = (last_available - first_available).days + 1
    if calendar_days <= 0:
        return None
    identities = {
        (r.adv_id, r.nmid, r.norm_query)
        for r in daily_rows
        if r.snapshot_status.value != "AMBIGUOUS"
    }
    if not identities:
        return 0.0 if daily_rows else None
    identity_days = _identity_day_keys(daily_rows)
    requested = len(identities) * calendar_days
    if requested <= 0:
        return None
    return len(identity_days) / requested


def _per_metric_coverage(
    daily_rows: list[KeywordDailyRowV1],
    *,
    first_available: date | None,
    last_available: date | None,
) -> dict[str, dict[str, int | float | None]]:
    """Per-metric observed/missing at unique identity×day cohort."""
    if first_available is None or last_available is None:
        return {}
    cohort = _identity_day_keys(daily_rows)
    requested = len(cohort)
    if requested <= 0:
        return {}
    result: dict[str, dict[str, int | float | None]] = {}
    for metric in _DAILY_METRICS:
        observed_keys: set[tuple[int, int, str, str]] = set()
        confirmed_zero = 0
        for row in daily_rows:
            if row.snapshot_status.value == "AMBIGUOUS":
                continue
            key = (row.adv_id, row.nmid, row.norm_query, row.date)
            if key not in cohort:
                continue
            value = getattr(row, metric, None)
            if value is None:
                continue
            observed_keys.add(key)
            if value == 0:
                confirmed_zero += 1
        observed = len(observed_keys)
        missing = requested - observed
        result[metric] = {
            "requested": requested,
            "observed": observed,
            "missing": missing,
            "confirmed_zero": confirmed_zero,
            "coverage_pct": observed / requested if requested else None,
        }
    return result


def _position_identities(
    position_rows: list[KeywordPositionRowV1],
) -> set[tuple[int, str]]:
    return {(r.nmid, r.source_query_text) for r in position_rows}


def _position_identity_day_keys(
    position_rows: list[KeywordPositionRowV1],
) -> set[tuple[int, str, str]]:
    return {
        (r.nmid, r.source_query_text, r.date)
        for r in position_rows
        if r.snapshot_status.value != "AMBIGUOUS"
    }


def _position_coverage_pct(
    position_rows: list[KeywordPositionRowV1],
    *,
    first_available: date | None,
    last_available: date | None,
) -> float | None:
    """Position coverage at (nmid, source_query_text, date) — not raw row count."""
    if first_available is None or last_available is None:
        return None
    calendar_days = (last_available - first_available).days + 1
    if calendar_days <= 0:
        return None
    identities = _position_identities(position_rows)
    if not identities:
        return None
    identity_days = _position_identity_day_keys(position_rows)
    requested = len(identities) * calendar_days
    if requested <= 0:
        return None
    return len(identity_days) / requested


def _position_metric_coverage(
    position_rows: list[KeywordPositionRowV1],
    *,
    first_available: date | None,
    last_available: date | None,
) -> dict[str, dict[str, int | float | None]]:
    cohort = _position_identity_day_keys(position_rows)
    requested = len(cohort)
    if requested <= 0:
        return {}
    observed_keys: set[tuple[int, str, str]] = set()
    for row in position_rows:
        if row.snapshot_status.value == "AMBIGUOUS":
            continue
        key = (row.nmid, row.source_query_text, row.date)
        if key not in cohort:
            continue
        if row.avr_position is not None:
            observed_keys.add(key)
    observed = len(observed_keys)
    return {
        "avr_position": {
            "requested": requested,
            "observed": observed,
            "missing": requested - observed,
            "confirmed_zero": 0,
            "coverage_pct": observed / requested if requested else None,
        }
    }


def build_coverage_json(
    *,
    scope: KeywordExportScope,
    cutoff: PackageCutoff,
    daily_first: date | None,
    daily_last: date | None,
    position_first: date | None,
    position_last: date | None,
    daily_rows: list[KeywordDailyRowV1],
    position_rows: list[KeywordPositionRowV1],
    bid_decision: BidDecisionAvailability,
    reason_codes: frozenset[str],
) -> dict[str, Any]:
    """Assemble coverage dimensions per source/metric at identity-day grain."""
    daily_coverage_pct = _identity_day_coverage_pct(
        daily_rows,
        first_available=daily_first,
        last_available=daily_last,
    )
    position_coverage_pct = _position_coverage_pct(
        position_rows,
        first_available=position_first,
        last_available=position_last,
    )

    bid_status = bid_decision.status.value
    bid_supported = bid_decision.status in (
        BidDecisionSourceStatus.AVAILABLE,
        BidDecisionSourceStatus.AVAILABLE_EMPTY,
    )

    return {
        "schema_version": "1.0.0",
        "package_cutoff_instant": cutoff.package_cutoff_instant.isoformat(),
        "ownership_evidence_scope": "REQUESTED_SHOP_PG_PLUS_GLOBAL_ADV_ID_OVERLAP",
        "datasets": {
            "keyword_daily": {
                "requested": len(scope.all_adv_ids),
                "returned": len(daily_rows),
                "observed": len(daily_rows),
                "first_available": daily_first.isoformat() if daily_first else None,
                "last_available": daily_last.isoformat() if daily_last else None,
                "coverage_pct": daily_coverage_pct,
                "metric_coverage": _per_metric_coverage(
                    daily_rows,
                    first_available=daily_first,
                    last_available=daily_last,
                ),
            },
            "keyword_positions": {
                "requested": len(_position_identities(position_rows)),
                "returned": len(position_rows),
                "observed": len(_position_identity_day_keys(position_rows)),
                "first_available": position_first.isoformat() if position_first else None,
                "last_available": position_last.isoformat() if position_last else None,
                "coverage_pct": position_coverage_pct,
                "metric_coverage": _position_metric_coverage(
                    position_rows,
                    first_available=position_first,
                    last_available=position_last,
                ),
            },
            "bid_decision_log": {
                "supported": bid_supported,
                "status": bid_status,
                "has_native_event_class_column": bid_decision.has_native_event_class,
                "present_columns": sorted(bid_decision.present_columns),
                "missing_required_columns": sorted(bid_decision.missing_required_columns),
                "missing_optional_columns": sorted(bid_decision.missing_optional_columns),
                "event_class_semantics": "source_derived_DECISION_not_native_column",
            },
        },
        "reason_codes": sorted(reason_codes),
        "missing_vs_zero": "missing rows are null/absent; confirmed_zero is explicit only",
    }
