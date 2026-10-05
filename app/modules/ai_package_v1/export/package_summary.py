"""Root PACKAGE_SUMMARY.json — детерминированный индекс всего ZIP."""

from __future__ import annotations

import json
from typing import Any, Final, TypedDict, cast

from app.modules.ai_package_v1.domain.dataset_card import DatasetCard
from app.modules.ai_package_v1.domain.enums import (
    DatasetId,
    FamilyStatus,
    PrimarySource,
    ReasonCode,
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
PACKAGE_SUMMARY_SCHEMA_VERSION: Final = "1"

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
    canonical_status: str
    dataset_ids: list[str]
    row_count: int | None
    object_count: int | None
    first_date: str | None
    last_date: str | None
    primary_key: list[str]
    join_keys: list[str]
    reasons: list[str]
    dataset_pointer: str | None
    data_map_pointer: str | None
    slice_kind: str
    missing_zero_null: dict[str, str]


def _campaign_identity_block() -> dict[str, Any]:
    return {
        "campaign_id_equals_physical_adv_id": True,
        "logical_campaign_resource_id": "adv_setting_id",
        "optional_resource_pointer": "a1_resource_id",
        "physical_adv_id_fields": {
            "campaign_stat.campaign_id": "CH full_adv_wb_stat adv_id grain",
            "settings.legs.wb_adv_id": "per-leg physical id",
            "keyword.adv_id": "same physical id as campaign_stat.campaign_id",
        },
        "leg_identity": {
            "leg_role": ["AUTO", "SEARCH"],
            "auto_physical_adv_id": "scope.auto_adv_id",
            "search_physical_adv_id": "scope.search_adv_id when distinct",
        },
        "auto_search_must_not_merge": True,
        "join": (
            "campaign_stat.campaign_id = settings.legs.wb_adv_id = keyword.adv_id "
            "AND keyword.leg_role = settings.legs.leg_role"
        ),
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
    dataset_pointer: str | None = None,
    data_map_pointer: str | None = None,
    primary_key: list[str] | None = None,
    join_keys: list[str] | None = None,
    first_date: str | None = None,
    last_date: str | None = None,
    extra_reasons: list[str] | None = None,
) -> _FamilyEntry:
    row_count = card.row_count if card is not None else None
    dataset_ids = [str(card.dataset_id)] if card is not None else []
    reasons = _reason_codes_from_card(card)
    if extra_reasons:
        reasons = [*reasons, *extra_reasons]
    if status in (FamilyStatus.GAP, FamilyStatus.PARTIAL) and not reasons:
        reasons = ["STATUS_REQUIRES_REASON"]
    keys = primary_key or join_keys or []
    return _FamilyEntry(
        family_id=family_id,
        canonical_status=str(status),
        dataset_ids=dataset_ids,
        row_count=row_count,
        first_date=first_date,
        last_date=last_date,
        primary_key=keys,
        join_keys=join_keys or keys,
        reasons=reasons,
        dataset_pointer=dataset_pointer,
        data_map_pointer=data_map_pointer,
        slice_kind=slice_kind or "EXPORTED",
        missing_zero_null=_value_semantics_for_family(family_id),
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
    def _gap_status(gap: dict[str, Any]) -> FamilyStatus:
        token = gap.get("family_status") or gap.get("status", "GAP")
        return family_status_for_gap_entry(str(token))

    history_status = _gap_status(history_gap)
    change_status = _gap_status(change_gap)

    period = manifest.period
    requested = period.to_manifest_dict()
    families: list[_FamilyEntry] = [
        _entry_from_card(
            family_id="campaign_full_stat",
            card=campaign_card,
            status=campaign_status,
            dataset_pointer="datasets/campaign_full_stat.csv",
            primary_key=["shop_id", "campaign_id", "date"],
            join_keys=["shop_id", "campaign_id", "date"],
            first_date=period.start.isoformat(),
            last_date=period.end.isoformat(),
        ),
        _entry_from_card(
            family_id="complex_adv_funnel",
            card=funnel_card,
            status=funnel_status,
            dataset_pointer="datasets/complex_adv_funnel.csv",
            primary_key=["shop_id", "nmid", "date"],
            join_keys=["shop_id", "nmid", "date"],
            first_date=period.start.isoformat(),
            last_date=period.end.isoformat(),
        ),
        _entry_from_card(
            family_id="campaign_settings_current",
            card=settings_card,
            status=settings_status,
            slice_kind="CURRENT",
            dataset_pointer="datasets/campaign_settings_snapshot.json",
            primary_key=["adv_setting_id", "leg_role", "wb_adv_id"],
            join_keys=["adv_setting_id", "leg_role", "wb_adv_id"],
            extra_reasons=[str(ReasonCode.PARTIAL_PG_WB_SYNC)]
            if settings_status == FamilyStatus.PARTIAL
            else None,
        ),
        _FamilyEntry(
            family_id="campaign_settings_history",
            canonical_status=str(history_status),
            dataset_ids=[],
            row_count=0,
            first_date=None,
            last_date=None,
            primary_key=["adv_setting_id", "effective_from"],
            join_keys=["adv_setting_id", "effective_from"],
            reasons=list(history_gap.get("reason_codes", ["UNKNOWN"])),
            dataset_pointer="PACKAGE_FAMILY_GAPS.json",
            slice_kind="HISTORY",
            missing_zero_null=_value_semantics_for_family("campaign_settings_history"),
        ),
        _FamilyEntry(
            family_id="campaign_change_events",
            canonical_status=str(change_status),
            dataset_ids=[],
            row_count=0,
            first_date=None,
            last_date=None,
            primary_key=["adv_setting_id", "change_time", "field_name"],
            join_keys=["adv_setting_id", "change_time", "field_name"],
            reasons=list(change_gap.get("reason_codes", ["UNKNOWN"])),
            dataset_pointer="PACKAGE_FAMILY_GAPS.json",
            slice_kind="CHANGE_EVENTS",
            missing_zero_null=_value_semantics_for_family("campaign_change_events"),
        ),
        _entry_from_card(
            family_id="keyword_performance",
            card=None,
            status=keyword_status,
            dataset_pointer="keyword_performance/keyword_daily.jsonl",
            data_map_pointer=DATA_MAP_LOGICAL,
            primary_key=["adv_id", "leg_role", "nmid", "norm_query", "date"],
            join_keys=["adv_id", "leg_role", "nmid", "norm_query", "date"],
            first_date=bounds.get("keyword_daily_first"),
            last_date=bounds.get("keyword_daily_last"),
        ),
        _entry_from_card(
            family_id="shop_product_orders_sales_feed",
            card=sales_card,
            status=sales_status,
            slice_kind="COMMON_SALES",
            dataset_pointer="PACKAGE_FAMILY_GAPS.json",
            primary_key=["shop_id", "nmid", "date"],
            join_keys=["shop_id", "nmid", "date"],
            extra_reasons=[
                str(ReasonCode.SOURCE_NOT_ASSIGNED),
                str(ReasonCode.UNKNOWN),
            ],
        ),
    ]
    families_sorted = sorted(families, key=lambda f: f["family_id"])

    observed_dates: dict[str, str | None] = {
        "campaign_full_stat_last": period.end.isoformat(),
        "keyword_daily_first": bounds.get("keyword_daily_first"),
        "keyword_daily_last": bounds.get("keyword_daily_last"),
    }

    return {
        "document_kind": SUMMARY_DOCUMENT_KIND,
        "package_summary_schema_version": PACKAGE_SUMMARY_SCHEMA_VERSION,
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "shop_id": manifest.shop_id,
        "requested_period": requested,
        "effective_coverage": {
            "requested": requested,
            "observed_date_bounds": observed_dates,
            "aggregate_canonical_status": str(
                combine_family_statuses(
                    FamilyStatus(str(f["canonical_status"])) for f in families_sorted
                ),
            ),
        },
        "generated_at": manifest.generated_at,
        "campaign_identity": _campaign_identity_block(),
        "missing_zero_null": _MISSING_ZERO_NULL_GLOBAL,
        "zip_determinism_contract": "PAYLOAD_HASH_ONLY",
        "families": families_sorted,
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
