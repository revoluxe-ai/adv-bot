"""Разрешение legacy assigned partition E (ComplexAdv snapshot)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.modules.shop_runner.service_manager.exceptions import NotFoundActiveAdvCompany
from app.modules.shop_runner.service_manager.wb_shop_data_manager import WBShopDataManager
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class LegacyAssignedSnapshot:
    """Замороженный снимок legacy assigned nmIDs и ComplexAdv для E-маршрута."""

    nmids: frozenset[int]
    complex_advs: tuple[ComplexAdv, ...]


async def resolve_legacy_assigned_nmids(
    wb_shop_data_manager: WBShopDataManager,
    *,
    only_bot_active: bool = False,
) -> LegacyAssignedSnapshot:
    """
    Загрузить E один раз; NotFoundActiveAdvCompany → пустой E без propagate.

    Args:
        wb_shop_data_manager: менеджер данных магазина shop-runner.
        only_bot_active: флаг legacy ComplexAdv (координатор использует False).

    Returns:
        LegacyAssignedSnapshot с уникальными main_nmid и frozen ComplexAdv list.
    """
    try:
        advs = await wb_shop_data_manager.get_complex_advs(
            only_bot_active=only_bot_active,
            load_extras=False,
        )
    except NotFoundActiveAdvCompany as exc:
        logger.info("shop_wide_common_sales: no active campaigns, E=empty: %s", exc)
        return LegacyAssignedSnapshot(nmids=frozenset(), complex_advs=())

    nmids = frozenset({adv.main_nmid for adv in advs})
    return LegacyAssignedSnapshot(nmids=nmids, complex_advs=tuple(advs))
