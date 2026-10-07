"""Сборка карточек датасетов export (coverage/freshness независимы)."""

from __future__ import annotations

from collections.abc import Sequence

from app.modules.ai_package_v1.domain.coverage_rules import (
    coverage_for_empty_campaign_stat,
    reason_codes_for_campaign_physical_legs,
)
from app.modules.ai_package_v1.domain.dataset_card import DatasetCard, Provenance
from app.modules.ai_package_v1.domain.enums import (
    CollectionOutcome,
    Coverage,
    DatasetId,
    FreshnessStatus,
    PrimarySource,
    ReasonCode,
)
from app.modules.ai_package_v1.domain.campaign_settings_snapshot_v1 import (
    CampaignSettingsSnapshotV1,
)
from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.domain.settings_enums import (
    SettingsCollectionOutcome,
    SettingsCoverageLevel,
    SettingsFreshnessLevel,
    SettingsReasonCode,
)
from app.modules.ai_package_v1.readers.ch_freshness_reader import freshness_from_version_timestamp
from app.modules.ai_package_v1.scope.dto import ExportScopeAdv

CAMPAIGN_SETTINGS_JSON_LOGICAL = "datasets/campaign_settings_snapshot.json"


def _map_settings_collection_outcome(
    outcome: SettingsCollectionOutcome,
) -> CollectionOutcome:
    if outcome == SettingsCollectionOutcome.SUCCESS:
        return CollectionOutcome.SUCCESS
    if outcome == SettingsCollectionOutcome.NO_DATA:
        return CollectionOutcome.UNKNOWN
    return CollectionOutcome.PARTIAL


def _map_settings_coverage(coverage: SettingsCoverageLevel) -> Coverage:
    if coverage == SettingsCoverageLevel.PARTIAL:
        return Coverage.PARTIAL
    if coverage == SettingsCoverageLevel.FULL:
        return Coverage.FULL
    return Coverage.UNKNOWN


def _map_settings_freshness(freshness: SettingsFreshnessLevel) -> FreshnessStatus:
    if freshness == SettingsFreshnessLevel.FRESH:
        return FreshnessStatus.FRESH
    if freshness == SettingsFreshnessLevel.STALE:
        return FreshnessStatus.STALE
    return FreshnessStatus.UNKNOWN


def _map_settings_reason_codes(
    codes: tuple[SettingsReasonCode, ...],
) -> list[ReasonCode]:
    mapped: list[ReasonCode] = []
    for code in codes:
        if code == SettingsReasonCode.NO_DATA:
            mapped.append(ReasonCode.NO_DATA)
        elif code == SettingsReasonCode.UNKNOWN:
            mapped.append(ReasonCode.UNKNOWN)
        elif code == SettingsReasonCode.PARTIAL_PG_WB_SYNC:
            mapped.append(ReasonCode.PARTIAL_PG_WB_SYNC)
        else:
            mapped.append(ReasonCode.PARTIAL_COLLECTION)
    return mapped


def build_campaign_full_stat_card(
    period: ExportPeriod,
    *,
    scoped_adv_ids: list[int],
    row_count: int,
    freshness: FreshnessStatus,
    observed_adv_ids: list[int] | None = None,
) -> DatasetCard:
    """
    Карточка campaign stat с fail-closed coverage (пустой срез ≠ FULL).

    Неполный набор физических adv_id (есть Auto, нет Search или наоборот)
    остаётся PARTIAL и получает ``PARTIAL_COLLECTION``. Отсутствующая нога
    не представлена нулевыми строками.

    Args:
        period: Период export.
        scoped_adv_ids: Ожидаемые физические adv_id из PG scope.
        row_count: Количество строк payload.
        freshness: Сигнал CH freshness (не вывод coverage).
        observed_adv_ids: campaign_id, реально попавшие в срез. ``None`` —
            не оценивать expected-vs-observed (только пустой срез → NO_DATA).

    Returns:
        DatasetCard для manifest.
    """
    if observed_adv_ids is None:
        reason_codes: list[ReasonCode] = (
            [ReasonCode.NO_DATA] if row_count == 0 else []
        )
    else:
        reason_codes = reason_codes_for_campaign_physical_legs(
            scoped_adv_ids=scoped_adv_ids,
            observed_adv_ids=observed_adv_ids,
            row_count=row_count,
        )
    coverage = coverage_for_empty_campaign_stat(
        scoped_adv_ids=scoped_adv_ids,
        row_count=row_count,
        reason_codes=reason_codes,
    )
    collection_outcome = (
        CollectionOutcome.SUCCESS if row_count > 0 else CollectionOutcome.PARTIAL
    )
    if not scoped_adv_ids:
        collection_outcome = CollectionOutcome.UNKNOWN
        coverage = Coverage.NONE
        reason_codes = [ReasonCode.NO_DATA]
    if ReasonCode.PARTIAL_COLLECTION in reason_codes:
        collection_outcome = CollectionOutcome.PARTIAL
        if coverage == Coverage.FULL:
            coverage = Coverage.PARTIAL
    return DatasetCard(
        dataset_id=DatasetId.CAMPAIGN_FULL_STAT,
        provenance=Provenance(
            primary_source=PrimarySource.CLICKHOUSE_FULL_ADV_WB_STAT,
            grain="adv_id + date",
            notes=(
                "Auto and Search adv_id rows preserved separately; "
                "a missing physical leg is omitted, not zero-filled"
            ),
        ),
        period=period,
        collection_outcome=collection_outcome,
        coverage=coverage,
        reason_codes=reason_codes,
        freshness=freshness,
        row_file="datasets/campaign_full_stat.csv",
        row_count=row_count,
    )


