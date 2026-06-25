"""Fallback мин. CPM (руб.) при cache miss или невалидном значении из Redis/WB.

Используется на путях расчёта ставок и UI, не при загрузке/refresh кеша min_bids
(``read_min_bids_cache_only``, ``apply_defaults=False``).

Значения из ``settings.MIN_BID_AUTO_DEFAULT`` / ``MIN_BID_SEARCH_DEFAULT``;
встроенные default при пустом env: **100** (auto), **300** (search).
"""

from __future__ import annotations

import logging

from app.core.mp.wb.api.domain_managers.promotion.methods.get_min_bids.convertor import (
    dto_to_command,
)
from app.core.mp.wb.dto.adv_min_bids import AdvMinNmidsBids
from app.core.mp.wb.dto.adv_placement_type import AdvPlacementType
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.settings import settings

logger = logging.getLogger(__name__)


def default_min_bid_rub(placement: AdvPlacementType) -> int:
    """Мин. CPM по умолчанию (руб.) для типа размещения РК."""
    if placement == AdvPlacementType.AUTO_ADV:
        return int(settings.MIN_BID_AUTO_DEFAULT)
    if placement == AdvPlacementType.SEARCH_ADV:
        return int(settings.MIN_BID_SEARCH_DEFAULT)
    raise ValueError(f"Unsupported placement for min bid default: {placement!r}")


def _is_valid_min_bid_rub(value: int | None) -> bool:
    return value is not None and int(value) > 0


def resolve_auto_min_bid_rub(nmid: int, min_bids: AdvMinNmidsBids | None) -> int:
    """Мин. auto CPM (руб.) для nmid; при miss — ``MIN_BID_AUTO_DEFAULT``."""
    if min_bids is not None:
        cached = min_bids.auto.get(nmid)
        if _is_valid_min_bid_rub(cached):
            assert cached is not None
            return int(cached)
    return default_min_bid_rub(AdvPlacementType.AUTO_ADV)


def resolve_search_min_bid_rub(nmid: int, min_bids: AdvMinNmidsBids | None) -> int:
    """Мин. search CPM (руб.) для nmid; при miss — ``MIN_BID_SEARCH_DEFAULT``."""
    if min_bids is not None:
        cached = min_bids.search.get(nmid)
        if _is_valid_min_bid_rub(cached):
            assert cached is not None
            return int(cached)
    return default_min_bid_rub(AdvPlacementType.SEARCH_ADV)


def apply_min_bid_defaults_for_advs(
    min_bids: AdvMinNmidsBids,
    advs: list[ComplexAdv],
    *,
    context: str = "",
) -> AdvMinNmidsBids:
    """Заполнить пропущенные/невалидные ячейки min_bids дефолтами из settings.

    Ожидаемые ячейки — как в ``dto_to_command(advs)``. Raw cache miss не меняет Redis.

    Args:
        min_bids: Результат ``read_min_bids_cache_only`` или WB API.
        advs: Список комплексных РК.
        context: Метка caller'а для логов ``min_bids using default``.

    Returns:
        Новый ``AdvMinNmidsBids`` с подставленными дефолтами где нужно.
    """
    auto = dict(min_bids.auto)
    search = dict(min_bids.search)
    command = dto_to_command(advs)

    for item in command.items:
        default_rub = default_min_bid_rub(item.placement_type)
        target = auto if item.placement_type == AdvPlacementType.AUTO_ADV else search
        for nmid in item.nmids:
            current = target.get(nmid)
            if _is_valid_min_bid_rub(current):
                continue
            target[nmid] = default_rub
            logger.warning(
                "min_bids using default context=%s placement=%s nmid=%s default_rub=%s",
                context,
                item.placement_type.value,
                nmid,
                default_rub,
            )

    return AdvMinNmidsBids(auto=auto, search=search)
