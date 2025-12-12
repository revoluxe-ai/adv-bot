from __future__ import annotations

import typing
import logging
if typing.TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.new_bids_calculator.\
    update_bids_command import (
    UpdateBidsCommand)

from app.modules.wb_update_state_manager import AdvActiveKeywordUpdateStateManager

logger = logging.getLogger(__name__)


if typing.TYPE_CHECKING:
    from app.core.mp.wb.api.domain_managers.promotion import PromotionManager



class WBModifier:
    def __init__(self, promotion_manager: "PromotionManager") -> None:
        self._promotion_manager: "PromotionManager" = promotion_manager

    async def set_minus_phrases_for_adv(
        self,
            adv_id: int,
            nmid: int,
            phrases: list[str],
            update_redis_timestamp_manager: AdvActiveKeywordUpdateStateManager
    ) -> None:
        # TODO: WB походу сделал так, что можно ставить отдельно на каждый nmid внутри фразы РК. Надо адаптировать к этому бот
        try:
            await self._promotion_manager.set_minus_phrases(adv_id, nm_id=nmid, phrases=phrases)
        except Exception as e:
            logger.error('Ошибка обновления минус-фраз: %s', exc_info=True)
            raise e
        await update_redis_timestamp_manager.set_one(adv_id=adv_id)
        return None

    async def set_cluster_bids_for_adv(self, bids: "UpdateBidsCommand") -> None:
        """Устанавливает ставки по кластерам для РК.
        
        Args:
            bids: Список ставок. Каждый элемент содержит:
                - advert_id: ID рекламной кампании
                - nm_id: Артикул WB
                - norm_query: Поисковый кластер (фраза)
                - bid: Ставка за 1000 показов в рублях
        """
        from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.command import (
            SetNormqueryBidsCommandItem,
        )
        
        # Конвертируем NewBid в SetNormqueryBidsCommandItem
        converted_bids = [
            SetNormqueryBidsCommandItem(
                advert_id=bid.adv_id,
                nm_id=bid.nmid,
                norm_query=bid.cluster,
                bid=bid.new_bid,
            )
            for bid in bids.new_bids
        ]
        
        await self._promotion_manager.set_cluster_bids(converted_bids)
        return None
