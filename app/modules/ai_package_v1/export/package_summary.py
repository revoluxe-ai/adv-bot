"""Root PACKAGE_SUMMARY.json — детерминированный индекс всего ZIP."""

from __future__ import annotations

import json
from typing import Any, Final, TypedDict, cast

from app.modules.ai_package_v1.domain.dataset_card import DatasetCard
from app.modules.ai_package_v1.domain.enums import (
    DatasetId,
    FamilyStatus,
    PrimarySource,
)
from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.domain.manifest import (
    PACKAGE_SCHEMA_VERSION,
    DomainPayload,
    ExportManifest,
)
from app.modules.ai_package_v1.domain.serialization import canonical_json_bytes
from app.modules.ai_package_v1.export.export_service import ExportResult
from app.modules.ai_package_v1.export.family_gaps import (
    GAP_SCHEMA_VERSION,
    build_family_gap_catalog,
)
from app.modules.ai_package_v1.export.family_status import (
    combine_family_statuses,
    derive_family_status_from_card,
    derive_keyword_performance_family_status,
    family_status_for_gap_entry,
)
from app.modules.ai_package_v1.keyword_performance.export.dataset_cards import (
    DATA_MAP_LOGICAL,
)

PACKAGE_SUMMARY_LOGICAL: Final = "PACKAGE_SUMMARY.json"
SUMMARY_DOCUMENT_KIND: Final = "package_summary"
SUMMARY_SCHEMA_VERSION: Final = "1.0.0"

_MISSING_ZERO_NULL_GLOBAL: Final = {
    "invariant": "missing_row != numeric_zero != json_null",
    "csv": {
        "header_only": "only CSV header means zero data rows, not zero metrics",
        "numeric_zero": "0 is an observed factual zero in a present row",
        "empty_string": "empty CSV field means not applicable for that column",
    },
    "json": {
        "null": "null means absent, unknown, or non-finite per finite_json_rule",
        "zero": "0 is an observed factual zero",
    },
    "coverage_json": {
        "missing_metric": "missing in metric_coverage means no observation, not zero",
        "observed_zero": "observed count may be 0 while requested>0 (true zero activity)",
    },
}


class _FamilyEntry(TypedDict, total=False):
    family_id: str
    family_status: str
    dataset_ids: list[str]
    row_count: int | None
    first_available_date: str | None
    last_available_date: str | None
    primary_join_keys: list[str]
    status_reason_codes: list[str]
    data_pointers: list[str]
    slice_kind: str
    value_semantics: dict[str, str]


def _campaign_identity_block() -> dict[str, Any]:
    return {
        "logical_campaign_resource": (
            "ComplexAdv / PG adv_setting row (adv_setting_id); not a single WB adv_id"
        ),
        "physical_wb_adv_id": {
            "column_name_in_campaign_full_stat_csv": "campaign_id",
            "meaning": (
                "Physical WB advertisement id from default_db.full_adv_wb_stat; "
                "equals auto_adv_id or search_adv_id from PG scope, not a synthetic merge"
            ),
        },
        "auto_search_legs": {
            "auto_leg_adv_id": "PG scope auto_adv_id → rows where campaign_id equals that id",
            "search_leg_adv_id": (
                "PG scope search_adv_id when distinct → rows where campaign_id equals search id"
            ),
            "never_merge": "Auto and Search legs MUST NOT be summed as one campaign_id",
        },
        "join_keys": {
            "campaign_full_stat_to_pg_scope": [
                "manifest.shop_id = campaign_full_stat.shop_id",
                "campaign_full_stat.campaign_id IN (scope.auto_adv_id, scope.search_adv_id)",
            ],
            "keyword_daily_to_campaign_leg": [
                "keyword_daily.adv_id = physical WB adv_id (same as campaign_id in stat)",
                "keyword_daily.leg_role disambiguates AUTO vs SEARCH when adv_id alone ambiguous",
            ],
            "keyword_to_pg_scope": [
                "keyword_daily.adv_setting_id = PG adv_setting primary key",
            ],
        },
    }


def _value_semantics_for_family(family_id: str) -> dict[str, str]:
    if family_id == "shop_common_sales":
        return {
            "missing": "family GAP — no shop product orders/sales feed in v1",
            "zero": "not applicable until source assigned",
            "null": "not applicable",
        }
    if family_id == "campaign_settings_history":
        return {
            "missing": "history not exported in v1 ZIP",
            "zero": "not applicable",
            "null": "not applicable",
        }
    if family_id == "campaign_change_events":
        return {
            "missing": "change-event timeline not exported in v1 ZIP",
            "zero": "not applicable",
            "null": "not applicable",
        }
    if family_id.startswith("keyword") or family_id == "keyword_performance":
        return {
            "missing": "no row for identity×day in payload; see coverage.json",
            "zero": "numeric 0 in JSONL is observed zero activity",
            "null": "null metric means absent or non-finite, not zero",
        }
    return {
        "missing": "no CSV row for shop×entity×day",
        "zero": "numeric 0 in CSV is observed zero",
        "null": "not used in CSV payloads",
    }


