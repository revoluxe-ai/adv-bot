import asyncio
import logging
from typing import Optional, Dict, List, Awaitable, Any, Union

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.common_slaves.wildberries.models import WBItemPosition
from app.modules.wb_adv_updater.data_manager import get_best_keyword as pick_best_keyword
from app.shared.application.commands.search_adv_bid_update.send_to_queue_for_update_nmid_bid_command import \
    SendToQueueForUpdateNmidBidCommand
from .bid_calculator import BidCalculator, BidCalculationParams

logger = logging.getLogger(__name__)


class NewCpmBidManager:
    _DEFAULT_BIDDER_STEP = 2

    def _to_future(self, obj: Union[asyncio.Future, Awaitable[Any]]) -> asyncio.Future:
        """Возвращает Task/Future: корутину оборачивает в Task, Future возвращает как есть."""
        if asyncio.iscoroutine(obj):
            return asyncio.create_task(obj)
        if isinstance(obj, asyncio.Future):
            return obj
        raise TypeError("Expected coroutine or Future")

    async def _cancel_all(self, tasks: Dict[str, asyncio.Future]) -> None:
        for t in tasks.values():
            if not t.done():
                t.cancel()
        if tasks:
            await asyncio.gather(*tasks.values(), return_exceptions=True)

    async def get_new_cmp_bid(
            self,
            command: SendToQueueForUpdateNmidBidCommand,
    ) -> int | None:
        """
        Получает новую CPM-ставку, обрабатывая результаты Futures по мере готовности.
        Не использует TaskGroup для уже созданных Future.
        """
        tasks: Dict[str, asyncio.Future] = {
            "best_keyword": self._to_future(command.best_keyword_future),
            "min_bids_map": self._to_future(command.min_bids_future),
            "current_bids_map": self._to_future(command.current_bids_future),
            "current_positions": self._to_future(command.current_positions_future),
        }
        name_by_task: Dict[asyncio.Future, str] = {t: name for name, t in tasks.items()}
        results: Dict[str, Any] = {}
        nmid = command.nmid

        try:
            for fut in asyncio.as_completed(list(tasks.values())):
                task = fut
                name = name_by_task[task]
                try:
                    res = await task
                except asyncio.CancelledError:
                    logger.debug("Task was cancelled", extra={"task": name, "nmid": nmid})
                    await self._cancel_all(tasks)
                    return None
                except Exception as e:
                    logger.error(f"Task failed: {name}: {e}", extra={"nmid": nmid})
                    await self._cancel_all(tasks)
                    return None

                if name == "best_keyword":
                    best_kw = await self.__get_best_keyword(res)
                    if not best_kw:
                        logger.debug("skip: no best keyword (None)", extra={"nmid": nmid})
                        await self._cancel_all(tasks)
                        return None
                    results[name] = best_kw
                elif name == "min_bids_map":
                    if not res or nmid not in res or not res.get(nmid):
                        logger.debug("skip: min_bid not found or invalid", extra={"nmid": nmid})
                        await self._cancel_all(tasks)
                        return None
                    results[name] = res
                elif name == "current_bids_map":
                    if not res or nmid not in res or not res.get(nmid):
                        logger.debug("skip: current_bid not found or invalid", extra={"nmid": nmid})
                        await self._cancel_all(tasks)
                        return None
                    results[name] = res
                elif name == "current_positions":
                    if not res or nmid not in res:
                        logger.debug("skip: position not found for nmid", extra={"nmid": nmid})
                        await self._cancel_all(tasks)
                        return None
                    pos = res.get(nmid)
                    if not pos or not hasattr(pos, "position") or pos.position in (None, 0):
                        logger.debug(
                            "skip: invalid position (None or 0)",
                            extra={"nmid": nmid, "position": getattr(pos, "position", None)},
                        )
                        await self._cancel_all(tasks)
                        return None
                    results[name] = res

            if not all(k in results for k in tasks.keys()):
                logger.debug("Not all results received", extra={"nmid": nmid})
                return None

            return await self._process_results(command, results)

        finally:
            await self._cancel_all(tasks)

    async def _process_results(
            self,
            command: SendToQueueForUpdateNmidBidCommand,
            results: Dict[str, Any],
    ) -> int | None:
        _best_keyword: CalculatedKeyword = results["best_keyword"]
        min_bids_map = results["min_bids_map"]
        current_bids_map = results["current_bids_map"]
        current_positions_map = results["current_positions"]

        nmid = command.nmid
        min_bid = min_bids_map.get(nmid)
        current_bid = current_bids_map.get(nmid)
        pos: WBItemPosition = current_positions_map.get(nmid)
        if not any([min_bid, current_bid, pos, pos.position]):
            return None

        params = BidCalculationParams(
            current_bid=current_bid,
            min_bid=min_bid,
            max_bid=command.max_cpm_bid,
            current_position=pos.position,
            target_position=command.target_position,
            bidder_step=command.bidder_step,
        )

        try:
            new_bid = BidCalculator().calculate_new_bid(params)
        except Exception as e:
            logger.critical(f"logic error: {e}")
            raise

        if new_bid is None or int(new_bid) == int(current_bid):
            logger.debug("skip: new bid is None or unchanged", extra={"nmid": nmid})
            return None

        return int(new_bid)

    async def get_new_cpm_bid(
            self,
            command: SendToQueueForUpdateNmidBidCommand,
    ) -> int | None:
        return await self.get_new_cmp_bid(command)

    async def __get_best_keyword(
            self,
            keywords: Optional[List[CalculatedKeyword]],
    ) -> Optional[CalculatedKeyword]:
        try:
            if not keywords:
                return None
            best = pick_best_keyword(keywords)
            return best or None
        except Exception as e:
            logger.error(f"Failed to get best keyword: {e}")
            return None
