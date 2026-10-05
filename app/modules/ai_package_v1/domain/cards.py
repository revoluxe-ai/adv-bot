"""Фабрики карточек датасетов v1 (без CH/PG адаптеров)."""

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


def build_shop_product_orders_sales_card(period: ExportPeriod) -> DatasetCard:
    """
    Карточка товарных заказов/продаж магазина: источник не назначен (v1).

    Без строк данных; fail-closed по coverage/collection_outcome.
    """
    return DatasetCard(
        dataset_id=DatasetId.SHOP_PRODUCT_ORDERS_SALES,
        provenance=Provenance(
            primary_source=PrimarySource.SOURCE_NOT_ASSIGNED,
            grain="n/a",
            notes="v1: no supplier or funnel stand-in",
        ),
        period=period,
        collection_outcome=CollectionOutcome.UNKNOWN,
        coverage=Coverage.UNKNOWN,
        reason_codes=[ReasonCode.SOURCE_NOT_ASSIGNED, ReasonCode.UNKNOWN],
        freshness=FreshnessStatus.UNKNOWN,
        row_file=None,
        row_count=0,
    )


def build_campaign_settings_unknown_card(period: ExportPeriod) -> DatasetCard:
    """Минимальная заглушка PG inventory до discovery §1.1–1.2."""
    return DatasetCard(
        dataset_id=DatasetId.CAMPAIGN_SETTINGS_SNAPSHOT,
        provenance=Provenance(
            primary_source=PrimarySource.UNKNOWN,
            grain="adv_id",
            notes="detailed settings deferred to ai-package-campaign-settings-snapshot",
        ),
        period=period,
        collection_outcome=CollectionOutcome.UNKNOWN,
        coverage=Coverage.UNKNOWN,
        reason_codes=[ReasonCode.UNKNOWN],
        freshness=FreshnessStatus.UNKNOWN,
        row_file=None,
        row_count=None,
    )