def _card_by_dataset(manifest: ExportManifest, dataset_id: DatasetId) -> DatasetCard | None:
    for card in manifest.datasets:
        if card.dataset_id == dataset_id:
            return card
    return None


def _reason_codes_from_card(card: DatasetCard | None) -> list[str]:
    if card is None:
        return ["CARD_MISSING"]
    return [str(c) for c in card.reason_codes]


def _entry_from_card(
    *,
    family_id: str,
    card: DatasetCard | None,
    status: FamilyStatus,
    slice_kind: str | None = None,
    data_pointers: list[str] | None = None,
    primary_join_keys: list[str] | None = None,
    first_date: str | None = None,
    last_date: str | None = None,
) -> _FamilyEntry:
    row_count = card.row_count if card is not None else None
    dataset_ids = [str(card.dataset_id)] if card is not None else []
    return _FamilyEntry(
        family_id=family_id,
        family_status=str(status),
        dataset_ids=dataset_ids,
        row_count=row_count,
        first_available_date=first_date,
        last_available_date=last_date,
        primary_join_keys=primary_join_keys or [],
        status_reason_codes=_reason_codes_from_card(card),
        data_pointers=data_pointers or [],
        slice_kind=slice_kind or "EXPORTED",
        value_semantics=_value_semantics_for_family(family_id),
    )


def _parse_data_map_bounds(payloads: list[DomainPayload]) -> dict[str, str | None]:
    for payload in payloads:
        if payload.logical_name != DATA_MAP_LOGICAL:
            continue
        doc = json.loads(payload.content.decode("utf-8"))
        bounds_raw = doc.get("keyword_history_bounds", {})
        if not isinstance(bounds_raw, dict):
            return {}
        bounds = cast(dict[str, Any], bounds_raw)
        first = bounds.get("daily_first_available")
        last = bounds.get("daily_last_available")
        return {
            "keyword_daily_first": str(first) if first is not None else None,
            "keyword_daily_last": str(last) if last is not None else None,
        }
    return {}


