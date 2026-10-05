"""Build root DATA_MAP.json documenting keyword dataset semantics."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.modules.ai_package_v1.keyword_performance.domain.export_field_registry import (
    build_export_field_matrix,
)


def _legacy_source_field_summary() -> list[dict[str, str]]:
    """Compact legacy summary; full per-field matrix is export_field_matrix."""
    return [
        {
            "field": "export_field_matrix",
            "source": "export_field_registry.EXPORT_FIELD_SPECS",
            "units": "metadata",
            "coverage_when_absent": "contract test validates completeness",
        },
        {
            "field": "keyword_coverage.datasets.*.metric_coverage",
            "source": "coverage_assembler per identity×day cohort",
            "units": "counts",
            "coverage_when_absent": "requested/observed/missing per metric",
        },
        {
            "field": "keyword_coverage.bid_decision_log",
            "source": "ChBidDecisionProbe before timeline fetch",
            "units": "status enum",
            "coverage_when_absent": "UNSUPPORTED|FAILED|AVAILABLE_EMPTY",
        },
    ]


def build_data_map(
    *,
    cutoff: PackageCutoff,
    daily_first: date | None,
    daily_last: date | None,
    position_first: date | None,
    position_last: date | None,
    export_period_note: str,
) -> dict[str, Any]:
    """Construct DATA_MAP root document per Owner §18."""
    return {
        "schema_version": "1.0.0",
        "source_calendar_timezone": "UNKNOWN",
        "package_calculation_timezone": "UTC",
        "package_cutoff_date": cutoff.package_cutoff_date.isoformat(),
        "package_cutoff_instant": cutoff.package_cutoff_instant.isoformat(),
        "last_closed_calendar_day": cutoff.last_closed_calendar_day.isoformat(),
        "ownership_evidence_scope": "REQUESTED_SHOP_PG_PLUS_GLOBAL_ADV_ID_OVERLAP",
        "source_period_closure": "UNKNOWN",
        "position_direction": "lower_is_better",
        "position_delta_convention": "position_end - position_start (negative = improvement)",
        "rate_units": "ratio_0_to_1_not_percent",
        "finite_json_rule": "null_for_missing_or_non_finite",
        "raw_query_semantics": "null unless distinct source raw proven; norm_query never copied",
        "export_period_vs_keyword_history": export_period_note,
        "per_source_cutoff": {
            "clusters_adv_stats": "date <= package_cutoff_date AND timestamp <= package_cutoff_instant",
            "keyword_position_from_api": "date <= package_cutoff_date AND version <= cutoff_instant_ms",
            "bid_decision_log": (
                "decision_time <= package_cutoff_instant AND "
                "stats_max_timestamp <= package_cutoff_instant when present"
            ),
        },
        "keyword_history_bounds": {
            "daily_first_available": daily_first.isoformat() if daily_first else None,
            "daily_last_available": daily_last.isoformat() if daily_last else None,
            "position_first_available": position_first.isoformat() if position_first else None,
            "position_last_available": position_last.isoformat() if position_last else None,
        },
        "datasets": {
            "keyword_daily": {
                "grain": "shop_id × adv_setting_id × adv_id × leg_role × nmid × norm_query × date",
                "primary_key": [
                    "adv_id",
                    "leg_role",
                    "nmid",
                    "norm_query",
                    "date",
                ],
                "source": "default_db.clusters_adv_stats",
                "snapshot_selection": "row_coherent_max_timestamp",
            },
            "keyword_windows": {
                "grain": "identity × window_id",
                "rate_formula": "sum(numerator)/sum(denominator) over observed days",
                "window_catalog": [
                    "1d",
                    "3d",
                    "7d",
                    "14d",
                    "30d",
                    "90d",
                    "180d",
                    "365d",
                    "month_to_date",
                    "previous_month",
                    "quarter_to_date",
                    "previous_quarter",
                    "year_to_date",
                    "previous_year",
                    "year_before_previous",
                    "all_available",
                ],
            },
            "keyword_current_state": {
                "grain": "adv_id × nmid × norm_query",
                "campaign_slot_role": ["ACTIVE", "REBOUND_HISTORICAL", "AMBIGUOUS"],
            },
            "keyword_changes": {
                "grain": "identity × change_id × metric_name",
                "delta_convention": "relative_delta null when previous=0 or missing",
                "change_catalog": [
                    "3d_vs_prev_3d",
                    "7d_vs_prev_7d",
                    "14d_vs_prev_14d",
                    "30d_vs_prev_30d",
                    "90d_vs_prev_90d",
                    "180d_vs_prev_180d",
                    "365d_vs_prev_365d",
                    "mtd_vs_prev_mtd",
                    "qtd_vs_prev_qtd",
                    "ytd_vs_prev_ytd",
                ],
            },
            "keyword_positions": {
                "grain": "nmid × source_query_text × date",
                "position_types": ["CLUSTER_AVG_POS", "WB_KEYWORD_POSITION_API"],
                "norm_query_provenance": [
                    "PROVEN_EQUAL",
                    "NORMALIZATION_UNPROVEN",
                ],
            },
            "keyword_position_windows": {
                "grain": "shop_id × nmid × source_query_text × position_type × window_id",
            },
            "keyword_position_current": {
                "grain": "shop_id × nmid × source_query_text × position_type latest",
            },
            "keyword_decisions": {
                "grain": "adv_id × nmid × norm_query × decision_time",
                "event_class": "source_derived_DECISION",
                "source_kind": "RETROSPECTIVE_COMPUTED_CONTEXT",
                "native_event_class_column": False,
            },
        },
        "comparable_window_formulas": {
            "rolling_prev_Nd": "prev_start = current_start - N days; prev_end = current_start - 1 day",
            "mtd_vs_prev_mtd": (
                "prev MTD = previous UTC month day 1 .. min(same ordinal day, month length)"
            ),
            "qtd_vs_prev_qtd": (
                "prev QTD = previous UTC quarter day 1 .. min(same ordinal day, quarter length)"
            ),
            "ytd_vs_prev_ytd": (
                "prev YTD = previous UTC year Jan 1 .. min(same month/day, leap-safe Feb 29→28)"
            ),
            "open_mtd_qtd_ytd": (
                "period start = UTC month/quarter/year of package_cutoff_date; "
                "end = last_closed_calendar_day; empty when end < period start"
            ),
            "calendar_previous_month_quarter_year": (
                "full closed previous calendar month/quarter/year (not elapsed-day truncated)"
            ),
            "rate_pp_delta": "percentage_point = (current - previous) * 100 for ratio metrics",
            "position_delta": "cluster_avg_pos_end - cluster_avg_pos_start; negative = improvement",
        },
        "export_field_matrix": build_export_field_matrix(),
        "source_field_matrix": _legacy_source_field_summary(),
        "campaign_identity": {
            "campaign_id_in_full_adv_wb_stat": (
                "Physical WB adv_id; exported as campaign_id in campaign_full_stat.csv"
            ),
            "adv_id_in_keyword_daily": "Same physical id as campaign_id; leg_role required for Auto/Search",
            "pg_logical_campaign": "adv_setting_id + auto_adv_id/search_adv_id relation in settings snapshot",
        },
        "missing_zero_null": {
            "invariant": "missing_row != numeric_zero != json_null",
            "keyword_jsonl": "null metric = absent/non-finite; 0 = observed zero",
            "campaign_csv": "no row = missing day, not zero views/clicks",
        },
        "limitations": [
            "source_calendar_timezone UNKNOWN — WB reporting-day TZ not proven",
            "mv_clusters_last_state is product-level stream, not campaign authority",
        ],
    }
