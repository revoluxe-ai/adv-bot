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
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
    PatchApiAdvertV1BidsBody,
    PatchApiAdvertV1BidsBodyBidsItem,
    PatchApiAdvertV1BidsBodyBidsItemNmBidsItem,
    PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement,
)

logger = logging.getLogger(__name__)


if typing.TYPE_CHECKING:
    from app.core.mp.wb.api.domain_managers.promotion import (
        PromotionManager,
        CampaignBudgetInfo,
        BudgetTopUpResult,
        SetMinusPhrasesFallbackResult,
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

    async def set_minus_phrases_with_fallback_for_adv(
        self,
        adv_id: int,
        nmid: int,
        phrases: list[str],
        update_redis_timestamp_manager: AdvActiveKeywordUpdateStateManager,
    ) -> "SetMinusPhrasesFallbackResult":
        try:
            result = await self._promotion_manager.set_minus_phrases_with_fallback(
                advert_id=adv_id,
                nm_id=nmid,
                phrases=phrases,
            )
        except Exception as e:
            logger.error("Ошибка обновления минус-фраз: %s", e, exc_info=True)
            raise e
        if not result.skipped_unsupported_campaign:
            await update_redis_timestamp_manager.set_one(adv_id=adv_id)
        return result

    async def get_minus_phrases_for_adv(self, adv_id: int, nmid: int) -> list[str]:
        """Получить текущий список минус-фраз для пары кампания + номенклатура."""
        return await self._promotion_manager.get_minus_phrases(
            advert_id=adv_id, nm_id=nmid
        )

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
                advert_id=bid.search_adv_id,
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
        """Обновляет CPM авто-кампании через PATCH /api/advert/v1/bids (ставки в копейках)."""
        placement = PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.COMBINED
        nm_bids = [
            PatchApiAdvertV1BidsBodyBidsItemNmBidsItem(
                nm_id=nm_id,
                bid_kopecks=int(bid_rub * 100),
                placement=placement,
            )
            for nm_id, bid_rub in nm_bid_pairs.items()
        ]
        body = PatchApiAdvertV1BidsBody(
            bids=[
                PatchApiAdvertV1BidsBodyBidsItem(
                    advert_id=adv_id,
                    nm_bids=nm_bids,
                )
            ]
        )
        await self._promotion_manager.patch_adv_v1_bids(body)

    async def _resolve_shelf_bid_placement(
        self, adv_id: int
    ) -> PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement:
        """Placement для PATCH /api/advert/v1/bids (auto shelf control).

        Правила WB (``GET /api/advert/v2/adverts`` → ``bid_type`` + ``settings.placements``):

        - ``unified`` (единая ставка, type 8): только ``combined``. Отдельные
          ``recommendations`` / ``search`` дают 400 «invalid target type recom/search».
        - ``manual`` + только рекомендации (полочная auto): ``recommendations``.
        - ``manual`` + только поиск: ``search``.
        - ``manual`` + обе зоны: ``recommendations`` (control управляет полкой).
        """
        fallback = PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.RECOMMENDATIONS
        campaigns = await self._promotion_manager.get_adverts_v2_by_ids([int(adv_id)])
        if not campaigns:
            logger.warning(
                "shelf_bid_placement_fallback adv_id=%s no v2/adverts row, using %s",
                adv_id,
                fallback.value,
            )
            return fallback

        campaign = campaigns[0]
        bid_type = (getattr(campaign, "bid_type", None) or "").lower()
        if bid_type == "unified":
            return PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.COMBINED

        placements = campaign.settings.placements
        has_recom = bool(placements.recommendations)
        has_search = bool(placements.search)

        if has_recom and not has_search:
            return PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.RECOMMENDATIONS
        if has_search and not has_recom:
            return PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.SEARCH
        if has_recom:
            return PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.RECOMMENDATIONS

        logger.warning(
            "shelf_bid_placement_no_zones adv_id=%s bid_type=%s, using %s",
            adv_id,
            bid_type or "?",
            fallback.value,
        )
        return fallback

    async def patch_auto_adv_bids_kopecks(
        self, adv_id: int, nm_bid_kopecks: dict[int, int]
    ) -> None:
        """PATCH /api/advert/v1/bids: ``nm_bid_kopecks`` уже в копейках (control ``bid_minor``).

        Placement выбирается в ``_resolve_shelf_bid_placement``: ``unified`` → ``combined``;
        ``manual`` полочная → ``recommendations``; search-only → ``search``.
        """
        if not nm_bid_kopecks:
            return None
        placement = await self._resolve_shelf_bid_placement(adv_id)
        nm_bids = [
            PatchApiAdvertV1BidsBodyBidsItemNmBidsItem(
                nm_id=int(nm_id),
                bid_kopecks=int(kopecks),
                placement=placement,
            )
            for nm_id, kopecks in nm_bid_kopecks.items()
        ]
        body = PatchApiAdvertV1BidsBody(
            bids=[
                PatchApiAdvertV1BidsBodyBidsItem(
                    advert_id=int(adv_id),
                    nm_bids=nm_bids,
                )
            ]
        )
        await self._promotion_manager.patch_adv_v1_bids(body)
        return None

    async def get_campaign_budget(self, adv_id: int) -> "CampaignBudgetInfo":
        return await self._promotion_manager.get_campaign_budget(adv_id)

    async def top_up_budget(
        self,
        adv_id: int,
        amount: int,
        balance_type: str,
        return_total: bool = True,
        cashback_sum: int | None = None,
        cashback_percent: int | None = None,
    ) -> "BudgetTopUpResult":
        return await self._promotion_manager.top_up_budget(
            adv_id=adv_id,
            amount=amount,
            balance_type=balance_type,
            return_total=return_total,
            cashback_sum=cashback_sum,
            cashback_percent=cashback_percent,
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

    async def rename_campaign(self, advert_id: int, new_name: str) -> None:
        """Переименовать рекламную кампанию по её ID."""
        await self._promotion_manager.rename_campaign(advert_id, new_name)

    async def rename_campaign_by_type(
        self, complex_adv: ComplexAdv, adv_type: AdvType, new_name: str
    ) -> None:
        """Переименовать кампанию заданного типа (авто или аукцион)."""
        adv_id = complex_adv.get_adv_id_by_type(adv_type)
        await self.rename_campaign(adv_id, new_name)

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
