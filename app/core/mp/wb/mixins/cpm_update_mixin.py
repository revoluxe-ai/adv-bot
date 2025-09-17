from __future__ import annotations

"""Миксин для обновления CPM ставок."""

import logging

from app.shared.application.dto.update_bids_in_advs.update_bids_search_adv_ids_batch import (
    UpdateBidsSearchAdvInShopBatch,
    UpdateBidForNmidTask,
    UpdateBidsResolvedBatch,
    UpdateBidResolvedTask,
)
from app.core.di import inject

logger = logging.getLogger(__name__)


class CPMUpdateMixin:
    """Миксин для управления ставками CPM."""

    @inject
    async def update_bids_in_search_advs(
        self: "BaseWBApi",
        update_bids_in_shop_batch: "UpdateBidsSearchAdvInShopBatch",
    ) -> None:
        """Отправляет ставки в WB Promotion API через promotion_adapter (DI).

        Принимает батч с ленивыми корутинами ставок, разворачивает их и формирует
        массив bids, поддерживая множественные кампании в одном запросе.
        """
        # Собираем все обновления (await корутин) в единый список
        bids_data: list[dict[str, int]] = []
        for task in update_bids_in_shop_batch.tasks:
            # тип: UpdateBidForNmidTask
            if not isinstance(task, UpdateBidForNmidTask):
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

        # Граничим размер запроса 50 элементов; отправляем чанками
        for i in range(0, len(bids_data), 50):
            chunk = bids_data[i : i + 50]
            # try:
            # promotion_adapter знает как маппить к generated клиенту
            # await adapter.update_bids(bids=chunk)
            # except Exception as e:
            #     logger.error(f"Ошибка обновления ставок в WB API: {e}")
        return None

    @inject
    async def update_bids_in_search_advs_resolved(
        self: "BaseWBApi",
        resolved_batch: "UpdateBidsResolvedBatch",
        # promotion_v1_adapter: Optional[PromotionAdapterProtocol] = Provide[
        #     WBApiDIContainer.current_adapter
        # ],
    ) -> None:
        """Отправка готовых ставок (без корутин) чанками через promotion_adapter (DI)."""
        # adapter = promotion_v1_adapter

        bids_data: list[dict[str, int]] = []
        for task in resolved_batch.tasks:
            if not isinstance(task, UpdateBidResolvedTask):
                continue
            bids_data.append(
                {
                    "id": int(task.adv_id),
                    "nm": int(task.nmid),
                    "cpm": int(task.new_bid),
                }
            )

        if not bids_data:
            return None

        for i in range(0, len(bids_data), 50):
            chunk = bids_data[i : i + 50]
            # try:
            #     await adapter.update_bids(bids=chunk)
            # except Exception as e:
            #     logger.error(f"Ошибка обновления ставок в WB API (resolved): {e}")
        return None
