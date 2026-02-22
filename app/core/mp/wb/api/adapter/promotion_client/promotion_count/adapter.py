"""Adapter for GET /adv/v1/promotion/count — список id кампаний по типам 8 и 9 (тот же источник, что и регулярное обновление update_advs_data_from_wb_to_pg)."""

from __future__ import annotations

from app.core.mp.wb.api.adapter.promotion_client.base_section_adapter import (
    BaseSectionAdapter,
)
from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.api.kampanii.get_adv_v1_promotion_count import (
    asyncio_detailed,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
    GetAdvV1PromotionCountResponse200,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.types import (
    UNSET,
)
from app.core.mp.wb.api.retry_decorator import retry_decorator


# Те же типы, что и в ShopDataUpdater (core wb_api mixins): 8 — единая ставка (устаревший), 9 — единая или ручная
_PROMOTION_TYPES = (8, 9)


class PromotionCountAdapter(BaseSectionAdapter):
    """Возвращает список advert_id кабинета через GET /adv/v1/promotion/count (типы 8 и 9). Совпадает с источником для update_advs_data()."""

    @retry_decorator(period=1, limit=5)
    async def get_cabinet_adv_ids(self) -> list[int]:
        """Список id кампаний типа 8 и 9 — тот же источник, что и у регулярного обновления РК."""
        client = await self.auth_client_handler.get_proxy_client(self)
        response = await with_raise_errors(asyncio_detailed, client)
        parsed = response.parsed
        if not isinstance(parsed, GetAdvV1PromotionCountResponse200):
            return []
        adverts = parsed.adverts
        if adverts is None or adverts is UNSET or not adverts:
            return []
        result: list[int] = []
        for group in adverts:
            type_val = group.type_
            if type_val is UNSET or type_val not in _PROMOTION_TYPES:
                continue
            advert_list = group.advert_list
            if advert_list is UNSET or not advert_list:
                continue
            for item in advert_list:
                aid = item.advert_id
                if aid is not UNSET and isinstance(aid, int):
                    result.append(aid)
        return result