def build_package_summary_document(
    export_result: ExportResult,
    *,
    gap_catalog: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Строит PACKAGE_SUMMARY.json из manifest, cards и gap catalog."""
    manifest = export_result.manifest
    gaps = gap_catalog if gap_catalog is not None else build_family_gap_catalog()
    bounds = _parse_data_map_bounds(export_result.payloads)

    campaign_card = _card_by_dataset(manifest, DatasetId.CAMPAIGN_FULL_STAT)
    funnel_card = _card_by_dataset(manifest, DatasetId.COMPLEX_ADV_FUNNEL)
    settings_card = _card_by_dataset(manifest, DatasetId.CAMPAIGN_SETTINGS_SNAPSHOT)
    sales_card = _card_by_dataset(manifest, DatasetId.SHOP_PRODUCT_ORDERS_SALES)

    campaign_status = (
        derive_family_status_from_card(campaign_card)
        if campaign_card
        else FamilyStatus.GAP
    )
    funnel_status = (
        derive_family_status_from_card(funnel_card) if funnel_card else FamilyStatus.GAP
    )
    settings_status = (
        derive_family_status_from_card(settings_card)
        if settings_card
        else FamilyStatus.GAP
    )
    sales_status = FamilyStatus.GAP
    keyword_status = derive_keyword_performance_family_status(manifest.datasets)

    gap_by_id = {str(g["family_id"]): g for g in gaps}
    history_gap = gap_by_id.get("campaign_settings_history", {})
    change_gap = gap_by_id.get("campaign_change_events", {})
    history_status = family_status_for_gap_entry(str(history_gap.get("status", "GAP")))
    change_status = family_status_for_gap_entry(str(change_gap.get("status", "GAP")))

    period = manifest.period
    families: list[_FamilyEntry] = [
        _entry_from_card(
            family_id="campaign_advertising",
            card=campaign_card,
            status=campaign_status,
            data_pointers=["datasets/campaign_full_stat.csv"],
            primary_join_keys=["shop_id", "campaign_id", "date"],
            first_date=period.start.isoformat(),
            last_date=period.end.isoformat(),
        ),
        _entry_from_card(
            family_id="complex_adv_funnel",
            card=funnel_card,
            status=funnel_status,
            data_pointers=["datasets/complex_adv_funnel.csv"],
            primary_join_keys=["shop_id", "nmid", "date"],
            first_date=period.start.isoformat(),
            last_date=period.end.isoformat(),
        ),
        _entry_from_card(
            family_id="campaign_settings_current",
            card=settings_card,
            status=settings_status,
            slice_kind="CURRENT",
            data_pointers=["datasets/campaign_settings_snapshot.json"],
            primary_join_keys=["adv_setting_id", "auto_leg", "search_leg"],
        ),
        _FamilyEntry(
            family_id="campaign_settings_history",
            family_status=str(history_status),
            dataset_ids=[],
            row_count=0,
            first_available_date=None,
            last_available_date=None,
            primary_join_keys=["adv_setting_id", "effective_from"],
            status_reason_codes=list(history_gap.get("reason_codes", ["UNKNOWN"])),
            data_pointers=["PACKAGE_FAMILY_GAPS.json#gaps.campaign_settings_history"],
            slice_kind="HISTORY",
            value_semantics=_value_semantics_for_family("campaign_settings_history"),
        ),
        _FamilyEntry(
            family_id="campaign_change_events",
            family_status=str(change_status),
            dataset_ids=[],
            row_count=0,
            first_available_date=None,
            last_available_date=None,
            primary_join_keys=["adv_setting_id", "change_time", "field_name"],
            status_reason_codes=list(change_gap.get("reason_codes", ["UNKNOWN"])),
            data_pointers=["PACKAGE_FAMILY_GAPS.json#gaps.campaign_change_events"],
            slice_kind="CHANGE_EVENTS",
            value_semantics=_value_semantics_for_family("campaign_change_events"),
        ),
        _entry_from_card(
            family_id="keyword_performance",
            card=None,
            status=keyword_status,
            data_pointers=[DATA_MAP_LOGICAL, "coverage.json", "datasets/keyword_*.jsonl"],
            primary_join_keys=[
                "adv_id",
                "leg_role",
                "nmid",
                "norm_query",
                "date",
            ],
            first_date=bounds.get("keyword_daily_first"),
            last_date=bounds.get("keyword_daily_last"),
        ),
        _entry_from_card(
            family_id="shop_common_sales",
            card=sales_card,
            status=sales_status,
            slice_kind="COMMON_SALES",
            data_pointers=["PACKAGE_FAMILY_GAPS.json#gaps.shop_product_orders_sales_feed"],
            primary_join_keys=["shop_id", "nmid", "date"],
        ),
    ]

    effective_coverage = combine_family_statuses(
        FamilyStatus(str(f["family_status"])) for f in families if "family_status" in f
    )

    return {
        "document_kind": SUMMARY_DOCUMENT_KIND,
        "summary_schema_version": SUMMARY_SCHEMA_VERSION,
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "gap_schema_version": GAP_SCHEMA_VERSION,
        "shop_id": manifest.shop_id,
        "export_period": period.to_manifest_dict(),
        "generated_at": manifest.generated_at,
        "effective_coverage": str(effective_coverage),
        "campaign_identity": _campaign_identity_block(),
        "missing_zero_null": _MISSING_ZERO_NULL_GLOBAL,
        "families": families,
        "pointers": {
            "data_map": DATA_MAP_LOGICAL,
            "family_gaps": "PACKAGE_FAMILY_GAPS.json",
            "manifest": "manifest.json",
        },
    }


def encode_package_summary_payload(document: dict[str, Any]) -> bytes:
    """Канонические UTF-8 bytes для PACKAGE_SUMMARY.json."""
    return canonical_json_bytes(document)


def build_package_summary_card(period: ExportPeriod) -> DatasetCard:
    """Manifest card для root summary (metadata only)."""
    from app.modules.ai_package_v1.domain.dataset_card import DatasetCard, Provenance
    from app.modules.ai_package_v1.domain.enums import (
        CollectionOutcome,
        Coverage,
        FreshnessStatus,
    )

    return DatasetCard(
        dataset_id=DatasetId.PACKAGE_SUMMARY,
        provenance=Provenance(
            primary_source=PrimarySource.EXPORT_DATA_MAP,
            grain="package_index",
            notes="deterministic PACKAGE_SUMMARY builder",
        ),
        period=period,
        collection_outcome=CollectionOutcome.SUCCESS,
        coverage=Coverage.FULL,
        reason_codes=[],
        freshness=FreshnessStatus.FRESH,
        row_file=PACKAGE_SUMMARY_LOGICAL,
        row_count=1,
    )


def attach_package_summary(export_result: ExportResult) -> tuple[ExportResult, DomainPayload]:
    """
    Добавляет PACKAGE_SUMMARY.json и карточку к результату export (+ gaps если уже есть).

    Returns:
        Обновлённый ``ExportResult`` и новый ``DomainPayload``.
    """
    document = build_package_summary_document(export_result)
    content = encode_package_summary_payload(document)
    payload = DomainPayload(
        logical_name=PACKAGE_SUMMARY_LOGICAL,
        dataset_id=str(DatasetId.PACKAGE_SUMMARY),
        content=content,
    )
    summary_card = build_package_summary_card(export_result.manifest.period)
    manifest = export_result.manifest.model_copy(
        update={"datasets": [*export_result.manifest.datasets, summary_card]},
    )
    payloads = [*export_result.payloads, payload]
    return ExportResult(manifest=manifest, payloads=payloads), payload
