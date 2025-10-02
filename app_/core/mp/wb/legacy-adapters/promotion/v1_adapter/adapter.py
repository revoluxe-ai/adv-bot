"""Адаптер для Promotion API v1 (рефакторинг)."""

import logging
from typing import List, Literal

from ..base_promotion_adapter import BasePromotionAdapter

logger = logging.getLogger(__name__)


class PromotionV1Adapter(BasePromotionAdapter):


    async def get_min_bid_for_adv_nmids(self, adv_id: int, nmids: list[int], payment_type: Literal['cmp','cpc']):








    async def get_campaign_ids(self) -> List[int]:
        """Получить список ID всех поисковых кампаний (тип 8)."""
        from .client_methods_and_models.get_adv_v1_promotion_count import (
            get_adv_v1_promotion_count,
        )
        from .dto import GetCampaignIdsResponseDTO

        response = await self._execute_api_call(
            method_name="get_campaign_ids",
            api_func=get_adv_v1_promotion_count.asyncio,
        )

        # Преобразуем в типизированный DTO с проверками на None/Unset
        result = GetCampaignIdsResponseDTO.from_api_response(response)

        # Возвращаем только ID поисковых кампаний
        return result.search_campaign_ids
