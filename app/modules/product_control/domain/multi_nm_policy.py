"""
Политика выбора control product для комплекса (pure, Slice A).

Запрещены heuristics: nmids[0], main_nmid, среднее DRR/цены.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.modules.product_control.domain.enums import ProductControlBlockerReason
from app.modules.product_control.domain.models import ProductRef


@dataclass(frozen=True, slots=True)
class ControlProductResolved:
    """Единственный авторитетный control product для scope."""

    product: ProductRef


@dataclass(frozen=True, slots=True)
class ControlProductAmbiguous:
    """Несколько nmID без доказанного единственного control SKU."""

    reason: ProductControlBlockerReason = (
        ProductControlBlockerReason.PRODUCT_CONTROL_MULTI_NM_AMBIGUOUS
    )


ControlProductResolution = ControlProductResolved | ControlProductAmbiguous


def resolve_control_product_for_complex(
    shop_id: str,
    nmids: Sequence[int],
    *,
    authoritative_control_nmid: int | None = None,
) -> ControlProductResolution:
    """
    Определить control ``(shop_id, nmid)`` для product-derived CPO.

    Args:
        shop_id: Идентификатор магазина.
        nmids: Список nmID на физической ноге/комплексе.
        authoritative_control_nmid: Единственный nmID, доказанный политикой
            membership (не main_nmid и не nmids[0] по умолчанию).

    Returns:
        ControlProductResolved при ровно одном nmID или явном authority;
        иначе ControlProductAmbiguous.
    """
    unique = tuple(dict.fromkeys(nmids))
    if len(unique) == 1:
        return ControlProductResolved(
            ProductRef(shop_id=shop_id, nmid=unique[0]),
        )
    if authoritative_control_nmid is not None:
        if authoritative_control_nmid in unique and len(unique) > 1:
            return ControlProductResolved(
                ProductRef(shop_id=shop_id, nmid=authoritative_control_nmid),
            )
    return ControlProductAmbiguous()


def main_nmid_is_not_control_authority(main_nmid: int, nmids: Sequence[int]) -> bool:
    """
    Документирующий helper: main_nmid совпадает с sorted(nmids)[0], но не authority.

    Возвращает True, если при len(nmids) > 1 выбор main_nmid был бы эвристикой.
    """
    if len(nmids) <= 1:
        return False
    sorted_first = sorted(nmids)[0]
    return main_nmid == sorted_first
