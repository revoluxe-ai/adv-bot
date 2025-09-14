import logging
from asyncio import Task, TaskGroup
from typing import Awaitable

from app.client_bot.user_interface.views.messages import ApiForrbidenError
from app.modules.common_slaves.wildberries.data_classes.adv import Adv
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from app.modules.wb_adv_updater import data_manager
from app.modules.wb_keywords_parser import parser
from app.shared.application.dto.update_bids_in_advs.update_bids_in_search_adv_dto import (
    UpdateBidsInSearchAdvDTO,
)
from app.shared.application.dto.update_bids_in_advs.update_bids_search_adv_ids_batch import (
    UpdateBidsSearchAdvInShopBatch,
    UpdateBidForNmidTask,
)
from .bid_orchestrator import BidUpdateOrchestrator
from .redis_manager import RedisManager

logger = logging.getLogger(__name__)


class UpdateCPMManager:
    _DEFAULT_BIDDER_STEP = 2

    def __init__(self, access: WBCabinetAccess) -> None:

        self._shop_id = access.shop_id
        self._redis_manager = RedisManager()
        # Создаем WB API через фабрику с DI в контексте WBAccessContext

        # Контекст гарантирует, что фабрика токен-менеджеров увидит корректный access

        # Сохраним доступ для асинхронных вызовов
        self._access = access

    async def update_cpms_in_search_advs(
        self,
        update_bids_in_search_adv_dtos: list[UpdateBidsInSearchAdvDTO],
    ) -> None:
        if not update_bids_in_search_adv_dtos:
            return None
        async with TaskGroup() as tg:
            update_batch = self.__get_update_batch(
                tg, update_bids_in_search_adv_dtos
            )
            orchestrator = BidUpdateOrchestrator(self._wb_api)
            # Запускаем в асинхронном контексте доступа к WB
            await orchestrator.process_updates(update_batch)

    async def __get_best_keyword(
        self, keywords_coro: Awaitable[list[CalculatedKeyword]]
    ) -> CalculatedKeyword | None:
        keywords: list[CalculatedKeyword] = await keywords_coro
        best_keyword = data_manager.get_best_keyword(keywords)
        if not best_keyword:
            return None
        else:
            return best_keyword

    async def __get_min_cpms_from_wb(
        self, adv_id: int, nmids: list[int]
    ) -> dict[int, int]:
        min_cpms: dict[int, int] = await self._wb_api.get_min_cpms_for_adv_setting(
            adv_id, nmids
        )
        return min_cpms

    async def _get_new_bid(
        self,
        *,
        search_adv_id: int,
        max_bid: int,
        best_keyword: Task[CalculatedKeyword | None],
        bidder_step: int | None = None,
        max_position: int | None = None,
        min_bid_in_adv: Task[dict[int, int]],
    ) -> int | None:
        best_keyword: CalculatedKeyword | None = await best_keyword_task
        if not best_keyword:
            return None
        max_cpm: int = max_bid
        step = bidder_step or self._DEFAULT_BIDDER_STEP
        if not best_keyword:
            return None
        text = best_keyword.text
        try:
            current_bids_map: dict[int, int] = (
                await self.__get_current_cpm_bids_from_wb_api(adv_id)
            )
        except ApiForrbidenError as e:
            raise e
        await parser.add_wb_positions(text, {nmid}, delay=0.1)
        wb_position = await self._redis_manager.get_keyword_position(text, nmid)

        if not wb_position or not wb_position.promo_position:
            logger.error("Позиция ключа не найдена или нет промопозиции")
            return None
        max_current_bid = max(current_cpm_from_wb_api, max_cpm)
        promo_position = wb_position.promo_position
        if promo_position <= max_position or promo_position == 1:
            new_cpm: int = max_current_bid - step
        else:
            new_cpm = max_current_bid + step

        await min_bid_in_adv
        new_cpm = max(min(new_cpm, max_cpm), 0)
        if new_cpm == current_cpm_from_wb_api:
            return None
        return new_cpm

    async def __get_current_cpm_bid_from_wb_api(self, adv_id: int) -> int:
        adv: list[Adv] = await self._wb_api.get_advs([adv_id])
        bid = adv[0].cpm
        return bid

    def _get_cpm_update_data(self, adv_setting: AdvSetting, new_cpm: int) -> dict:
        """Подготовить данные для обновления ставок."""
        return {
            "adv_setting": adv_setting,
            "new_cpm": new_cpm,
        }

    def __get_update_batch(
        self,
        tg: TaskGroup,
        update_bids_in_search_adv_dtos: list[UpdateBidsInSearchAdvDTO],
    ) -> UpdateBidsSearchAdvInShopBatch:

        update_batch = UpdateBidsSearchAdvInShopBatch(self._shop_id)
        for dto in update_bids_in_search_adv_dtos:
            keywords_coro = dto.calculated_keywords_coro
            best_keyword_task: Task[CalculatedKeyword | None] = tg.create_task(
                self.__get_best_keyword(keywords_coro)
            )
            adv_id = dto.adv_id
            nmids = dto.nmids
            min_bid_in_adv_task: Task[dict[int, int]] = tg.create_task(
                self.__get_min_cpms_from_wb(adv_id, nmids)
            )
            max_bid = dto.max_cpm_bid
            for nmid in nmids:
                new_bid_coro = self._get_new_bid(
                    adv_id=adv_id,
                    nmid=nmid,
                    max_bid=max_bid,
                    best_keyword_task=best_keyword_task,
                    bidder_step=dto.bidder_step,
                    max_position=dto.target_place,
                    min_bid_in_adv=min_bid_in_adv_task,
                )
                # Schedule the coroutine to avoid "coroutine was never awaited" warnings
                new_bid_coro_task = tg.create_task(new_bid_coro)  # type: ignore[arg-type]
                update_task = UpdateBidForNmidTask(adv_id, nmid, new_bid_coro_task)
                update_batch.add_task(update_task)
