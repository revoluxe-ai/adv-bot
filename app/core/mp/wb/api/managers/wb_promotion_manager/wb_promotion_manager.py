from __future__ import annotations

import logging
import typing
from collections.abc import Awaitable
from typing import Callable


from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.wb_update_state_manager import AdvActiveKeywordUpdateStateManager
from app.shared.domains.wb.enums import AdvType
from app.core.mp.wb.api.adapter.promotion_client.common_bids.command import (
    SetCommonBidsCommand,
)

logger = logging.getLogger(__name__)


if typing.TYPE_CHECKING:
    from app.core.mp.wb.api.domain_managers.promotion import (
        PromotionManager,
        CampaignBudgetInfo,
        BudgetTopUpResult,
    )
    from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
        GetAdvV1BalanceResponse200,
    )
    from app.core.mp.wb.api.domain_managers.promotion import PromotionManager
    from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.new_bids_calculator.update_bids_command import (
        UpdateBidsCommand,
    )



class WBModifier:
    def __init__(self, promotion_manager: "PromotionManager") -> None:
        self._promotion_manager: "PromotionManager" = promotion_manager

    async def set_minus_phrases_for_adv(
        self,
        adv_id: int,
        nmid: int,
        phrases: list[str],
        update_redis_timestamp_manager: AdvActiveKeywordUpdateStateManager,
    ) -> None:
        # TODO: WB походу сделал так, что можно ставить отдельно на каждый nmid внутри фразы РК. Надо адаптировать к этому бот
        try:
            await self._promotion_manager.set_minus_phrases(adv_id, nm_id=nmid, phrases=phrases)
        except Exception as e:
            logger.error('Ошибка обновления минус-фраз: %s', e, exc_info=True)
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

    async def update_auto_adv_cpm(
        self, adv_id: int, nm_bid_pairs: dict[int, int]
    ) -> None:
        """Понижает CPM автоматической кампании до предельных значений."""
        from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
            PatchAdvV0BidsBody,
            V0AdvertMultibid,
            V0AdvertMultiBidItem,
        )

        nm_bid_items = [
            V0AdvertMultiBidItem(nm=nmid, bid=bid) for nmid, bid in nm_bid_pairs.items()
        ]

        body = PatchAdvV0BidsBody(
            bids=[V0AdvertMultibid(advert_id=adv_id, nm_bids=nm_bid_items)]
        )

        await self._promotion_manager.patch_adv_bids(body)

    async def get_campaign_budget(self, adv_id: int) -> "CampaignBudgetInfo":
        return await self._promotion_manager.get_campaign_budget(adv_id)

    async def top_up_budget(
        self,
        adv_id: int,
        amount: int,
        balance_type: str,
        return_total: bool = True,
    ) -> "BudgetTopUpResult":
        return await self._promotion_manager.top_up_budget(
            adv_id=adv_id,
            amount=amount,
            balance_type=balance_type,
            return_total=return_total,
        )

    async def get_campaign_balance(self) -> typing.Union["GetAdvV1BalanceResponse200", None]:
        return await self._promotion_manager.get_campaign_balance()


    async def start_auto_campaign(self, complex_adv: ComplexAdv) -> None:
        """Запустить автоматическую кампанию для магазина."""
        await self.start_campaign_by_type(complex_adv, AdvType.AUTO)

    async def pause_auto_campaign(self, complex_adv: ComplexAdv) -> None:
        """Поставить на паузу автоматическую кампанию."""
        await self.pause_campaign_by_type(complex_adv, AdvType.AUTO)

    async def stop_auto_campaign(self, complex_adv: ComplexAdv) -> None:
        """Полностью остановить автоматическую кампанию."""
        await self.stop_campaign_by_type(complex_adv, AdvType.AUTO)

    async def start_auction_campaign(self, complex_adv: ComplexAdv) -> None:
        """Запустить аукционную кампанию по Cluster."""
        await self.start_campaign_by_type(complex_adv, AdvType.SEARCH)

    async def pause_auction_campaign(self, complex_adv: ComplexAdv) -> None:
        """Приостановить аукционную кампанию."""
        await self.pause_campaign_by_type(complex_adv, AdvType.SEARCH)

    async def stop_auction_campaign(self, complex_adv: ComplexAdv) -> None:
        """Остановить аукционную кампанию наверняка."""
        await self.stop_campaign_by_type(complex_adv, AdvType.SEARCH)

    async def start_campaign_by_type(
        self, complex_adv: ComplexAdv, adv_type: AdvType
    ) -> None:
        """Запустить кампанию заданного типа."""
        await self._control_campaign_by_type(
            complex_adv, adv_type, self._promotion_manager.start_campaign
        )

    async def pause_campaign_by_type(
        self, complex_adv: ComplexAdv, adv_type: AdvType
    ) -> None:
        """Поставить на паузу кампанию заданного типа."""
        await self._control_campaign_by_type(
            complex_adv, adv_type, self._promotion_manager.pause_campaign
        )

    async def stop_campaign_by_type(
        self, complex_adv: ComplexAdv, adv_type: AdvType
    ) -> None:
        """Остановить кампанию заданного типа."""
        await self._control_campaign_by_type(
            complex_adv, adv_type, self._promotion_manager.stop_campaign
        )
    @staticmethod
    async def _control_campaign_by_type(
        complex_adv: ComplexAdv,
        adv_type: AdvType,
        action: Callable[[int], Awaitable[None]],
    ) -> None:
        adv_id = complex_adv.get_adv_id_by_type(adv_type)
        await action(adv_id)

    async def update_search_adv_common_cpm(
        self, command: SetCommonBidsCommand
    ) -> None:
        await self._promotion_manager.set_common_bids(command)
