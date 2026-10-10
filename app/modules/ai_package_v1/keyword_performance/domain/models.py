"""Pydantic domain rows для keyword performance datasets."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.ai_package_v1.domain.shop_id import AuthoritativeShopId
from app.modules.ai_package_v1.keyword_performance.domain.enums import (
    BidEvidenceStatus,
    CampaignSlotRole,
    ComparatorKind,
    DecisionEventClass,
    DecisionSourceKind,
    FinalBidSemantics,
    KeywordLegRole,
    NormQueryProvenance,
    PositionType,
    QuerySpendStatus,
    RawQueryStatus,
    SCHEMA_VERSION_KEYWORD,
    SnapshotStatus,
    WindowSpendStatus,
)

_FROZEN = ConfigDict(frozen=True)


class RowCoverageV1(BaseModel):
    """Per-field observed/missing coverage on a row."""

    model_config = _FROZEN

    observed: tuple[str, ...] = Field(default_factory=tuple)
    missing: tuple[str, ...] = Field(default_factory=tuple)
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)


class KeywordDailyRowV1(BaseModel):
    """Canonical daily query fact at strict grain."""

    model_config = _FROZEN

    schema_version: str = SCHEMA_VERSION_KEYWORD
    shop_id: AuthoritativeShopId
    adv_setting_id: int | None = None
    adv_id: int
    leg_role: KeywordLegRole
    nmid: int
    norm_query: str
    raw_query: str | None = None
    raw_query_status: RawQueryStatus = RawQueryStatus.RAW_QUERY_UNAVAILABLE
    date: str
    observation_ts: str | None = None
    views: int | None = None
    clicks: int | None = None
    add_to_cart: int | None = None
    orders: int | None = None
    spend_rub: float | None = None
    query_spend_status: QuerySpendStatus = QuerySpendStatus.UNAVAILABLE
    cpm: float | None = None
    cpc: float | None = None
    ctr: float | None = None
    conv_views_to_cart: float | None = None
    conv_cart_to_order: float | None = None
    conv_views_to_order: float | None = None
    cpo_rub: float | None = None
    cluster_avg_pos: float | None = None
    snapshot_status: SnapshotStatus = SnapshotStatus.OK
    source: str = "clusters_adv_stats"
    row_coverage: RowCoverageV1 = Field(default_factory=RowCoverageV1)


class KeywordPositionRowV1(BaseModel):
    """Separate position observation stream."""

    model_config = _FROZEN

    schema_version: str = SCHEMA_VERSION_KEYWORD
    shop_id: AuthoritativeShopId
    adv_id: int | None = None
    nmid: int
    norm_query: str | None = None
    norm_query_provenance: NormQueryProvenance = (
        NormQueryProvenance.NORMALIZATION_UNPROVEN
    )
    source_query_text: str
    date: str
    position_type: PositionType
    source_version: int | None = None
    avr_position: float | None = None
    total_views: int | None = None
    orders: int | None = None
    snapshot_status: SnapshotStatus = SnapshotStatus.OK
    source: str
    row_coverage: RowCoverageV1 = Field(default_factory=RowCoverageV1)


class KeywordPositionLatestRowV1(BaseModel):
    """Latest compact position per (shop, nmid, source_query_text, position_type)."""

    model_config = _FROZEN

    schema_version: str = SCHEMA_VERSION_KEYWORD
    shop_id: AuthoritativeShopId
    adv_id: int | None = None
    nmid: int
    norm_query: str | None = None
    norm_query_provenance: NormQueryProvenance = (
        NormQueryProvenance.NORMALIZATION_UNPROVEN
    )
    source_query_text: str
    position_type: PositionType
    observation_date: str
    source_version: int | None = None
    avr_position: float | None = None
    snapshot_status: SnapshotStatus = SnapshotStatus.OK
    source: str
    row_coverage: RowCoverageV1 = Field(default_factory=RowCoverageV1)


class KeywordPositionWindowRowV1(BaseModel):
    """Deterministic position window at API source grain."""

    model_config = _FROZEN

    schema_version: str = SCHEMA_VERSION_KEYWORD
    shop_id: AuthoritativeShopId
    adv_id: int | None = None
    nmid: int
    norm_query: str | None = None
    norm_query_provenance: NormQueryProvenance = (
        NormQueryProvenance.NORMALIZATION_UNPROVEN
    )
    source_query_text: str
    position_type: PositionType
    window_id: str
    window_start: str
    window_end: str
    observed_days: int = 0
    missing_days: int = 0
    requested_days: int = 0
    partial: bool = False
    position_start: float | None = None
    position_end: float | None = None
    position_delta: float | None = None
    position_best: float | None = None
    position_worst: float | None = None
    position_mean: float | None = None
    position_median: float | None = None
    window_coverage: dict[str, Any] = Field(default_factory=dict)


class KeywordDecisionRowV1(BaseModel):
    """Bid decision timeline row — source-derived DECISION class."""

    model_config = _FROZEN

    schema_version: str = SCHEMA_VERSION_KEYWORD
    shop_id: AuthoritativeShopId
    adv_id: int
    nmid: int
    norm_query: str
    event_class: DecisionEventClass = DecisionEventClass.DECISION
    source_kind: DecisionSourceKind = DecisionSourceKind.RETROSPECTIVE_COMPUTED_CONTEXT
    cpm_curr: float | None = None
    final_bid: float | None = None
    final_bid_semantics: FinalBidSemantics = (
        FinalBidSemantics.ANALYTICS_COMPUTED_NOT_VERIFIED_APPLIED
    )
    decision_time: str | None = None
    stats_max_timestamp: str | None = None
    decision_source: str | None = None
    version: int | None = None
    snapshot_status: SnapshotStatus = SnapshotStatus.OK
    row_coverage: RowCoverageV1 = Field(default_factory=RowCoverageV1)


class KeywordWindowRowV1(BaseModel):
    """Ready analytical window aggregate."""

    model_config = _FROZEN

    schema_version: str = SCHEMA_VERSION_KEYWORD
    shop_id: AuthoritativeShopId
    adv_setting_id: int | None = None
    adv_id: int
    leg_role: KeywordLegRole
    nmid: int
    norm_query: str
    window_id: str
    window_start: str
    window_end: str
    comparator_kind: ComparatorKind = ComparatorKind.NONE
    observed_days: int = 0
    missing_days: int = 0
    requested_days: int = 0
    partial: bool = False
    views_sum: int | None = None
    clicks_sum: int | None = None
    add_to_cart_sum: int | None = None
    orders_sum: int | None = None
    spend_rub_sum: float | None = None
    spend_status: WindowSpendStatus = WindowSpendStatus.UNAVAILABLE
    ctr: float | None = None
    conv_views_to_cart: float | None = None
    conv_cart_to_order: float | None = None
    conv_views_to_order: float | None = None
    cpo_rub: float | None = None
    cpm_mean: float | None = None
    cpc_mean: float | None = None
    cluster_avg_pos_mean: float | None = None
    cluster_avg_pos_median: float | None = None
    cluster_avg_pos_start: float | None = None
    cluster_avg_pos_end: float | None = None
    cluster_avg_pos_delta: float | None = None
    cluster_avg_pos_best: float | None = None
    cluster_avg_pos_worst: float | None = None
    position_observed_days: int = 0
    position_missing_days: int = 0
    window_coverage: dict[str, Any] = Field(default_factory=dict)


class KeywordCurrentStateRowV1(BaseModel):
    """Latest observation per campaign identity."""

    model_config = _FROZEN

    schema_version: str = SCHEMA_VERSION_KEYWORD
    shop_id: AuthoritativeShopId
    adv_setting_id: int | None = None
    adv_id: int
    leg_role: KeywordLegRole
    nmid: int
    norm_query: str
    campaign_slot_role: CampaignSlotRole
    observation_date: str
    observation_ts: str | None = None
    freshness_status: str = "UNKNOWN"
    views: int | None = None
    clicks: int | None = None
    orders: int | None = None
    spend_rub: float | None = None
    cpm: float | None = None
    cpc: float | None = None
    ctr: float | None = None
    cluster_avg_pos: float | None = None
    observed_cpm: float | None = None
    configured_max_cpm: float | None = None
    current_bid_evidence: float | None = None
    current_bid_evidence_status: BidEvidenceStatus = BidEvidenceStatus.UNAVAILABLE
    decision_cpm_curr: float | None = None
    bidder_active: bool | None = None
    campaign_active_status: str | None = None
    strategy_status: str | None = None
    min_target_position: int | None = None
    target_position_mode: str | None = None
    keyword_target_place: int | None = None
    keyword_strategy_mode: str | None = None
    last_observed_historical: dict[str, Any] | None = None
    product_last_state: dict[str, Any] | None = None
    row_coverage: RowCoverageV1 = Field(default_factory=RowCoverageV1)


class KeywordChangeRowV1(BaseModel):
    """Facts-only comparison between windows."""

    model_config = _FROZEN

    schema_version: str = SCHEMA_VERSION_KEYWORD
    shop_id: AuthoritativeShopId
    adv_setting_id: int | None = None
    adv_id: int
    leg_role: KeywordLegRole
    nmid: int
    norm_query: str
    change_id: str
    current_window_id: str
    previous_window_id: str
    current_start: str
    current_end: str
    previous_start: str
    previous_end: str
    metric_name: str
    current_value: float | None = None
    previous_value: float | None = None
    absolute_delta: float | None = None
    relative_delta: float | None = None
    pp_delta: float | None = None
    ranking_delta: float | None = None
    spend_status_current: WindowSpendStatus = WindowSpendStatus.UNAVAILABLE
    spend_status_previous: WindowSpendStatus = WindowSpendStatus.UNAVAILABLE
    coverage_current: dict[str, Any] = Field(default_factory=dict)
    coverage_previous: dict[str, Any] = Field(default_factory=dict)
    row_coverage: RowCoverageV1 = Field(default_factory=RowCoverageV1)
