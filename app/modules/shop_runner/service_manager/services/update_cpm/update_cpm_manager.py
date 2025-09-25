import asyncio
import logging
from asyncio import Task, TaskGroup
from collections.abc import Awaitable

from app.client_bot.user_interface.views.messages import ApiForrbidenError
from app.modules.common_slaves.wildberries.data_classes.adv import Adv
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater import data_manager
from app.modules.wb_keywords_parser import parser
from app.shared.application.dto.update_bids_in_advs.update_bids_in_search_adv_dto import (
    UpdateBidsInSearchAdvDTO,
)
from app.shared.application.dto.update_bids_in_advs.update_bids_search_adv_ids_batch import (
    UpdateBidForNmidTask,
    UpdateBidsSearchAdvInShopBatch,
)

from .bid_orchestrator import BidUpdateOrchestrator
from .redis_manager import RedisManager

logger = logging.getLogger(__name__)


class UpdateCPMManager:
    _DEFAULT_BIDDER_STEP = 2

    def __init__(self, shop_id: str) -> None:
        self._shop_id = shop_id
        self._wb_data_getter = WBApiDataGetter()
        self._wb_cpm_updater = WBApiCpmUpdater()
        self._stop_event = asyncio.Event()
        queue: asyncio.Queue[BidUpdateForNmidCommand] = asyncio.Queue()
        self._update_bid_orchestrator = UpdateBidOrchestrator(
            queue=queue,
            stop_event=self._stop_event,
            shop_id=self._shop_id,
            wb_api_cpm_updater=self._wb_cpm_updater,
        )
        loop = asyncio.get_running_loop()
        self._min_bids_for_adv_from_future_getter = MinBidsForAdvGetter(loop)
        self._best_keyword_from_future_getter = BestKeywordFromFutureGetter(loop)
        self._current_positions_for_adv_from_future_getter = CurrentPositionsForAdvGetter(loop)
        self._current_bids_for_adv_from_future_getter = CurrentBidsForAdvGetter(loop)

    async def __get_best_keyword(
        self, keywords_coro: Awaitable[List[CalculatedKeyword]]
    ) -> Optional[CalculatedKeyword]:
        keywords: List[CalculatedKeyword] = await keywords_coro
        best_keyword = data_manager.get_best_keyword(keywords)
        if not best_keyword:
            logger.debug("skip: no best keyword")
            return None
        return best_keyword

    async def update_cpms_in_search_advs(
        self, adv_settings_and_keywords_coro: list[tuple[AdvSetting, Awaitable[list[CalculatedKeyword]]]]
    ) -> None:
        if not adv_settings_and_keywords_coro:
            return None

        send_update_commands_coros: list[Coroutine[Any, Any, None]] = []
        for adv, keywords_coro in adv_settings_and_keywords_coro:
            search_adv_id = adv.search_adv_id
            target_place = adv.max_place
            max_bid = adv.max_cpm
            nmids = adv.nmids
            if not any([search_adv_id, nmids, max_bid, target_place]):
                logger.debug("skip: empty adv params", extra={"adv_id": adv.adv_id})
                continue
            best_keyword_future: asyncio.Future[list[CalculatedKeyword]] = (
                self._best_keyword_from_future_getter._get_future(keywords_coro)
            )
            min_bids_future: Future[dict[int, int]] = self._min_bids_for_adv_from_future_getter._get_future(
                search_adv_id, nmids
            )
            current_positions_future: Future[dict[int, int]] = (
                self._current_positions_for_adv_from_future_getter.get_future(adv, best_keyword_future)
            )
            max_bid = adv.max_cpm

            current_bids_future: Future[dict[int, int]] = self._current_bids_for_adv_from_future_getter._get_future(
                nmids, best_keyword_future
            )

            bidder_step = adv.bidder_step or self._DEFAULT_BIDDER_STEP
            for nmid in nmids:
                cmd = SendToQueueForUpdateNmidBidCommand(
                    shop_id=self._shop_id,
                    adv_id=search_adv_id,
                    nmid=nmid,
                    max_cpm_bid=max_bid,
                    target_position=target_place,
                    bidder_step=bidder_step,
                    best_keyword_future=best_keyword_future,
                    min_bids_future=min_bids_future,
                    current_positions_future=current_positions_future,
                    current_bids_future=current_bids_future,
                )
                send_update_commands_coros.append(self._update_bid_orchestrator.send_update_command_to_queue(cmd))

        update_batch_task = asyncio.create_task(self._update_bid_orchestrator.update_batch())
        update_bids_by_batch_task = asyncio.create_task(self._update_bid_orchestrator.update_bids_for_batch())

        async with asyncio.TaskGroup() as tg:
            for coro in send_update_commands_coros:
                tg.create_task(coro)
                tg.create_task(self._best_keyword_from_future_getter.run())
                tg.create_task(self._min_bids_for_adv_from_future_getter.run())
                tg.create_task(self._current_positions_for_adv_from_future_getter.run())
                tg.create_task(self._current_bids_for_adv_from_future_getter.run())

        self._stop_event.set()

        await asyncio.gather(update_batch_task, update_bids_by_batch_task)
        return None
