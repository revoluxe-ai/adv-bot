import logging
from typing import Dict, Optional

from app.core.di.wb_api.wb_api_container import WBApiDIContainer
from app.core.mp.wb.api_client.clients.promotion.generated.v1.marketing_i_prodvizhenie.models import (
    PostAdvV0BidsMinBodyPlacementTypesItem,
)

from app.core.di import inject, Provide
from app.core.mp.wb.protocols.promotion_protocol import PromotionAdapterProtocol

logger = logging.getLogger(__name__)


class MinBidMixin:

    @inject
    async def get_min_cpms_for_adv_setting(
        self: "BaseWBApi",
        adv_id: int,
        nmids: list[int],
        promotion_adapter: Optional[PromotionAdapterProtocol] = Provide[
            WBApiDIContainer.current_adapter
        ],
    ) -> Dict[int, int]:
        """
        Получить минимальные CPM ставки для товаров из настройки рекламы.

        Args:
            adv_setting: Настройка рекламной кампании с adv_id и nmids

        Returns:
            Словарь {nmid: min_cpm_bid}
        """
        try:
            # Используем адаптер, переданный через DI
            adapter = promotion_adapter
            # Вызываем адаптер с именованными аргументами
            response = await adapter.get_min_bids(
                advert_id=adv_id,
                nmids=nmids,
                payment_type="cpm",
                placement_type="search",
            )

            # Проверяем пустой ответ
            if not response:
                logger.warning(
                    f"[{self.shop_id}] {adv_id}] Пустой ответ при получении минимальных ставок"
                )
                return {}

            # Преобразуем в удобный формат
            return {int(item["nmid"]): int(item["min_bid"]) for item in response}

        except Exception as e:
            logger.error(
                f"[{self.shop_id}] [{adv_id}] Ошибка получения минимальных ставок CPM: {e}",
                exc_info=True,
            )
            raise
