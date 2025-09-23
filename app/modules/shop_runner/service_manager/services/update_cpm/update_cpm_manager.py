import asyncio
import logging
from asyncio import TaskGroup
from typing import Awaitable, Dict, List, Optional

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater import data_manager
from app.modules.wb_keywords_parser import parser
from app.shared.application.dto.update_bids_in_advs.update_bids_in_search_adv_dto import (
    UpdateBidsInSearchAdvDTO,
)
from app.shared.application.dto.update_bids_in_advs.update_bids_search_adv_ids_batch import (
    UpdateBidsSearchAdvInShopBatch,
    UpdateBidForNmidTask,
)
from .bid_calculator import BidCalculator, BidCalculationParams
from .bid_orchestrator import BidUpdateOrchestrator
from .wb_api_managers import WBApiDataGetter, WBApiCpmUpdater

logger = logging.getLogger(__name__)


class UpdateCPMManager:
    _DEFAULT_BIDDER_STEP = 2

    def __init__(self, shop_id: str, promotion_adapter=None) -> None:
        self._shop_id = shop_id
        # Внедряем адаптер (через DI или напрямую), затем оборачиваем тонкими менеджерами
        if promotion_adapter is None:
            # Отложенная инициализация потребует внешней передачи адаптера в реальном рантайме
            raise RuntimeError("Promotion adapter must be provided to UpdateCPMManager")
        self._data_getter = WBApiDataGetter(promotion_adapter)
        self._cpm_updater = WBApiCpmUpdater(promotion_adapter)

    async def update_cpms_in_search_advs(
            self, update_bids_in_search_adv_dtos: List[UpdateBidsInSearchAdvDTO]
    ) -> None:
        if not update_bids_in_search_adv_dtos:
            return None
        update_batch = self.__get_update_batch(update_bids_in_search_adv_dtos)
        # Запускаем сеттеры и оркестратор в одном TaskGroup для централизованной отмены
        async with TaskGroup() as tg:
            # Планировщик корутин-сеттеров
            for fut, setter_coro in update_batch.futures_to_coros:
                tg.create_task(setter_coro)
            # Оркестратор
            orchestrator = BidUpdateOrchestrator(self._shop_id, self._cpm_updater)
            tg.create_task(orchestrator.process_updates(update_batch))

    async def __get_best_keyword(
            self, keywords_coro: Awaitable[List[CalculatedKeyword]]
    ) -> Optional[CalculatedKeyword]:
        keywords: List[CalculatedKeyword] = await keywords_coro
        best_keyword = data_manager.get_best_keyword(keywords)
        if not best_keyword:
            logger.debug("skip: no best keyword")
            return None
        return best_keyword

    async def _get_new_bid(
            self,
            *,
            adv_id: int,
            nmid: int,
            max_bid: int,
            best_keyword_task: asyncio.Future[Optional[CalculatedKeyword]],
            bidder_step: Optional[int],
            target_position: Optional[int],
            min_bids_map_task: asyncio.Future[Dict[int, int]],
            current_bids_map_task: asyncio.Future[Dict[int, int]],
    ) -> Optional[int]:
        from app.utils.redis_manager import get_keyword_position

        # 1) Лучший ключ
        best_keyword = await best_keyword_task
        if not best_keyword:
            logger.debug("skip: no best keyword (None)", extra={"adv_id": adv_id, "nmid": nmid})
            return None

        # 2) Карты ставок
        min_map = await min_bids_map_task
        curr_map = await current_bids_map_task

        # 3) Текущая/минимальная ставка
        min_bid = int(min_map.get(nmid, 0))
        current_bid = int(curr_map.get(nmid, 0))
        if current_bid == 0:
            logger.debug(
                "current bid not found, using 0",
                extra={"adv_id": adv_id, "nmid": nmid},
            )

        # 4) Позиция из Redis
        # Перед чтением позиции инициируем парсер для обновления позиции в Redis
        try:
            await parser.add_wb_positions(best_keyword.text, {nmid}, delay=0.1)
        except Exception as e:
            logger.debug(
                "parser add_wb_positions failed or skipped",
                extra={"adv_id": adv_id, "nmid": nmid, "error": str(e)},
            )
        pos = await get_keyword_position(best_keyword.text, int(nmid))
        if not pos or pos.position in (None, 0):
            logger.debug(
                "skip: no applicable position",
                extra={"adv_id": adv_id, "nmid": nmid},
            )
            return None

        # 5) Расчет
        params = BidCalculationParams(
            current_bid=int(current_bid),
            min_bid=int(min_bid),
            max_bid=int(max_bid),
            current_position=int(pos.position),
            target_position=int(target_position or 5),
            bidder_step=int(bidder_step or self._DEFAULT_BIDDER_STEP),
        )
        try:
            new_bid = BidCalculator().calculate_new_bid(params)
        except Exception as e:
            logger.critical(f"logic error: {e}")
            raise

        if new_bid is None or int(new_bid) == int(current_bid):
            logger.debug(
                "skip: new bid is None or unchanged",
                extra={"adv_id": adv_id, "nmid": nmid},
            )
            return None
        return int(new_bid)

    def __get_update_batch(
            self, update_bids_in_search_adv_dtos: List[UpdateBidsInSearchAdvDTO]
    ) -> UpdateBidsSearchAdvInShopBatch:
        update_batch = UpdateBidsSearchAdvInShopBatch(self._shop_id)
        futures_to_coros = []  # list[(future, coro)]

        for dto in update_bids_in_search_adv_dtos:
            adv_id = int(dto.adv_id)
            nmids = [int(x) for x in dto.nmids]
            max_bid = int(dto.max_cpm_bid)
            bidder_step = dto.bidder_step
            target_position = getattr(dto, "target_place", None)

            # Best keyword future
            best_keyword_future: asyncio.Future[Optional[CalculatedKeyword]] = asyncio.Future()

            async def best_keyword_setter(coro=dto.calculated_keywords_coro, fut=best_keyword_future):
                try:
                    result = await self.__get_best_keyword(coro)
                    if not fut.done():
                        fut.set_result(result)
                except Exception as e:
                    if not fut.done():
                        fut.set_exception(e)

            futures_to_coros.append((best_keyword_future, best_keyword_setter()))

            # Min bids map future
            min_bids_future: asyncio.Future[Dict[int, int]] = asyncio.Future()

            async def min_bids_setter(adv_id=adv_id, nmids=nmids, fut=min_bids_future):
                try:
                    result = await self._data_getter.get_min_bid_for_nmids(
                        self._shop_id, adv_id=adv_id, nmids=nmids
                    )
                    if not fut.done():
                        fut.set_result(result)
                except Exception as e:
                    if not fut.done():
                        fut.set_exception(e)

            futures_to_coros.append((min_bids_future, min_bids_setter()))

            # Current bids map future
            current_bids_future: asyncio.Future[Dict[int, int]] = asyncio.Future()

            async def current_bids_setter(adv_id=adv_id, nmids=nmids, fut=current_bids_future):
                try:
                    result = await self._data_getter.get_current_bids(
                        self._shop_id, adv_id=adv_id, nmids=nmids
                    )
                    if not fut.done():
                        fut.set_result(result)
                except Exception as e:
                    if not fut.done():
                        fut.set_exception(e)

            futures_to_coros.append((current_bids_future, current_bids_setter()))

            # Per nmid new bid futures
            for nmid in nmids:
                new_bid_future: asyncio.Future[Optional[int]] = asyncio.Future()

                async def new_bid_setter(
                        adv_id=adv_id,
                        nmid=nmid,
                        max_bid=max_bid,
                        best_keyword_future=best_keyword_future,
                        bidder_step=bidder_step,
                        target_position=target_position,
                        min_bids_future=min_bids_future,
                        current_bids_future=current_bids_future,
                        fut=new_bid_future,
                ):
                    try:
                        result = await self._get_new_bid(
                            adv_id=adv_id,
                            nmid=nmid,
                            max_bid=max_bid,
                            best_keyword_task=best_keyword_future,
                            bidder_step=bidder_step,
                            target_position=target_position,
                            min_bids_map_task=min_bids_future,
                            current_bids_map_task=current_bids_future,
                        )
                        if not fut.done():
                            fut.set_result(result)
                    except Exception as e:
                        if not fut.done():
                            fut.set_exception(e)

                futures_to_coros.append((new_bid_future, new_bid_setter()))
                update_batch.add_task(UpdateBidForNmidTask(adv_id, nmid, new_bid_future))

        # прикрепляем список сеттеров к batch для последующего запуска
        update_batch.futures_to_coros = futures_to_coros  # type: ignore[attr-defined]
        return update_batch