def build_complex_adv_funnel_card(
    period: ExportPeriod,
    *,
    scoped_nmids: list[int],
    row_count: int,
    freshness: FreshnessStatus,
) -> DatasetCard:
    """
    Карточка funnel только по main_nmid (не shop-wide).

    Args:
        period: Период export.
        scoped_nmids: main_nmid whitelist.
        row_count: Строк в payload.
        freshness: CH freshness signal.

    Returns:
        DatasetCard для manifest.
    """
    reason_codes: list[ReasonCode] = []
    if row_count == 0:
        reason_codes.append(ReasonCode.NO_DATA)
    coverage = Coverage.UNKNOWN if row_count == 0 else Coverage.PARTIAL
    if not scoped_nmids:
        coverage = Coverage.NONE
        reason_codes = [ReasonCode.NO_DATA]
    collection_outcome = (
        CollectionOutcome.SUCCESS if row_count > 0 else CollectionOutcome.PARTIAL
    )
    if not scoped_nmids:
        collection_outcome = CollectionOutcome.UNKNOWN
    return DatasetCard(
        dataset_id=DatasetId.COMPLEX_ADV_FUNNEL,
        provenance=Provenance(
            primary_source=PrimarySource.CLICKHOUSE_WB_COMMON_STAT,
            grain="nmid + date (main_nmid only)",
            notes="funnel orders do not populate shop_product_orders_sales",
        ),
        period=period,
        collection_outcome=collection_outcome,
        coverage=coverage,
        reason_codes=reason_codes,
        freshness=freshness,
        row_file="datasets/complex_adv_funnel.csv",
        row_count=row_count,
    )


def build_campaign_settings_inventory_card(
    period: ExportPeriod,
    *,
    inventory_rows: Sequence[ExportScopeAdv],
) -> DatasetCard:
    """
    Карточка PG inventory (§6): PARTIAL grain, не WB-universe FULL.

    Detailed settings/bids/budgets — out of scope (отдельный change).

    Args:
        period: Период export (metadata).
        inventory_rows: DTO после ``PgSnapshotReader`` (для row_count).
        row_count: Число inventory строк в payload.

    Returns:
        DatasetCard ``campaign_settings_snapshot``.
    """
    row_count = len(inventory_rows)
    reason_codes: list[ReasonCode] = []
    if row_count == 0:
        reason_codes.append(ReasonCode.NO_DATA)
    coverage = Coverage.PARTIAL if row_count > 0 else Coverage.NONE
    collection_outcome = (
        CollectionOutcome.SUCCESS if row_count > 0 else CollectionOutcome.UNKNOWN
    )
    return DatasetCard(
        dataset_id=DatasetId.CAMPAIGN_SETTINGS_SNAPSHOT,
        provenance=Provenance(
            primary_source=PrimarySource.POSTGRES_INVENTORY,
            grain="auto_adv_id + search_adv_id relation (shop-scoped inventory)",
            notes=(
                "PG inventory only; not full WB cabinet campaign universe; "
                "detailed settings deferred to ai-package-campaign-settings-snapshot"
            ),
        ),
        period=period,
        collection_outcome=collection_outcome,
        coverage=coverage,
        reason_codes=reason_codes,
        freshness=FreshnessStatus.UNKNOWN,
        row_file="datasets/campaign_settings_snapshot.csv",
        row_count=row_count,
    )


def build_detailed_campaign_settings_card(
    period: ExportPeriod,
    *,
    payload: CampaignSettingsSnapshotV1,
) -> DatasetCard:
    """Manifest card для detailed ``CampaignSettingsSnapshotV1`` export."""
    completeness = payload.completeness
    reason_codes = _map_settings_reason_codes(completeness.reason_codes)
    row_count = len(payload.records)
    if row_count == 0 and ReasonCode.NO_DATA not in reason_codes:
        reason_codes.append(ReasonCode.NO_DATA)
    return DatasetCard(
        dataset_id=DatasetId.CAMPAIGN_SETTINGS_SNAPSHOT,
        provenance=Provenance(
            primary_source=PrimarySource.POSTGRES_CAMPAIGN_SETTINGS,
            grain="adv_setting_id + auto_leg + search_leg (detailed settings)",
            notes=(
                "CampaignSettingsSnapshotV1 detailed export; "
                "detailed_settings_export=true; PG-only PARTIAL WB sync"
            ),
        ),
        period=period,
        collection_outcome=_map_settings_collection_outcome(
            completeness.collection_outcome
        ),
        coverage=_map_settings_coverage(completeness.coverage),
        reason_codes=reason_codes,
        freshness=_map_settings_freshness(completeness.freshness),
        row_file=CAMPAIGN_SETTINGS_JSON_LOGICAL,
        row_count=row_count,
    )


def campaign_freshness_status(
    max_version: float | None,
    period: ExportPeriod,
) -> FreshnessStatus:
    """Обёртка над freshness reader pure function."""
    return freshness_from_version_timestamp(max_version, period.end)
