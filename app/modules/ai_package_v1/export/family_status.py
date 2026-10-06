"""Единый источник семантики FamilyStatus для summary, gaps и валидации."""

from __future__ import annotations

from collections.abc import Iterable

from app.modules.ai_package_v1.domain.dataset_card import DatasetCard
from app.modules.ai_package_v1.domain.enums import (
    CollectionOutcome,
    Coverage,
    DatasetId,
    FamilyStatus,
    PrimarySource,
    ReasonCode,
)

_FAMILY_STATUS_ORDER: tuple[FamilyStatus, ...] = (
    FamilyStatus.FAILED,
    FamilyStatus.GAP,
    FamilyStatus.UNSUPPORTED,
    FamilyStatus.PARTIAL,
    FamilyStatus.COMPLETE,
)


def combine_family_statuses(statuses: Iterable[FamilyStatus]) -> FamilyStatus:
    """Worst-wins агрегация (fail-closed: пустой ввод → GAP)."""
    items = list(statuses)
    if not items:
        return FamilyStatus.GAP
    worst_index = min(_FAMILY_STATUS_ORDER.index(s) for s in items)
    return _FAMILY_STATUS_ORDER[worst_index]


def derive_family_status_from_card(card: DatasetCard) -> FamilyStatus:
    """
    Сводит независимые измерения dataset card в один FamilyStatus.

    Unknown / fail-closed пары не интерпретируются как COMPLETE.
    """
    if card.collection_outcome == CollectionOutcome.FAILURE:
        return FamilyStatus.FAILED
    if ReasonCode.SOURCE_NOT_ASSIGNED in card.reason_codes:
        return FamilyStatus.GAP
    if card.provenance.primary_source == PrimarySource.SOURCE_NOT_ASSIGNED:
        return FamilyStatus.GAP
    if card.coverage == Coverage.NONE:
        return FamilyStatus.GAP
    if card.collection_outcome == CollectionOutcome.UNKNOWN:
        return FamilyStatus.GAP
    if card.collection_outcome == CollectionOutcome.PARTIAL:
        return FamilyStatus.PARTIAL
    if card.coverage == Coverage.PARTIAL:
        return FamilyStatus.PARTIAL
    if ReasonCode.PARTIAL_COLLECTION in card.reason_codes:
        return FamilyStatus.PARTIAL
    if ReasonCode.PARTIAL_PG_WB_SYNC in card.reason_codes:
        return FamilyStatus.PARTIAL
    if card.collection_outcome == CollectionOutcome.SUCCESS and card.coverage == Coverage.FULL:
        return FamilyStatus.COMPLETE
    if card.collection_outcome == CollectionOutcome.SUCCESS:
        return FamilyStatus.PARTIAL
    return FamilyStatus.GAP


def derive_keyword_performance_family_status(cards: list[DatasetCard]) -> FamilyStatus:
    """Агрегирует все keyword_* dataset cards в одно семейство."""
    keyword_cards = [
        c for c in cards if str(c.dataset_id).startswith("keyword")
    ]
    if not keyword_cards:
        return FamilyStatus.GAP
    return combine_family_statuses(
        derive_family_status_from_card(c) for c in keyword_cards
    )


def family_status_for_gap_entry(status_token: str) -> FamilyStatus:
    """Нормализует status из PACKAGE_FAMILY_GAPS (неизвестное → GAP)."""
    try:
        return FamilyStatus(status_token)
    except ValueError:
        return FamilyStatus.GAP


def dataset_id_for_export_family(family_id: str) -> DatasetId | None:
    """Связь логического family_id summary с dataset_id manifest при наличии."""
    mapping: dict[str, DatasetId] = {
        "campaign_advertising": DatasetId.CAMPAIGN_FULL_STAT,
        "complex_adv_funnel": DatasetId.COMPLEX_ADV_FUNNEL,
        "campaign_settings_current": DatasetId.CAMPAIGN_SETTINGS_SNAPSHOT,
        "shop_common_sales": DatasetId.SHOP_PRODUCT_ORDERS_SALES,
    }
    return mapping.get(family_id)
