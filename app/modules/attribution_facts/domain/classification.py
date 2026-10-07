"""Чистая классификация DIRECT / LINKED / UNKNOWN."""

from __future__ import annotations

from app.modules.attribution_facts.domain.enums import AttributionClass
from app.modules.attribution_facts.domain.models import MembershipSnapshot


def classify_ordered_nm(
    ordered_nm_id: int,
    snapshot: MembershipSnapshot | None,
) -> AttributionClass:
    """
    Определить класс атрибуции для ordered nm.

    Args:
        ordered_nm_id: nm из breakdown fullstats.
        snapshot: as-of membership; ``None`` если снимок отсутствует.

    Returns:
        DIRECT, LINKED или UNKNOWN. Без fallback LINKED→DIRECT.
    """
    if snapshot is None:
        return AttributionClass.UNKNOWN
    if not snapshot.authoritative:
        return AttributionClass.UNKNOWN
    if not snapshot.promoted_nm_ids:
        return AttributionClass.UNKNOWN
    if ordered_nm_id in snapshot.promoted_nm_ids:
        return AttributionClass.DIRECT
    return AttributionClass.LINKED


def classify_fact_row(
    ordered_nm_id: int,
    snapshot: MembershipSnapshot | None,
    *,
    unsupported_metric: bool = False,
) -> AttributionClass:
    """
    Классификация строки fact с учётом unsupported capability.

    Args:
        ordered_nm_id: Заказанный nm.
        snapshot: Membership snapshot.
        unsupported_metric: True если метрика вне V1 контракта (например buyouts).

    Returns:
        UNSUPPORTED, иначе результат ``classify_ordered_nm``.
    """
    if unsupported_metric:
        return AttributionClass.UNSUPPORTED
    return classify_ordered_nm(ordered_nm_id, snapshot)
