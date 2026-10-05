"""Registry of every exported keyword-performance field with source/formula metadata.

Used by DATA_MAP builder and contract tests to prove per-field coverage (not
two-key presence checks). Each entry documents grain, nullable semantics, and
provenance for auditor review.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from app.modules.ai_package_v1.keyword_performance.domain.models import (
    KeywordChangeRowV1,
    KeywordCurrentStateRowV1,
    KeywordDailyRowV1,
    KeywordDecisionRowV1,
    KeywordPositionLatestRowV1,
    KeywordPositionRowV1,
    KeywordPositionWindowRowV1,
    KeywordWindowRowV1,
    RowCoverageV1,
)

_REQUIRED_MATRIX_KEYS = frozenset(
    {
        "field",
        "dataset",
        "source",
        "units",
        "nullable",
        "coverage_when_absent",
        "formula",
        "grain",
    }
)


@dataclass(frozen=True, slots=True)
class ExportFieldSpec:
    """Single exported field metadata row for DATA_MAP matrix."""

    field: str
    dataset: str
    source: str
    units: str
    nullable: bool
    coverage_when_absent: str
    formula: str
    grain: str
    pk: bool = False
    nested: str | None = None

    def to_matrix_row(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "field": self.field,
            "dataset": self.dataset,
            "source": self.source,
            "units": self.units,
            "nullable": self.nullable,
            "coverage_when_absent": self.coverage_when_absent,
            "formula": self.formula,
            "grain": self.grain,
        }
        if self.pk:
            row["primary_key"] = True
        if self.nested is not None:
            row["nested_in"] = self.nested
        return row


def _specs(*entries: ExportFieldSpec) -> tuple[ExportFieldSpec, ...]:
    return entries


_DAILY_GRAIN = "shop_id × adv_setting_id × adv_id × leg_role × nmid × norm_query × date"
_WINDOW_GRAIN = "shop_id × adv_setting_id × adv_id × leg_role × nmid × norm_query × window_id"
_CURRENT_GRAIN = "adv_id × nmid × norm_query (latest daily)"
_CHANGE_GRAIN = "identity × change_id × metric_name"
_POSITION_GRAIN = "shop_id × nmid × source_query_text × date × position_type"
_POS_WINDOW_GRAIN = "shop_id × nmid × source_query_text × position_type × window_id"
_POS_CURRENT_GRAIN = "shop_id × nmid × source_query_text × position_type latest"
_DECISION_GRAIN = "adv_id × nmid × norm_query × decision_time"
_COVERAGE_NESTED = "row_coverage"


EXPORT_FIELD_SPECS: tuple[ExportFieldSpec, ...] = (
    *_specs(
        ExportFieldSpec("schema_version", "keyword_daily", "constant", "semver", False, "required", "SCHEMA_VERSION_KEYWORD", _DAILY_GRAIN),
        ExportFieldSpec("shop_id", "keyword_daily", "manifest_shop_id", "int", False, "required", "manifest scope", _DAILY_GRAIN),
        ExportFieldSpec("adv_setting_id", "keyword_daily", "PG AdvSetting.id via scope", "int", True, "null when unmapped", "scope join", _DAILY_GRAIN),
        ExportFieldSpec("adv_id", "keyword_daily", "clusters_adv_stats.adv_id", "int", False, "required PK", "physical CH adv_id", _DAILY_GRAIN, pk=True),
        ExportFieldSpec("leg_role", "keyword_daily", "scope assignment", "enum", False, "required", "AUTO|SEARCH|REBOUND_*", _DAILY_GRAIN),
        ExportFieldSpec("nmid", "keyword_daily", "clusters_adv_stats.nmid", "int", False, "required PK", "product id", _DAILY_GRAIN, pk=True),
        ExportFieldSpec("norm_query", "keyword_daily", "clusters_adv_stats.norm_query", "text", False, "required PK", "normalized query key", _DAILY_GRAIN, pk=True),
        ExportFieldSpec("raw_query", "keyword_daily", "none proven", "text", True, "RAW_QUERY_UNAVAILABLE → null", "never copy norm_query", _DAILY_GRAIN),
        ExportFieldSpec("raw_query_status", "keyword_daily", "export policy", "enum", False, "RAW_QUERY_UNAVAILABLE default", "status not fabricated text", _DAILY_GRAIN),
        ExportFieldSpec("date", "keyword_daily", "clusters_adv_stats.date", "date", False, "required PK", "UTC calendar day", _DAILY_GRAIN, pk=True),
        ExportFieldSpec("observation_ts", "keyword_daily", "clusters_adv_stats.timestamp", "datetime", True, "null when absent", "snapshot max ts", _DAILY_GRAIN),
        ExportFieldSpec("views", "keyword_daily", "clusters_adv_stats.views", "count", True, "missing not zero", "row-coherent snapshot", _DAILY_GRAIN),
        ExportFieldSpec("clicks", "keyword_daily", "clusters_adv_stats.clicks", "count", True, "missing not zero", "row-coherent snapshot", _DAILY_GRAIN),
        ExportFieldSpec("add_to_cart", "keyword_daily", "clusters_adv_stats.add_to_cart", "count", True, "missing not zero", "row-coherent snapshot", _DAILY_GRAIN),
        ExportFieldSpec("orders", "keyword_daily", "clusters_adv_stats.orders", "count", True, "missing not zero", "row-coherent snapshot", _DAILY_GRAIN),
        ExportFieldSpec("spend_rub", "keyword_daily", "clusters_adv_stats.spend", "RUB", True, "UNAVAILABLE if null", "QUERY_SPEND_STATUS mapper", _DAILY_GRAIN),
        ExportFieldSpec("query_spend_status", "keyword_daily", "spend mapper", "enum", False, "UNAVAILABLE default", "FACTUAL only when spend non-null", _DAILY_GRAIN),
        ExportFieldSpec("cpm", "keyword_daily", "clusters_adv_stats.cpm", "RUB", True, "null + coverage", "source column not CPM×views", _DAILY_GRAIN),
        ExportFieldSpec("cpc", "keyword_daily", "clusters_adv_stats.cpc", "RUB", True, "null + coverage", "source column", _DAILY_GRAIN),
        ExportFieldSpec("ctr", "keyword_daily", "derived", "ratio 0..1", True, "null if views=0/missing", "clicks/views same-row", _DAILY_GRAIN),
        ExportFieldSpec("conv_views_to_cart", "keyword_daily", "derived", "ratio 0..1", True, "null if views missing", "add_to_cart/views aligned", _DAILY_GRAIN),
        ExportFieldSpec("conv_cart_to_order", "keyword_daily", "derived", "ratio 0..1", True, "null if cart missing", "orders/add_to_cart aligned", _DAILY_GRAIN),
        ExportFieldSpec("conv_views_to_order", "keyword_daily", "derived", "ratio 0..1", True, "null if views missing", "orders/views aligned", _DAILY_GRAIN),
        ExportFieldSpec("cpo_rub", "keyword_daily", "derived", "RUB", True, "null unless FACTUAL spend & orders>0", "spend/orders aligned", _DAILY_GRAIN),
        ExportFieldSpec("cluster_avg_pos", "keyword_daily", "clusters_adv_stats.avr_pos", "rank", True, "null not 0/max", "lower is better", _DAILY_GRAIN),
        ExportFieldSpec("snapshot_status", "keyword_daily", "snapshot probe", "enum", False, "OK|AMBIGUOUS", "tuple_variants_at_max_ts", _DAILY_GRAIN),
        ExportFieldSpec("source", "keyword_daily", "constant", "text", False, "clusters_adv_stats", "dataset tag", _DAILY_GRAIN),
        ExportFieldSpec("row_coverage.observed", "keyword_daily", "coverage assembler", "string[]", False, "empty when none", "per-row observed fields", _DAILY_GRAIN, nested=_COVERAGE_NESTED),
        ExportFieldSpec("row_coverage.missing", "keyword_daily", "coverage assembler", "string[]", False, "empty when none", "per-row missing fields", _DAILY_GRAIN, nested=_COVERAGE_NESTED),
        ExportFieldSpec("row_coverage.reason_codes", "keyword_daily", "coverage assembler", "string[]", False, "empty when none", "SNAPSHOT_CONFLICT etc", _DAILY_GRAIN, nested=_COVERAGE_NESTED),
    ),
    *_specs(
        ExportFieldSpec("schema_version", "keyword_windows", "constant", "semver", False, "required", "SCHEMA_VERSION_KEYWORD", _WINDOW_GRAIN),
        ExportFieldSpec("shop_id", "keyword_windows", "manifest_shop_id", "int", False, "required", "manifest scope", _WINDOW_GRAIN),
        ExportFieldSpec("adv_setting_id", "keyword_windows", "scope", "int", True, "null when unmapped", "identity carry", _WINDOW_GRAIN),
        ExportFieldSpec("adv_id", "keyword_windows", "daily identity", "int", False, "required", "physical adv_id", _WINDOW_GRAIN, pk=True),
        ExportFieldSpec("leg_role", "keyword_windows", "scope", "enum", False, "required", "leg assignment", _WINDOW_GRAIN),
        ExportFieldSpec("nmid", "keyword_windows", "daily identity", "int", False, "required", "product id", _WINDOW_GRAIN, pk=True),
        ExportFieldSpec("norm_query", "keyword_windows", "daily identity", "text", False, "required", "query key", _WINDOW_GRAIN, pk=True),
        ExportFieldSpec("window_id", "keyword_windows", "window catalog", "text", False, "required PK", "rolling|calendar|all_available", _WINDOW_GRAIN, pk=True),
        ExportFieldSpec("window_start", "keyword_windows", "window engine UTC", "date", False, "required", "inclusive start", _WINDOW_GRAIN),
        ExportFieldSpec("window_end", "keyword_windows", "window engine UTC", "date", False, "required", "inclusive end", _WINDOW_GRAIN),
        ExportFieldSpec("comparator_kind", "keyword_windows", "window catalog", "enum", False, "NONE default", "PREVIOUS_* for prev windows", _WINDOW_GRAIN),
        ExportFieldSpec("observed_days", "keyword_windows", "window engine", "count", False, "0 when empty", "distinct dates in window", _WINDOW_GRAIN),
        ExportFieldSpec("missing_days", "keyword_windows", "window engine", "count", False, "requested - observed", "calendar gap count", _WINDOW_GRAIN),
        ExportFieldSpec("requested_days", "keyword_windows", "window catalog", "count", False, "0 for empty open periods", "catalog spec", _WINDOW_GRAIN),
        ExportFieldSpec("partial", "keyword_windows", "window engine", "bool", False, "observed < requested", "coverage flag", _WINDOW_GRAIN),
        ExportFieldSpec("views_sum", "keyword_windows", "daily.views sum", "count", True, "null if no non-null views", "_sum_int non-null subset", _WINDOW_GRAIN),
        ExportFieldSpec("clicks_sum", "keyword_windows", "daily.clicks sum", "count", True, "null if no non-null clicks", "_sum_int non-null subset", _WINDOW_GRAIN),
        ExportFieldSpec("add_to_cart_sum", "keyword_windows", "daily.add_to_cart sum", "count", True, "null if none", "_sum_int", _WINDOW_GRAIN),
        ExportFieldSpec("orders_sum", "keyword_windows", "daily.orders sum", "count", True, "null if none", "_sum_int", _WINDOW_GRAIN),
        ExportFieldSpec("spend_rub_sum", "keyword_windows", "daily.spend FACTUAL", "RUB", True, "null unless all days FACTUAL", "fail-closed partial", _WINDOW_GRAIN),
        ExportFieldSpec("spend_status", "keyword_windows", "window economics", "enum", False, "UNAVAILABLE default", "FACTUAL|PARTIAL|UNAVAILABLE", _WINDOW_GRAIN),
        ExportFieldSpec("ctr", "keyword_windows", "derived aligned", "ratio 0..1", True, "null if no paired clicks+views", "sum(clicks)/sum(views) aligned cohort", _WINDOW_GRAIN),
        ExportFieldSpec("conv_views_to_cart", "keyword_windows", "derived aligned", "ratio 0..1", True, "null if no paired rows", "cart/views aligned", _WINDOW_GRAIN),
        ExportFieldSpec("conv_cart_to_order", "keyword_windows", "derived aligned", "ratio 0..1", True, "null if no paired rows", "orders/cart aligned", _WINDOW_GRAIN),
        ExportFieldSpec("conv_views_to_order", "keyword_windows", "derived aligned", "ratio 0..1", True, "null if no paired rows", "orders/views aligned", _WINDOW_GRAIN),
        ExportFieldSpec("cpo_rub", "keyword_windows", "derived aligned", "RUB", True, "null unless FACTUAL aligned spend+orders", "spend/orders same-row FACTUAL", _WINDOW_GRAIN),
        ExportFieldSpec("cpm_mean", "keyword_windows", "derived aligned", "RUB", True, "null unless FACTUAL aligned spend+views", "spend/views*1000 aligned", _WINDOW_GRAIN),
        ExportFieldSpec("cpc_mean", "keyword_windows", "derived aligned", "RUB", True, "null unless FACTUAL aligned spend+clicks", "spend/clicks aligned", _WINDOW_GRAIN),
        ExportFieldSpec("cluster_avg_pos_mean", "keyword_windows", "derived ranking", "rank", True, "views-weighted or unweighted fallback", "position_mean metadata in window_coverage", _WINDOW_GRAIN),
        ExportFieldSpec("cluster_avg_pos_median", "keyword_windows", "derived ranking", "rank", True, "null when no positions", "median of observed positions", _WINDOW_GRAIN),
        ExportFieldSpec("cluster_avg_pos_start", "keyword_windows", "derived ranking", "rank", True, "null when none", "first chronological position", _WINDOW_GRAIN),
        ExportFieldSpec("cluster_avg_pos_end", "keyword_windows", "derived ranking", "rank", True, "null when none", "last chronological position", _WINDOW_GRAIN),
        ExportFieldSpec("cluster_avg_pos_delta", "keyword_windows", "derived ranking", "rank delta", True, "null when start/end missing", "end - start; negative=improvement", _WINDOW_GRAIN),
        ExportFieldSpec("cluster_avg_pos_best", "keyword_windows", "derived ranking", "rank", True, "null when none", "min position", _WINDOW_GRAIN),
        ExportFieldSpec("cluster_avg_pos_worst", "keyword_windows", "derived ranking", "rank", True, "null when none", "max position", _WINDOW_GRAIN),
        ExportFieldSpec("position_observed_days", "keyword_windows", "window engine", "count", False, "0 when none", "distinct dates with position", _WINDOW_GRAIN),
        ExportFieldSpec("position_missing_days", "keyword_windows", "window engine", "count", False, "requested - position_observed", "includes absent requested days", _WINDOW_GRAIN),
        ExportFieldSpec("window_coverage.partial", "keyword_windows", "window engine", "bool", False, "mirrors partial", "nested coverage", _WINDOW_GRAIN, nested="window_coverage"),
        ExportFieldSpec("window_coverage.observed_days", "keyword_windows", "window engine", "count", False, "required", "nested coverage", _WINDOW_GRAIN, nested="window_coverage"),
        ExportFieldSpec("window_coverage.missing_days", "keyword_windows", "window engine", "count", False, "required", "nested coverage", _WINDOW_GRAIN, nested="window_coverage"),
        ExportFieldSpec("window_coverage.position_observed_days", "keyword_windows", "window engine", "count", False, "required", "nested coverage", _WINDOW_GRAIN, nested="window_coverage"),
        ExportFieldSpec("window_coverage.position_missing_days", "keyword_windows", "window engine", "count", False, "required", "nested coverage", _WINDOW_GRAIN, nested="window_coverage"),
        ExportFieldSpec("window_coverage.position_mean_mode", "keyword_windows", "window engine", "text", False, "views_weighted|unweighted|none", "honest weighting metadata", _WINDOW_GRAIN, nested="window_coverage"),
    ),
    *_specs(
        ExportFieldSpec("schema_version", "keyword_current_state", "constant", "semver", False, "required", "SCHEMA_VERSION_KEYWORD", _CURRENT_GRAIN),
        ExportFieldSpec("shop_id", "keyword_current_state", "manifest", "int", False, "required", "manifest scope", _CURRENT_GRAIN),
        ExportFieldSpec("adv_setting_id", "keyword_current_state", "scope", "int", True, "null when unmapped", "PG id", _CURRENT_GRAIN),
        ExportFieldSpec("adv_id", "keyword_current_state", "daily latest", "int", False, "required", "physical adv_id", _CURRENT_GRAIN, pk=True),
        ExportFieldSpec("leg_role", "keyword_current_state", "scope", "enum", False, "required", "leg assignment", _CURRENT_GRAIN),
        ExportFieldSpec("nmid", "keyword_current_state", "daily latest", "int", False, "required", "product id", _CURRENT_GRAIN, pk=True),
        ExportFieldSpec("norm_query", "keyword_current_state", "daily latest", "text", False, "required", "query key", _CURRENT_GRAIN, pk=True),
        ExportFieldSpec("campaign_slot_role", "keyword_current_state", "current selector", "enum", False, "ACTIVE|REBOUND|AMBIGUOUS", "not mv_clusters authority", _CURRENT_GRAIN),
        ExportFieldSpec("observation_date", "keyword_current_state", "daily latest", "date", False, "required", "max date row", _CURRENT_GRAIN),
        ExportFieldSpec("observation_ts", "keyword_current_state", "daily latest", "datetime", True, "null when absent", "snapshot ts", _CURRENT_GRAIN),
        ExportFieldSpec("freshness_status", "keyword_current_state", "freshness calc", "text", False, "UNKNOWN default", "days since observation", _CURRENT_GRAIN),
        ExportFieldSpec("views", "keyword_current_state", "daily latest", "count", True, "null not zero", "latest row copy", _CURRENT_GRAIN),
        ExportFieldSpec("clicks", "keyword_current_state", "daily latest", "count", True, "null not zero", "latest row copy", _CURRENT_GRAIN),
        ExportFieldSpec("orders", "keyword_current_state", "daily latest", "count", True, "null not zero", "latest row copy", _CURRENT_GRAIN),
        ExportFieldSpec("spend_rub", "keyword_current_state", "daily latest", "RUB", True, "null when unavailable", "latest row copy", _CURRENT_GRAIN),
        ExportFieldSpec("cpm", "keyword_current_state", "daily latest", "RUB", True, "null + coverage", "observed cluster cpm", _CURRENT_GRAIN),
        ExportFieldSpec("cpc", "keyword_current_state", "daily latest", "RUB", True, "null + coverage", "observed cluster cpc", _CURRENT_GRAIN),
        ExportFieldSpec("ctr", "keyword_current_state", "daily latest", "ratio", True, "null when undefined", "derived on daily", _CURRENT_GRAIN),
        ExportFieldSpec("cluster_avg_pos", "keyword_current_state", "daily latest", "rank", True, "null not synthetic", "latest cluster position", _CURRENT_GRAIN),
        ExportFieldSpec("observed_cpm", "keyword_current_state", "cluster snapshot", "RUB", True, "null when absent", "distinct from configured_max_cpm", _CURRENT_GRAIN),
        ExportFieldSpec("configured_max_cpm", "keyword_current_state", "PG AdvSetting.max_cpm", "RUB", True, "null when bidder inactive", "policy CAP not applied bid", _CURRENT_GRAIN),
        ExportFieldSpec("current_bid_evidence", "keyword_current_state", "persisted applied bid", "RUB", True, "UNAVAILABLE — cap≠bid", "no proven source wired", _CURRENT_GRAIN),
        ExportFieldSpec("current_bid_evidence_status", "keyword_current_state", "export policy", "enum", False, "UNAVAILABLE default", "BidEvidenceStatus", _CURRENT_GRAIN),
        ExportFieldSpec("decision_cpm_curr", "keyword_current_state", "bid_decision_log latest", "RUB", True, "null when unsupported", "join adv_id,nmid,norm_query", _CURRENT_GRAIN),
        ExportFieldSpec("bidder_active", "keyword_current_state", "PG AdvSetting", "bool", True, "null when unmapped", "campaign policy", _CURRENT_GRAIN),
        ExportFieldSpec("campaign_active_status", "keyword_current_state", "PG AdvSetting", "text", True, "null when unmapped", "campaign policy", _CURRENT_GRAIN),
        ExportFieldSpec("strategy_status", "keyword_current_state", "PG AdvSetting", "text", True, "null when unmapped", "campaign policy", _CURRENT_GRAIN),
        ExportFieldSpec("min_target_position", "keyword_current_state", "PG AdvSetting", "rank", True, "null when unmapped", "campaign policy", _CURRENT_GRAIN),
        ExportFieldSpec("target_position_mode", "keyword_current_state", "PG AdvSetting", "text", True, "null when unmapped", "campaign policy", _CURRENT_GRAIN),
        ExportFieldSpec("keyword_target_place", "keyword_current_state", "PG KeywordSetting", "rank", True, "null per query when absent", "not campaign max", _CURRENT_GRAIN),
        ExportFieldSpec("keyword_strategy_mode", "keyword_current_state", "PG KeywordSetting", "text", True, "null per query when absent", "query policy", _CURRENT_GRAIN),
        ExportFieldSpec("last_observed_historical", "keyword_current_state", "optional stream", "object", True, "null default", "REBOUND historical metadata", _CURRENT_GRAIN),
        ExportFieldSpec("product_last_state", "keyword_current_state", "mv_clusters_last_state", "object", True, "null default", "product stream not campaign authority", _CURRENT_GRAIN),
        ExportFieldSpec("row_coverage.observed", "keyword_current_state", "coverage assembler", "string[]", False, "empty when none", "nested", _CURRENT_GRAIN, nested=_COVERAGE_NESTED),
        ExportFieldSpec("row_coverage.missing", "keyword_current_state", "coverage assembler", "string[]", False, "empty when none", "nested", _CURRENT_GRAIN, nested=_COVERAGE_NESTED),
        ExportFieldSpec("row_coverage.reason_codes", "keyword_current_state", "coverage assembler", "string[]", False, "empty when none", "nested", _CURRENT_GRAIN, nested=_COVERAGE_NESTED),
    ),
    *_specs(
        ExportFieldSpec("schema_version", "keyword_changes", "constant", "semver", False, "required", "SCHEMA_VERSION_KEYWORD", _CHANGE_GRAIN),
        ExportFieldSpec("shop_id", "keyword_changes", "window identity", "int", False, "required", "carry from window", _CHANGE_GRAIN),
        ExportFieldSpec("adv_setting_id", "keyword_changes", "window identity", "int", True, "null when unmapped", "carry", _CHANGE_GRAIN),
        ExportFieldSpec("adv_id", "keyword_changes", "window identity", "int", False, "required", "physical adv_id", _CHANGE_GRAIN),
        ExportFieldSpec("leg_role", "keyword_changes", "window identity", "enum", False, "required", "leg", _CHANGE_GRAIN),
        ExportFieldSpec("nmid", "keyword_changes", "window identity", "int", False, "required", "product", _CHANGE_GRAIN),
        ExportFieldSpec("norm_query", "keyword_changes", "window identity", "text", False, "required", "query", _CHANGE_GRAIN),
        ExportFieldSpec("change_id", "keyword_changes", "comparator catalog", "text", False, "required PK", "7d_vs_prev_7d etc", _CHANGE_GRAIN, pk=True),
        ExportFieldSpec("current_window_id", "keyword_changes", "window map", "text", False, "required", "current side", _CHANGE_GRAIN),
        ExportFieldSpec("previous_window_id", "keyword_changes", "window map", "text", False, "required", "previous side", _CHANGE_GRAIN),
        ExportFieldSpec("current_start", "keyword_changes", "window bounds", "date", False, "required", "UTC inclusive", _CHANGE_GRAIN),
        ExportFieldSpec("current_end", "keyword_changes", "window bounds", "date", False, "required", "UTC inclusive", _CHANGE_GRAIN),
        ExportFieldSpec("previous_start", "keyword_changes", "window bounds", "date", False, "required", "comparable prev", _CHANGE_GRAIN),
        ExportFieldSpec("previous_end", "keyword_changes", "window bounds", "date", False, "required", "comparable prev", _CHANGE_GRAIN),
        ExportFieldSpec("metric_name", "keyword_changes", "CHANGE_METRICS catalog", "text", False, "required PK", "facts-only metric", _CHANGE_GRAIN, pk=True),
        ExportFieldSpec("current_value", "keyword_changes", "window aggregate", "float", True, "null when missing", "no AI labels", _CHANGE_GRAIN),
        ExportFieldSpec("previous_value", "keyword_changes", "window aggregate", "float", True, "null when missing", "no AI labels", _CHANGE_GRAIN),
        ExportFieldSpec("absolute_delta", "keyword_changes", "derived", "float", True, "null when either side missing", "current - previous", _CHANGE_GRAIN),
        ExportFieldSpec("relative_delta", "keyword_changes", "derived", "ratio", True, "null when previous=0/missing", "absolute/previous", _CHANGE_GRAIN),
        ExportFieldSpec("pp_delta", "keyword_changes", "derived", "ratio points", True, "null for non-rate metrics", "rate delta * 100", _CHANGE_GRAIN),
        ExportFieldSpec("ranking_delta", "keyword_changes", "derived", "rank delta", True, "null for non-ranking", "position metric delta", _CHANGE_GRAIN),
        ExportFieldSpec("spend_status_current", "keyword_changes", "window economics", "enum", False, "carry", "current window spend_status", _CHANGE_GRAIN),
        ExportFieldSpec("spend_status_previous", "keyword_changes", "window economics", "enum", False, "carry", "previous window spend_status", _CHANGE_GRAIN),
        ExportFieldSpec("coverage_current.observed_days", "keyword_changes", "window coverage", "count", False, "nested", "partial metadata", _CHANGE_GRAIN, nested="coverage_current"),
        ExportFieldSpec("coverage_current.partial", "keyword_changes", "window coverage", "bool", False, "nested", "partial metadata", _CHANGE_GRAIN, nested="coverage_current"),
        ExportFieldSpec("coverage_previous.observed_days", "keyword_changes", "window coverage", "count", False, "nested", "partial metadata", _CHANGE_GRAIN, nested="coverage_previous"),
        ExportFieldSpec("coverage_previous.partial", "keyword_changes", "window coverage", "bool", False, "nested", "partial metadata", _CHANGE_GRAIN, nested="coverage_previous"),
        ExportFieldSpec("row_coverage.observed", "keyword_changes", "coverage assembler", "string[]", False, "nested", "per-row coverage", _CHANGE_GRAIN, nested=_COVERAGE_NESTED),
        ExportFieldSpec("row_coverage.missing", "keyword_changes", "coverage assembler", "string[]", False, "nested", "per-row coverage", _CHANGE_GRAIN, nested=_COVERAGE_NESTED),
        ExportFieldSpec("row_coverage.reason_codes", "keyword_changes", "coverage assembler", "string[]", False, "nested", "per-row coverage", _CHANGE_GRAIN, nested=_COVERAGE_NESTED),
    ),
    *_specs(
        ExportFieldSpec("schema_version", "keyword_positions", "constant", "semver", False, "required", "SCHEMA_VERSION_KEYWORD", _POSITION_GRAIN),
        ExportFieldSpec("shop_id", "keyword_positions", "manifest", "int", False, "required", "manifest scope", _POSITION_GRAIN),
        ExportFieldSpec("adv_id", "keyword_positions", "optional join", "int", True, "null when unproven", "not fabricated", _POSITION_GRAIN),
        ExportFieldSpec("nmid", "keyword_positions", "keyword_position_from_api.nmid", "int", False, "required", "product id", _POSITION_GRAIN, pk=True),
        ExportFieldSpec("norm_query", "keyword_positions", "daily match only", "text", True, "null when NORMALIZATION_UNPROVEN", "never copy source_query_text", _POSITION_GRAIN),
        ExportFieldSpec("norm_query_provenance", "keyword_positions", "export policy", "enum", False, "PROVEN_EQUAL|NORMALIZATION_UNPROVEN", "API grain separate", _POSITION_GRAIN),
        ExportFieldSpec("source_query_text", "keyword_positions", "keyword_position_from_api.text", "text", False, "required PK", "API own query grain", _POSITION_GRAIN, pk=True),
        ExportFieldSpec("date", "keyword_positions", "keyword_position_from_api.date", "date", False, "required PK", "date <= cutoff", _POSITION_GRAIN, pk=True),
        ExportFieldSpec("position_type", "keyword_positions", "export policy", "enum", False, "required PK", "WB_KEYWORD_POSITION_API", _POSITION_GRAIN, pk=True),
        ExportFieldSpec("source_version", "keyword_positions", "keyword_position_from_api.version", "int ms", True, "null when absent", "version <= cutoff_instant_ms", _POSITION_GRAIN),
        ExportFieldSpec("avr_position", "keyword_positions", "keyword_position_from_api.avr_position", "rank", True, "null not coerced", "row-coherent snapshot", _POSITION_GRAIN),
        ExportFieldSpec("total_views", "keyword_positions", "keyword_position_from_api.total_views", "count", True, "null when absent", "API column", _POSITION_GRAIN),
        ExportFieldSpec("orders", "keyword_positions", "keyword_position_from_api.orders", "count", True, "null when absent", "API column", _POSITION_GRAIN),
        ExportFieldSpec("snapshot_status", "keyword_positions", "snapshot probe", "enum", False, "OK|AMBIGUOUS", "tuple_variants_at_max_version", _POSITION_GRAIN),
        ExportFieldSpec("source", "keyword_positions", "constant", "text", False, "keyword_position_from_api", "stream tag", _POSITION_GRAIN),
        ExportFieldSpec("row_coverage.observed", "keyword_positions", "coverage assembler", "string[]", False, "nested", "per-row", _POSITION_GRAIN, nested=_COVERAGE_NESTED),
        ExportFieldSpec("row_coverage.missing", "keyword_positions", "coverage assembler", "string[]", False, "nested", "per-row", _POSITION_GRAIN, nested=_COVERAGE_NESTED),
        ExportFieldSpec("row_coverage.reason_codes", "keyword_positions", "coverage assembler", "string[]", False, "nested", "per-row", _POSITION_GRAIN, nested=_COVERAGE_NESTED),
    ),
    *_specs(
        ExportFieldSpec("schema_version", "keyword_position_windows", "constant", "semver", False, "required", "SCHEMA_VERSION_KEYWORD", _POS_WINDOW_GRAIN),
        ExportFieldSpec("shop_id", "keyword_position_windows", "manifest", "int", False, "required", "manifest scope", _POS_WINDOW_GRAIN),
        ExportFieldSpec("adv_id", "keyword_position_windows", "optional", "int", True, "null when unproven", "not fabricated", _POS_WINDOW_GRAIN),
        ExportFieldSpec("nmid", "keyword_position_windows", "position identity", "int", False, "required", "product", _POS_WINDOW_GRAIN, pk=True),
        ExportFieldSpec("norm_query", "keyword_position_windows", "position row", "text", True, "null when unproven", "provenance tagged", _POS_WINDOW_GRAIN),
        ExportFieldSpec("norm_query_provenance", "keyword_position_windows", "position row", "enum", False, "required", "provenance enum", _POS_WINDOW_GRAIN),
        ExportFieldSpec("source_query_text", "keyword_position_windows", "position identity", "text", False, "required PK", "API query grain", _POS_WINDOW_GRAIN, pk=True),
        ExportFieldSpec("position_type", "keyword_position_windows", "position identity", "enum", False, "required PK", "separate streams", _POS_WINDOW_GRAIN, pk=True),
        ExportFieldSpec("window_id", "keyword_position_windows", "window catalog", "text", False, "required PK", "same catalog as daily windows", _POS_WINDOW_GRAIN, pk=True),
        ExportFieldSpec("window_start", "keyword_position_windows", "window engine", "date", False, "required", "UTC inclusive", _POS_WINDOW_GRAIN),
        ExportFieldSpec("window_end", "keyword_position_windows", "window engine", "date", False, "required", "UTC inclusive", _POS_WINDOW_GRAIN),
        ExportFieldSpec("observed_days", "keyword_position_windows", "position engine", "count", False, "0 when empty", "distinct OK snapshot dates", _POS_WINDOW_GRAIN),
        ExportFieldSpec("missing_days", "keyword_position_windows", "position engine", "count", False, "requested - observed", "requested calendar gap", _POS_WINDOW_GRAIN),
        ExportFieldSpec("requested_days", "keyword_position_windows", "window catalog", "count", False, "0 when empty open", "catalog spec", _POS_WINDOW_GRAIN),
        ExportFieldSpec("partial", "keyword_position_windows", "position engine", "bool", False, "observed < requested", "coverage flag", _POS_WINDOW_GRAIN),
        ExportFieldSpec("position_start", "keyword_position_windows", "derived ranking", "rank", True, "null when none", "first position in window", _POS_WINDOW_GRAIN),
        ExportFieldSpec("position_end", "keyword_position_windows", "derived ranking", "rank", True, "null when none", "last position in window", _POS_WINDOW_GRAIN),
        ExportFieldSpec("position_delta", "keyword_position_windows", "derived ranking", "rank delta", True, "null when undefined", "end - start", _POS_WINDOW_GRAIN),
        ExportFieldSpec("position_best", "keyword_position_windows", "derived ranking", "rank", True, "null when none", "min position", _POS_WINDOW_GRAIN),
        ExportFieldSpec("position_worst", "keyword_position_windows", "derived ranking", "rank", True, "null when none", "max position", _POS_WINDOW_GRAIN),
        ExportFieldSpec("position_mean", "keyword_position_windows", "derived ranking", "rank", True, "null when none", "arithmetic mean", _POS_WINDOW_GRAIN),
        ExportFieldSpec("position_median", "keyword_position_windows", "derived ranking", "rank", True, "null when none", "median", _POS_WINDOW_GRAIN),
        ExportFieldSpec("window_coverage.partial", "keyword_position_windows", "position engine", "bool", False, "nested", "coverage block", _POS_WINDOW_GRAIN, nested="window_coverage"),
        ExportFieldSpec("window_coverage.observed_days", "keyword_position_windows", "position engine", "count", False, "nested", "coverage block", _POS_WINDOW_GRAIN, nested="window_coverage"),
        ExportFieldSpec("window_coverage.missing_days", "keyword_position_windows", "position engine", "count", False, "nested", "coverage block", _POS_WINDOW_GRAIN, nested="window_coverage"),
    ),
    *_specs(
        ExportFieldSpec("schema_version", "keyword_position_current", "constant", "semver", False, "required", "SCHEMA_VERSION_KEYWORD", _POS_CURRENT_GRAIN),
        ExportFieldSpec("shop_id", "keyword_position_current", "manifest", "int", False, "required", "manifest scope", _POS_CURRENT_GRAIN),
        ExportFieldSpec("adv_id", "keyword_position_current", "optional", "int", True, "null when unproven", "not fabricated", _POS_CURRENT_GRAIN),
        ExportFieldSpec("nmid", "keyword_position_current", "position latest", "int", False, "required", "product", _POS_CURRENT_GRAIN, pk=True),
        ExportFieldSpec("norm_query", "keyword_position_current", "position latest", "text", True, "null when unproven", "provenance tagged", _POS_CURRENT_GRAIN),
        ExportFieldSpec("norm_query_provenance", "keyword_position_current", "position latest", "enum", False, "required", "provenance enum", _POS_CURRENT_GRAIN),
        ExportFieldSpec("source_query_text", "keyword_position_current", "position latest", "text", False, "required PK", "API query grain", _POS_CURRENT_GRAIN, pk=True),
        ExportFieldSpec("position_type", "keyword_position_current", "position latest", "enum", False, "required PK", "separate streams", _POS_CURRENT_GRAIN, pk=True),
        ExportFieldSpec("observation_date", "keyword_position_current", "position latest", "date", False, "required", "max date; null position kept", _POS_CURRENT_GRAIN),
        ExportFieldSpec("source_version", "keyword_position_current", "position latest", "int ms", True, "null when absent", "version tie-break", _POS_CURRENT_GRAIN),
        ExportFieldSpec("avr_position", "keyword_position_current", "position latest", "rank", True, "null when ambiguous/latest null", "never backfill stale", _POS_CURRENT_GRAIN),
        ExportFieldSpec("snapshot_status", "keyword_position_current", "position latest", "enum", False, "OK|AMBIGUOUS", "conflict nulling", _POS_CURRENT_GRAIN),
        ExportFieldSpec("source", "keyword_position_current", "constant", "text", False, "keyword_position_from_api", "stream tag", _POS_CURRENT_GRAIN),
        ExportFieldSpec("row_coverage.observed", "keyword_position_current", "coverage assembler", "string[]", False, "nested", "per-row", _POS_CURRENT_GRAIN, nested=_COVERAGE_NESTED),
        ExportFieldSpec("row_coverage.missing", "keyword_position_current", "coverage assembler", "string[]", False, "nested", "per-row", _POS_CURRENT_GRAIN, nested=_COVERAGE_NESTED),
        ExportFieldSpec("row_coverage.reason_codes", "keyword_position_current", "coverage assembler", "string[]", False, "nested", "per-row", _POS_CURRENT_GRAIN, nested=_COVERAGE_NESTED),
    ),
    *_specs(
        ExportFieldSpec("schema_version", "keyword_decisions", "constant", "semver", False, "required", "SCHEMA_VERSION_KEYWORD", _DECISION_GRAIN),
        ExportFieldSpec("shop_id", "keyword_decisions", "manifest", "int", False, "required", "manifest scope", _DECISION_GRAIN),
        ExportFieldSpec("adv_id", "keyword_decisions", "bid_decision_log.adv_id", "int", False, "required PK", "physical adv_id", _DECISION_GRAIN, pk=True),
        ExportFieldSpec("nmid", "keyword_decisions", "bid_decision_log.nmid", "int", False, "required PK", "product id", _DECISION_GRAIN, pk=True),
        ExportFieldSpec("norm_query", "keyword_decisions", "bid_decision_log.norm_query", "text", False, "required PK", "query key", _DECISION_GRAIN, pk=True),
        ExportFieldSpec("event_class", "keyword_decisions", "source-derived", "enum", False, "DECISION default", "no native event_class column", _DECISION_GRAIN),
        ExportFieldSpec("source_kind", "keyword_decisions", "export policy", "enum", False, "RETROSPECTIVE_COMPUTED_CONTEXT", "analytics not verified apply", _DECISION_GRAIN),
        ExportFieldSpec("cpm_curr", "keyword_decisions", "bid_decision_log.cpm_curr", "RUB", True, "null on conflict", "row-coherent latest", _DECISION_GRAIN),
        ExportFieldSpec("final_bid", "keyword_decisions", "bid_decision_log.final_bid", "RUB", True, "ANALYTICS_COMPUTED_NOT_VERIFIED_APPLIED", "retrospective computed", _DECISION_GRAIN),
        ExportFieldSpec("final_bid_semantics", "keyword_decisions", "export policy", "enum", False, "ANALYTICS_COMPUTED_NOT_VERIFIED_APPLIED", "not verified applied bid", _DECISION_GRAIN),
        ExportFieldSpec("decision_time", "keyword_decisions", "bid_decision_log.decision_time", "datetime", True, "null on conflict", "<= package_cutoff_instant", _DECISION_GRAIN, pk=True),
        ExportFieldSpec("stats_max_timestamp", "keyword_decisions", "bid_decision_log.stats_max_timestamp", "datetime", True, "null when absent", "scoped cutoff filter", _DECISION_GRAIN),
        ExportFieldSpec("decision_source", "keyword_decisions", "bid_decision_log.decision_source", "text", True, "null when absent", "optional column", _DECISION_GRAIN),
        ExportFieldSpec("version", "keyword_decisions", "bid_decision_log.version", "int", True, "null on conflict", "row-coherent max version", _DECISION_GRAIN),
        ExportFieldSpec("snapshot_status", "keyword_decisions", "snapshot probe", "enum", False, "OK|AMBIGUOUS", "tuple_variants_at_max_version", _DECISION_GRAIN),
        ExportFieldSpec("row_coverage.observed", "keyword_decisions", "coverage assembler", "string[]", False, "nested", "per-row", _DECISION_GRAIN, nested=_COVERAGE_NESTED),
        ExportFieldSpec("row_coverage.missing", "keyword_decisions", "coverage assembler", "string[]", False, "nested", "per-row", _DECISION_GRAIN, nested=_COVERAGE_NESTED),
        ExportFieldSpec("row_coverage.reason_codes", "keyword_decisions", "coverage assembler", "string[]", False, "nested", "per-row", _DECISION_GRAIN, nested=_COVERAGE_NESTED),
    ),
)

_DATASET_MODELS: dict[str, type[BaseModel]] = {
    "keyword_daily": KeywordDailyRowV1,
    "keyword_windows": KeywordWindowRowV1,
    "keyword_current_state": KeywordCurrentStateRowV1,
    "keyword_changes": KeywordChangeRowV1,
    "keyword_positions": KeywordPositionRowV1,
    "keyword_position_windows": KeywordPositionWindowRowV1,
    "keyword_position_current": KeywordPositionLatestRowV1,
    "keyword_decisions": KeywordDecisionRowV1,
}


def _flatten_model_fields(model: type[BaseModel], prefix: str = "") -> set[str]:
    names: set[str] = set()
    for name, field_info in model.model_fields.items():
        qualified = f"{prefix}.{name}" if prefix else name
        annotation = field_info.annotation
        if annotation is RowCoverageV1 or (
            isinstance(annotation, type) and issubclass(annotation, RowCoverageV1)
        ):
            names.add(f"{qualified}.observed")
            names.add(f"{qualified}.missing")
            names.add(f"{qualified}.reason_codes")
            continue
        if name == "window_coverage" and model is KeywordWindowRowV1:
            names.add(f"{qualified}.partial")
            names.add(f"{qualified}.observed_days")
            names.add(f"{qualified}.missing_days")
            names.add(f"{qualified}.position_observed_days")
            names.add(f"{qualified}.position_missing_days")
            names.add(f"{qualified}.position_mean_mode")
            continue
        if name == "window_coverage" and model is KeywordPositionWindowRowV1:
            names.add(f"{qualified}.partial")
            names.add(f"{qualified}.observed_days")
            names.add(f"{qualified}.missing_days")
            continue
        if name in {"coverage_current", "coverage_previous"}:
            names.add(f"{qualified}.partial")
            names.add(f"{qualified}.observed_days")
            continue
        names.add(qualified)
    return names


def expected_export_fields() -> dict[str, set[str]]:
    """Expected exported field names per dataset derived from pydantic models."""
    return {
        dataset: _flatten_model_fields(model)
        for dataset, model in _DATASET_MODELS.items()
    }


def build_export_field_matrix() -> list[dict[str, Any]]:
    """Full per-field matrix for DATA_MAP.json."""
    return [spec.to_matrix_row() for spec in EXPORT_FIELD_SPECS]


def registry_fields_by_dataset() -> dict[str, set[str]]:
    """Registry field names keyed by dataset id."""
    result: dict[str, set[str]] = {}
    for spec in EXPORT_FIELD_SPECS:
        result.setdefault(spec.dataset, set()).add(spec.field)
    return result


def validate_registry_completeness() -> list[str]:
    """Return gap messages when registry misses model fields or metadata keys."""
    gaps: list[str] = []
    expected = expected_export_fields()
    registry = registry_fields_by_dataset()
    for dataset, model_fields in expected.items():
        reg_fields = registry.get(dataset, set())
        missing = model_fields - reg_fields
        extra = reg_fields - model_fields
        if missing:
            gaps.append(f"{dataset}: registry missing {sorted(missing)}")
        if extra:
            gaps.append(f"{dataset}: registry extra {sorted(extra)}")
    for spec in EXPORT_FIELD_SPECS:
        row = spec.to_matrix_row()
        missing_keys = _REQUIRED_MATRIX_KEYS - set(row)
        if missing_keys:
            gaps.append(f"{spec.dataset}.{spec.field}: missing keys {sorted(missing_keys)}")
        if not row.get("source") or not row.get("formula"):
            gaps.append(f"{spec.dataset}.{spec.field}: empty source/formula")
    return gaps
