from __future__ import annotations

"""Миксин для обновления CPM ставок."""

import logging

from app.shared.application.dto.update_bids_in_advs.update_bids_search_adv_ids_batch import (
    UpdateBidsSearchAdvInShopBatch,
    UpdateBidForNmidCommand,
)
from app.core.di import inject
from app.core.mp.wb.base_adapters.base_adapter import WBBaseAdapters

logger = logging.getLogger(__name__)


class CPMUpdateMixin(WBBaseAdapters):
    """Миксин для управления ставками CPM."""

    @inject
    async def update_bids_in_search_advs(
            self: "BaseWBApi",
            update_bids_in_shop_batch: "UpdateBidsSearchAdvInShopBatch",
            promotion_adapter=None,  # DI: PromotionV1Adapter
    ) -> None:
        """
        Тонкий слой: вызывает адаптер для обновления ставок.
        Формирует bids_data (id, nm, cpm) и вызывает promotion_adapter.update_bids.
        Возвращает результат вызова адаптера.
        """
        bids_data: list[dict[str, int]] = []
        for task in update_bids_in_shop_batch.tasks:
            if not isinstance(task, UpdateBidForNmidCommand):
                continue
            try:
                new_bid = await task.new_bid_coro
            except Exception as e:
                logger.error(
                    f"Ошибка вычисления ставки для adv={task.adv_id}, nmid={task.nmid}: {e}"
                )
                continue
            if new_bid is None:
                continue
            bids_data.append(
                {
                    "id": int(task.adv_id),
                    "nm": int(task.nmid),
                    "cpm": int(new_bid),
                }
            )
        if not bids_data:
            return None
        # Тонкий слой: вызываем адаптер и возвращаем его результат
        return await promotion_adapter.update_bids(bids_data)

    async def get_bids_for_nmid_campaign(
            self,
            adv_id: int,
            nmids: list[int],
    ) -> dict[int, int]:
        """
        Получить ставки для списка nmids в рамках кампании adv_id через promotion_adapter.
        """
        return await self.promotion_adapter.get_bids_for_nmid_campaign(adv_id, nmids)
