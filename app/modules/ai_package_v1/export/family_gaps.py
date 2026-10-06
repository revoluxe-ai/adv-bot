"""Каталог явных GAP для семейств данных, не входящих в AI Package v1 export."""

from __future__ import annotations

from typing import Any, Final, TypedDict

from app.modules.ai_package_v1.domain.dataset_card import DatasetCard, Provenance
from app.modules.ai_package_v1.domain.enums import (
    CollectionOutcome,
    Coverage,
    DatasetId,
    FamilyStatus,
    FreshnessStatus,
    PrimarySource,
    ReasonCode,
)
from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.domain.manifest import DomainPayload
from app.modules.ai_package_v1.domain.serialization import canonical_json_bytes
from app.modules.ai_package_v1.export.export_service import ExportResult

PACKAGE_FAMILY_GAPS_LOGICAL: Final = "PACKAGE_FAMILY_GAPS.json"
GAP_DOCUMENT_KIND: Final = "package_family_gaps"
GAP_SCHEMA_VERSION: Final = "1.0.0"


class FamilyGapEntry(TypedDict):
    """Одна запись отсутствующего или неназначенного семейства."""

    family_id: str
    family_status: str
    reason_codes: list[str]
    notes: str


def build_family_gap_catalog() -> list[FamilyGapEntry]:
    """
    Стабильный перечень семейств вне v1 export или без назначенного источника.

    Семейства, уже материализованные ExportService (campaign stat, funnel,
    settings snapshot, keyword_performance), здесь не перечисляются.
    """
    return [
        {
            "family_id": "shop_product_orders_sales_feed",
            "family_status": str(FamilyStatus.GAP),
            "reason_codes": [
                str(ReasonCode.SOURCE_NOT_ASSIGNED),
                str(ReasonCode.UNKNOWN),
            ],
            "notes": (
                "Товарные заказы/продажи магазина: supplier ORDERS/SALES не "
                "назначены shop feed (orders-or-sales-read-identity; v1 card "
                "SOURCE_NOT_ASSIGNED only)."
            ),
        },
        {
            "family_id": "campaign_settings_history",
            "family_status": str(FamilyStatus.GAP),
            "reason_codes": [str(ReasonCode.UNKNOWN)],
            "notes": (
                "История canonical settings (CH campaign_settings_history) "
                "не входит в v1 ZIP; change campaign-settings-history."
            ),
        },
        {
            "family_id": "campaign_change_events",
            "family_status": str(FamilyStatus.GAP),
            "reason_codes": [str(ReasonCode.UNKNOWN)],
            "notes": (
                "Таймлайн change events (settings/campaign mutations) не "
                "экспортируется в v1 ZIP; нет назначенного read-only collector."
            ),
        },
        {
            "family_id": "shop_inventory_discovery",
            "family_status": str(FamilyStatus.GAP),
            "reason_codes": [str(ReasonCode.UNKNOWN)],
            "notes": (
                "Обнаружение кампаний вне PG inventory — "
                "shop-wide-campaign-data-collection, не export path."
            ),
        },
        {
            "family_id": "store_drr",
            "family_status": str(FamilyStatus.GAP),
            "reason_codes": [str(ReasonCode.UNKNOWN)],
            "notes": (
                "Store DRR остаётся разрывом: BLOCKED_BY_SHOP_WIDE_CAMPAIGN_COVERAGE, "
                "BLOCKED_BY_COMMON_SALES, BLOCKED_BY_SHOP_DRR_SOURCE. "
                "Аналитические окна этот разрыв не закрывают."
            ),
        },
        {
            "family_id": "campaign_change_events",
            "status": "GAP",
            "reason_codes": [str(ReasonCode.UNKNOWN)],
            "notes": (
                "Лента изменений кампании не входит в пакет; "
                "BLOCKED_BY_CHANGE_EVENTS."
            ),
        },
        {
            "family_id": "product_prices_stocks",
            "family_status": str(FamilyStatus.GAP),
            "reason_codes": [str(ReasonCode.UNKNOWN)],
            "notes": "Цены и остатки по артикулам не входят в v1 export.",
        },
        {
            "family_id": "finance_promo",
            "family_status": str(FamilyStatus.GAP),
            "reason_codes": [str(ReasonCode.UNKNOWN)],
            "notes": "Финансы и промо-отчёты не входят в v1 export.",
        },
    ]


def build_family_gaps_document(
    export_result: ExportResult,
) -> dict[str, Any]:
    """Строит JSON-документ GAP с привязкой к shop/period export."""
    manifest = export_result.manifest
    return {
        "document_kind": GAP_DOCUMENT_KIND,
        "gap_schema_version": GAP_SCHEMA_VERSION,
        "shop_id": manifest.shop_id,
        "export_period": manifest.period.to_manifest_dict(),
        "generated_at": manifest.generated_at,
        "gaps": build_family_gap_catalog(),
    }


def encode_family_gaps_payload(document: dict[str, Any]) -> bytes:
    """Канонические UTF-8 bytes для PACKAGE_FAMILY_GAPS.json."""
    return canonical_json_bytes(document)


def build_family_gaps_card(period: ExportPeriod) -> DatasetCard:
    """Manifest-карточка для root gaps file (метаданные без строк данных)."""
    return DatasetCard(
        dataset_id=DatasetId.PACKAGE_FAMILY_GAPS,
        provenance=Provenance(
            primary_source=PrimarySource.EXPORT_DATA_MAP,
            grain="family_catalog",
            notes="explicit v1 out-of-package families",
        ),
        period=period,
        collection_outcome=CollectionOutcome.SUCCESS,
        coverage=Coverage.FULL,
        reason_codes=[],
        freshness=FreshnessStatus.FRESH,
        row_file=PACKAGE_FAMILY_GAPS_LOGICAL,
        row_count=len(build_family_gap_catalog()),
    )


def attach_family_gaps(export_result: ExportResult) -> tuple[ExportResult, DomainPayload]:
    """
    Добавляет gaps payload и карточку к результату ExportService.

    Returns:
        Обновлённый ``ExportResult`` и новый ``DomainPayload``.
    """
    document = build_family_gaps_document(export_result)
    content = encode_family_gaps_payload(document)
    payload = DomainPayload(
        logical_name=PACKAGE_FAMILY_GAPS_LOGICAL,
        dataset_id=str(DatasetId.PACKAGE_FAMILY_GAPS),
        content=content,
    )
    gaps_card = build_family_gaps_card(export_result.manifest.period)
    manifest = export_result.manifest.model_copy(
        update={"datasets": [*export_result.manifest.datasets, gaps_card]},
    )
    payloads = [*export_result.payloads, payload]
    return ExportResult(manifest=manifest, payloads=payloads), payload
