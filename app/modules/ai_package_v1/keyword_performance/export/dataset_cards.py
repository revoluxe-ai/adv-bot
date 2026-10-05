"""Manifest dataset cards for keyword performance family."""

from __future__ import annotations

from app.modules.ai_package_v1.domain.dataset_card import DatasetCard, Provenance
from app.modules.ai_package_v1.domain.enums import (
    CollectionOutcome,
    Coverage,
    DatasetId,
    FreshnessStatus,
    PrimarySource,
    ReasonCode,
)
from app.modules.ai_package_v1.domain.export_period import ExportPeriod

KEYWORD_DAILY_LOGICAL = "keyword_performance/keyword_daily.jsonl"
KEYWORD_WINDOWS_LOGICAL = "keyword_performance/keyword_windows.jsonl"
KEYWORD_CURRENT_LOGICAL = "keyword_performance/keyword_current_state.jsonl"
KEYWORD_CHANGES_LOGICAL = "keyword_performance/keyword_changes.jsonl"
KEYWORD_POSITIONS_LOGICAL = "keyword_performance/keyword_positions.jsonl"
KEYWORD_POSITION_WINDOWS_LOGICAL = "keyword_performance/keyword_position_windows.jsonl"
KEYWORD_POSITION_CURRENT_LOGICAL = "keyword_performance/keyword_position_current.jsonl"
KEYWORD_DECISIONS_LOGICAL = "keyword_performance/keyword_decisions.jsonl"
DATA_MAP_LOGICAL = "DATA_MAP.json"
COVERAGE_LOGICAL = "coverage.json"


def _keyword_card(
    dataset_id: DatasetId,
    *,
    period: ExportPeriod,
    row_count: int,
    row_file: str,
    source: PrimarySource,
    grain: str,
) -> DatasetCard:
    reason_codes: list[ReasonCode] = []
    if row_count == 0:
        reason_codes.append(ReasonCode.NO_DATA)
    coverage = Coverage.PARTIAL if row_count > 0 else Coverage.UNKNOWN
    outcome = CollectionOutcome.SUCCESS if row_count > 0 else CollectionOutcome.PARTIAL
    return DatasetCard(
        dataset_id=dataset_id,
        provenance=Provenance(
            primary_source=source,
            grain=grain,
            notes="keyword performance export; independent of ExportPeriod bounds",
        ),
        period=period,
        collection_outcome=outcome,
        coverage=coverage,
        reason_codes=reason_codes,
        freshness=FreshnessStatus.UNKNOWN,
        row_file=row_file,
        row_count=row_count,
    )


def build_keyword_daily_card(period: ExportPeriod, *, row_count: int) -> DatasetCard:
    return _keyword_card(
        DatasetId.KEYWORD_DAILY,
        period=period,
        row_count=row_count,
        row_file=KEYWORD_DAILY_LOGICAL,
        source=PrimarySource.CLICKHOUSE_CLUSTERS_ADV_STATS,
        grain="adv_id × leg_role × nmid × norm_query × date",
    )


def build_keyword_windows_card(period: ExportPeriod, *, row_count: int) -> DatasetCard:
    return _keyword_card(
        DatasetId.KEYWORD_WINDOWS,
        period=period,
        row_count=row_count,
        row_file=KEYWORD_WINDOWS_LOGICAL,
        source=PrimarySource.DERIVED_KEYWORD_DAILY,
        grain="identity × window_id",
    )


def build_keyword_current_card(period: ExportPeriod, *, row_count: int) -> DatasetCard:
    return _keyword_card(
        DatasetId.KEYWORD_CURRENT_STATE,
        period=period,
        row_count=row_count,
        row_file=KEYWORD_CURRENT_LOGICAL,
        source=PrimarySource.DERIVED_KEYWORD_DAILY,
        grain="adv_id × nmid × norm_query latest",
    )


def build_keyword_changes_card(period: ExportPeriod, *, row_count: int) -> DatasetCard:
    return _keyword_card(
        DatasetId.KEYWORD_CHANGES,
        period=period,
        row_count=row_count,
        row_file=KEYWORD_CHANGES_LOGICAL,
        source=PrimarySource.DERIVED_KEYWORD_WINDOWS,
        grain="identity × change_id × metric",
    )


def build_keyword_positions_card(period: ExportPeriod, *, row_count: int) -> DatasetCard:
    return _keyword_card(
        DatasetId.KEYWORD_POSITIONS,
        period=period,
        row_count=row_count,
        row_file=KEYWORD_POSITIONS_LOGICAL,
        source=PrimarySource.CLICKHOUSE_KEYWORD_POSITION_API,
        grain="nmid × text × date",
    )


def build_keyword_position_windows_card(
    period: ExportPeriod, *, row_count: int
) -> DatasetCard:
    return _keyword_card(
        DatasetId.KEYWORD_POSITION_WINDOWS,
        period=period,
        row_count=row_count,
        row_file=KEYWORD_POSITION_WINDOWS_LOGICAL,
        source=PrimarySource.DERIVED_KEYWORD_POSITION_WINDOWS,
        grain="nmid × source_query_text × position_type × window_id",
    )


def build_keyword_position_current_card(
    period: ExportPeriod, *, row_count: int
) -> DatasetCard:
    return _keyword_card(
        DatasetId.KEYWORD_POSITION_CURRENT,
        period=period,
        row_count=row_count,
        row_file=KEYWORD_POSITION_CURRENT_LOGICAL,
        source=PrimarySource.DERIVED_KEYWORD_POSITION_WINDOWS,
        grain="nmid × source_query_text × position_type latest",
    )


def build_keyword_decisions_card(period: ExportPeriod, *, row_count: int) -> DatasetCard:
    return _keyword_card(
        DatasetId.KEYWORD_DECISIONS,
        period=period,
        row_count=row_count,
        row_file=KEYWORD_DECISIONS_LOGICAL,
        source=PrimarySource.CLICKHOUSE_BID_DECISION_LOG,
        grain="adv_id × nmid × norm_query × decision_time",
    )


def build_data_map_card(period: ExportPeriod) -> DatasetCard:
    return DatasetCard(
        dataset_id=DatasetId.DATA_MAP,
        provenance=Provenance(
            primary_source=PrimarySource.EXPORT_DATA_MAP,
            grain="package documentation",
            notes="root DATA_MAP.json",
        ),
        period=period,
        collection_outcome=CollectionOutcome.SUCCESS,
        coverage=Coverage.FULL,
        reason_codes=[],
        freshness=FreshnessStatus.UNKNOWN,
        row_file=DATA_MAP_LOGICAL,
        row_count=1,
    )


def build_coverage_card(period: ExportPeriod) -> DatasetCard:
    return DatasetCard(
        dataset_id=DatasetId.KEYWORD_COVERAGE,
        provenance=Provenance(
            primary_source=PrimarySource.EXPORT_KEYWORD_COVERAGE,
            grain="package coverage",
            notes="root coverage.json",
        ),
        period=period,
        collection_outcome=CollectionOutcome.SUCCESS,
        coverage=Coverage.PARTIAL,
        reason_codes=[],
        freshness=FreshnessStatus.UNKNOWN,
        row_file=COVERAGE_LOGICAL,
        row_count=1,
    )
