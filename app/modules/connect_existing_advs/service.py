"""Entry point: get connect-existing candidates for shop_id and nmid via DI."""

from __future__ import annotations

import logging

from app.core.di.app_container import AppContainer
from app.core.di.di_manager import DIManager
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models.get_adverts_adverts_item_status import (
    GetAdvertsAdvertsItemStatus,
)
from app.modules.connect_existing_advs.candidates_service import (
    ConnectExistingCandidatesResult,
)

logger = logging.getLogger(__name__)

STATUS_DONE_WB = GetAdvertsAdvertsItemStatus.VALUE_7
STATUS_CANCELLED_WB = GetAdvertsAdvertsItemStatus.VALUE_8

async def is_campaign_done_on_wb(shop_id: str, adv_id: int) -> bool:
    """
    True, если кампания на WB в статусе «завершена» (7) или не найдена.
    Используется, чтобы не показывать «Использовать подключённую» для авто, которая уже завершена на WB.
    """
    async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
        factory = container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
        hub = factory.get_wb_manager_hub(shop_id)
        pm = hub.wb_data_manager.promotion_manager
        status = await pm.get_campaign_status(adv_id)
        return status is None or status in [STATUS_DONE_WB, STATUS_CANCELLED_WB]


async def get_connect_existing_candidates(
    shop_id: str,
    nmid: int,
    extra_adv_ids: list[int] | None = None,
) -> ConnectExistingCandidatesResult:
    """
    Get candidates for connecting existing campaigns (auction + auto) by shop_id and nmid.
    extra_adv_ids: ids из БД по этому артикулу — запрашиваются у WB дополнительно, чтобы кампании,
    не попавшие в список /adv/v1/adverts, всё равно оказались в кандидатах.
    """
    async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
        factory = container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
        hub = factory.get_wb_manager_hub(shop_id)
        pm = hub.wb_data_manager.promotion_manager
        return await pm.get_connect_existing_candidates(nmid, extra_adv_ids=extra_adv_ids)
