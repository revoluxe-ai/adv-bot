"""Validate a single campaign ID for connect-existing flow (by shop_id, nmid, type)."""

from __future__ import annotations

import logging
from typing import Any, Literal

from app.core.di.app_container import AppContainer
from app.core.di.di_manager import DIManager
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
    GetAdvertsAdvertsItem,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models.get_adverts_adverts_item_status import (
    GetAdvertsAdvertsItemStatus,
)
from app.modules.connect_existing_advs.candidates_service import (
    filter_and_classify_campaigns_by_nmid,
)

logger = logging.getLogger(__name__)

CampaignType = Literal["auction", "auto"]

# Статусы, при которых кампанию не предлагаем для подключения (завершена/отклонена)
_CONNECTABLE_EXCLUDE_STATUSES = {
    GetAdvertsAdvertsItemStatus.VALUE_7,  # done
    GetAdvertsAdvertsItemStatus.VALUE_8,  # refused
}

_STATUS_DISPLAY_RU: dict[int | str, str] = {
    4: "готова к старту",
    7: "завершена",
    8: "отклонена",
    9: "запущена",
    11: "пауза",
}


def _format_status_for_display(status: int | str | None) -> str:
    if status is None:
        return "—"
    return _STATUS_DISPLAY_RU.get(status, str(status))


def _serialize_candidate_item(item: GetAdvertsAdvertsItem) -> dict[str, Any]:
    """Serialize one campaign to FSM-style dict (id, name, status, status_text)."""
    status_val = getattr(item.status, "value", item.status) if hasattr(item.status, "value") else item.status
    name = getattr(getattr(item, "settings", None), "name", "") or ""
    return {
        "id": item.id,
        "name": name,
        "status": status_val,
        "status_text": _format_status_for_display(status_val),
    }


async def validate_campaign_id_for_connect(
    shop_id: str,
    nmid: int,
    adv_id: int,
    campaign_type: CampaignType,
) -> tuple[bool, str, dict[str, Any] | None]:
    """
    Validate that adv_id is a connectable campaign for this nmid and type (auction or auto).

    Returns:
        (success, error_message, serialized_candidate_dict or None)
    """
    try:
        async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
            factory = (
                container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
            )
            hub = factory.get_wb_manager_hub(shop_id)
            pm = hub.wb_data_manager.promotion_manager
            campaigns = await pm.get_campaigns_info([adv_id])
    except Exception as e:
        logger.warning("validate_campaign_id get_campaigns_info failed: %s", e)
        return False, "Не удалось проверить кампанию в WB. Попробуйте позже.", None

    if not campaigns:
        return False, "Кампания не найдена.", None

    result = filter_and_classify_campaigns_by_nmid(campaigns, nmid)
    if campaign_type == "auction":
        candidates = result.auction_candidates
        type_label = "поисковую (аукцион)"
    else:
        candidates = result.auto_candidates
        type_label = "авто"

    item = next((c for c in candidates if c.id == adv_id), None)
    if item is None:
        if not result.auction_candidates and not result.auto_candidates:
            return False, "Кампания не подходит для этого артикула или не того типа.", None
        return False, f"Кампания не подходит: укажите {type_label} РК для артикула {nmid}.", None

    if item.status in _CONNECTABLE_EXCLUDE_STATUSES:
        return False, "Кампания завершена или отклонена. Выберите активную кампанию.", None

    return True, "", _serialize_candidate_item(item)
