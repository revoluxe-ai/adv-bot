import logging
from collections.abc import Awaitable, Callable, Iterator
from typing import Any, cast

from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.dto import NormqueryBidDTO
from app.core.mp.wb.dto.adv_min_bids import AdvMinNmidsBids
from app.modules.predict_keywords_target_place import PredictKeywordsTargetPlace
from app.modules.predict_keywords_target_place.clickhouse_manager.dto import BidPosition
from app.modules.predict_keywords_target_place.di import PredictKeywordsTargetPlaceContainer
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus
from .dto.bidder_update_data import BidderUpdateData
from .mappers.adv_id_item_map import AdvIdItemCalculateData
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_keyword_bidder_status_manager import RedisKeywordBidderStatusManager
from app.modules.cluster_bids_redis import (
    ClusterBidKey,
    RedisClusterBidsManager,
    RedisClusterBidsTimestampManager,
)
from app.modules.cluster_bids_redis.redis_cluster_bids_manager import ClusterBidEntry
from .wb_manager import WBManager
from app.modules.plan_fact.provider import PlanFactProvider
from ...old_modules.setting_auto_updater.data_classes import FactData, PlanData
from ...wb_shop_data_manager.dto.complex_adv import ComplexAdv
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.\
    new_bids_calculator.update_bids_command import DirectEnum, UpdateBidsCommand, NewBid
from .new_bids_calculator.calculation_input import CalculationInput
from .dto.calculate_data import BidderCalculateData

from app.modules.shop_runner.tasks_manager.tasks_manager import run_tasks

# TODO: Внедрить в ректрай WB Api декораторы всплески


logger = logging.getLogger(__name__)


def _max_workers_for(handler_count: int, cap: int) -> int:
    return max(1, min(handler_count, cap))

"""
TODO: WB Стал передавать информацию о Depricated методах прям в методах,

2025-12-10 22:32:56 - DEBUG - app.core.wb_api.http_request:156 - Запрос к https://seller-analytics-api.wildberries.ru/api/v2/nm-report/detail/history выполнен. Статус: 429, ответ: {
 "title": "too many requests",
 "detail": "This method is deprecated. It will be removed on 23 December. Link: https://dev.wildberries.ru/release-notes?id=355",
 "code": "461a0b83d6bd 2950e93b5fda",
 "requestId": "71f1324326d68dbcc8c87fc6957fd3e6",
 "origin": "s2sauth-ca",
 "status": 429,
 "statusText": "Too Many Requests",
 "timestamp": "2025-12-10T19:32:58Z"
}


"""


class UpdateClusterBidsManager:
    def __init__(
        self,
        wb_manager: WBManager,
        redis_keyword_bidder_status_manager: RedisKeywordBidderStatusManager,
        redis_cluster_bids_manager: RedisClusterBidsManager,
        redis_cluster_bids_timestamp_manager: RedisClusterBidsTimestampManager,
    ):
        self._wb_manager = wb_manager
        self._redis_keyword_bidder_status_manager = redis_keyword_bidder_status_manager
        self._redis_cluster_bids_manager = redis_cluster_bids_manager
        self._redis_cluster_bids_timestamp_manager: RedisClusterBidsTimestampManager = (
            redis_cluster_bids_timestamp_manager
        )


    async def _get_local_data(self, advs: list[ComplexAdv]) -> set[AdvIdItemCalculateData]:
        return await self._get_maps(advs)

    async def _get_data_from_wb_api(
        self,
        advs: list[ComplexAdv],
        map_datas: set[AdvIdItemCalculateData],
    ) -> BidderUpdateData:
        return await self._get_bidder_update_data(advs, map_datas)

    async def _get_calculate_data(self, advs: list[ComplexAdv]) -> BidderCalculateData:
        local_data: set[AdvIdItemCalculateData] = await self._get_local_data(advs)
        remote_data: BidderUpdateData = await self._get_data_from_wb_api(advs, local_data)
        predict_bids_data: dict[int, dict[int, dict[str, dict[int, int]]] | None] = (
            await self._get_predict_bids_data(advs, remote_data.min_bids.search)
        )

        return BidderCalculateData(
            data_from_local=local_data,
            data_from_wb_api=remote_data,
            predict_bids_data=predict_bids_data,
        )

    async def update_cluster_bids(self, advs: list[ComplexAdv]) -> None:
         calculate_data: BidderCalculateData = await self._get_calculate_data(advs)
         calculation_inputs: list[CalculationInput] = await self._get_calculation_inputs(calculate_data)
         new_bids_command: UpdateBidsCommand = self._get_bids_command(calculation_inputs)
         await self._apply_command(new_bids_command)
         for adv in advs: # TODO: Тут накостылил, чтобы быстрее в прод выложить
             await self._redis_cluster_bids_timestamp_manager.set(adv)

    async def _get_bidder_update_data(
        self,
        advs: list[ComplexAdv],
        map_datas: set[AdvIdItemCalculateData],
    ) -> BidderUpdateData:
        async def _get_cluster_bids() -> list[NormqueryBidDTO]:
            return await self._get_cluster_bids_for_maps(map_datas, advs)

        async def _get_min_bids() -> AdvMinNmidsBids:
            return await self._wb_manager.get_min_bids(advs, cache_possible=True)

        async def _get_fact_data() -> dict[int, FactData]:
            return await self._get_fact_datas(advs)

        handlers: list[Callable[[], Awaitable[Any]]] = [
            _get_cluster_bids,
            _get_min_bids,
            _get_fact_data,
        ]

        results = await run_tasks(
            handlers,
            max_workers=3,
            return_exceptions=False,
        )
        current_bids = cast(list[NormqueryBidDTO], results[0])
        min_bids = cast(AdvMinNmidsBids, results[1])
        fact_data = cast(dict[int, FactData], results[2])
        plan_data = self._get_plan_data(advs)

        return BidderUpdateData(
            advs=advs,
            cluster_bids=current_bids,
            min_bids=min_bids,
            fact_datas=fact_data,
            plan_datas=plan_data,
        )

    async def _get_cluster_bids_for_maps(
        self,
        map_datas: set[AdvIdItemCalculateData],
        advs: list[ComplexAdv],
    ) -> list[NormqueryBidDTO]:
        if not map_datas:
            return []
        keys: list[ClusterBidKey] = [
            ClusterBidKey(
                adv_id=data.adv_id,
                nmid=data.nmid,
                cluster=data.cluster,
            )
            for data in map_datas
        ]
        cached = await self._redis_cluster_bids_manager.get_bids(keys)
        total = len(keys)
        cached_count = len(cached)
        if cached_count:
            logger.debug(
                "Cluster bid cache HIT for %s/%s combinations", cached_count, total
            )
        missing_keys = [key for key in keys if key not in cached]
        bids_map: dict[ClusterBidKey, NormqueryBidDTO] = {
            key: NormqueryBidDTO(
                advert_id=key.adv_id,
                nm_id=key.nmid,
                norm_query=key.cluster,
                bid=value,
            )
            for key, value in cached.items()
        }
        if missing_keys:
            logger.debug(
                "Cluster bid cache MISS for %s/%s combinations",
                len(missing_keys),
                total,
            )
            missing_set = set(missing_keys)
            wb_bids = await self._wb_manager.get_current_bids(advs)
            for dto in wb_bids:
                key = ClusterBidKey(
                    adv_id=dto.advert_id,
                    nmid=dto.nm_id,
                    cluster=dto.norm_query,
                )
                if key in missing_set:
                    bids_map[key] = dto
            missing_after_api = [key for key in missing_set if key not in bids_map]
            if missing_after_api:
                logger.debug(
                    "WB API did not return bids for %s combinations",
                    len(missing_after_api),
                )
        return list(bids_map.values())

    async def _get_calculation_inputs(
        self, calculate_data: BidderCalculateData
    ) -> list[CalculationInput]:
        from .mappers import Mapper
        bidder_update_data = calculate_data.data_from_wb_api
        maps_data: set[AdvIdItemCalculateData] = calculate_data.data_from_local
        mapper = Mapper(bidder_update_data)
        bid_keys = [
            ClusterBidKey(
                adv_id=map_data.adv_id,
                nmid=map_data.nmid,
                cluster=map_data.cluster,
            )
            for map_data in maps_data
        ]
        cached_states = await self._redis_cluster_bids_manager.get_bid_states(bid_keys)
        inputs: list[CalculationInput] = []
        for map_data in maps_data:
            current_bid = mapper.get_current_bid(map_data)
            if current_bid is None:
                fallback_bid = map_data.current_cpm
                if fallback_bid is None:
                    logger.debug(
                        "Нет текущей ставки для adv_id: %s, nmid: %s, cluster: %s",
                        map_data.adv_id,
                        map_data.nmid,
                        map_data.cluster,
                    )
                    continue
                current_bid = fallback_bid
            current_position = mapper.get_current_position(map_data)
            target_position: int = mapper.get_target_position(map_data)
            adv_id = map_data.adv_id
            nmid = map_data.nmid
            state_key = ClusterBidKey(
                adv_id=adv_id,
                nmid=nmid,
                cluster=map_data.cluster,
            )
            prev_state = cached_states.get(state_key)
            prev_step: int | None = prev_state.step if prev_state else None
            prev_direct: DirectEnum | None = None
            if prev_state and prev_state.direct is not None:
                try:
                    prev_direct = DirectEnum(prev_state.direct)
                except ValueError:
                    prev_direct = None
            predict_bids_data_for_adv = calculate_data.predict_bids_data.get(adv_id)
            predict_target_bids = (
                predict_bids_data_for_adv.get(nmid)
                if isinstance(predict_bids_data_for_adv, dict)
                else None
            )
            calculate_input = CalculationInput(
                adv_id=adv_id ,
                nmid=nmid,
                current_bid=current_bid,
                current_position=current_position,
                target_position=target_position,
                cluster=map_data.cluster,
                step=map_data.step,
                min_bid=mapper.get_min_bid(map_data),
                max_bid=map_data.max_cpm,
                predict_target_bids=predict_target_bids,
                prev_direct=prev_direct,
                prev_step=prev_step,
            )
            inputs.append(calculate_input)
        return inputs

    @staticmethod
    async def __get_calculate_data(adv: ComplexAdv) -> set[AdvIdItemCalculateData]:
        from app.modules.shop_runner.service_manager.services.minus_phrase_manager\
            .click_house_manager.click_house_manager import ClickHouseManager
        search_adv_id = adv.auction_adv_id
        if search_adv_id is None:
            logger.warning('Нет поисковой компании у комплекса: %s', adv.adv_id)
            return set()
        ch_manager = ClickHouseManager()
        texts_in_this_adv = set(await ch_manager.get_cluster_texts_for_adv(search_adv_id))

        keywords: list[CalculatedKeyword] = await adv.get_keywords()
        keywords = [kw for kw in keywords if kw.status == KeywordStatus.GOOD]
        keywords = [kw for kw in keywords if kw.text in texts_in_this_adv]
        map_datas: set[AdvIdItemCalculateData] = set()
        for nmid in adv.nmids:
            for kw in keywords:
                kw_cpm = getattr(kw, "cpm", None)
                current_cpm = int(kw_cpm + 0.5) if kw_cpm is not None else None
                if adv.individual_keywords_target_place_mode and (keyword_target_place := kw.target_place):
                    target_position = keyword_target_place
                else:
                    target_position = adv.target_place
                map_data = AdvIdItemCalculateData(
                    adv_id=search_adv_id,
                    nmid=nmid,
                    cluster=kw.text,
                    current_position=kw.position,
                    max_cpm=adv.max_user_cpm,
                    target_position=target_position,
                    step=adv.bid_cpm_step,
                    current_cpm=current_cpm,
                )
                map_datas.add(map_data)
        return map_datas


    async def _get_maps(self, advs: list[ComplexAdv]) -> set[AdvIdItemCalculateData]:
        handlers: list[Callable[[], Awaitable[set[AdvIdItemCalculateData]]]] = [
            lambda adv_=adv: self.__get_calculate_data(adv_) for adv in advs
        ]
        results = await run_tasks(
            handlers,
            max_workers=_max_workers_for(len(handlers), cap=16),
        )
        datas: set[AdvIdItemCalculateData] = set()
        for result in results:
            if isinstance(result, BaseException):
                logger.error('Ошибка получения данных для расчета новой ставки: %s', result)
            elif result:
                datas.update(result)
        return datas

    async def _apply_command(self, update_bids_command: UpdateBidsCommand):
        handlers: list[Callable[[], Awaitable[Any]]] = [
            lambda: self._redis_keyword_bidder_status_manager.update_statuses(
                update_bids_command
            ),
            lambda: self._wb_manager.set_new_cluster_bids(update_bids_command),
        ]
        tasks = await run_tasks(
            handlers,
            max_workers=2,
            return_exceptions=True,
        )
        wb_error: BaseException | None = None
        for idx, result in enumerate(tasks):
            if isinstance(result, Exception):
                logger.error("Ошибка применения новых ставок: %s", result)
                if idx == 1:
                    wb_error = result
        if wb_error is None:
            try:
                entries = [
                    ClusterBidEntry(
                        adv_id=b.adv_id,
                        nmid=b.nmid,
                        cluster=b.cluster,
                        new_bid=b.new_bid,
                        step=b.step,
                        direct=b.direct.value,
                    )
                    for b in update_bids_command.new_bids
                ]
                await self._redis_cluster_bids_manager.remember_bids(entries)
            except Exception as error:  # noqa: BLE001
                logger.error("Не удалось сохранить ставки в Redis: %s", error)

    @staticmethod
    def _get_bids_command(calculation_inputs: list[CalculationInput]):
        from .new_bids_calculator import new_bid_calculate
        new_bids: list[NewBid] = []
        for input_dto in calculation_inputs:
            new_bid: NewBid | None = new_bid_calculate(input_dto)
            if new_bid:
                new_bids.append(new_bid)
        return UpdateBidsCommand(new_bids)

    async def _get_fact_datas(self, advs: list[ComplexAdv])-> dict[int, FactData]:
        handlers: list[Callable[[], Awaitable[FactData]]] = [
            lambda adv_=adv: self.__get_fact_data(adv_) for adv in advs
        ]
        results = await run_tasks(
            handlers,
            max_workers=_max_workers_for(len(handlers), cap=16),
            return_exceptions=True,
        )
        facts: list[FactData | None] = []
        for result in results:
            if isinstance(result, BaseException):
                logger.error('Ошибка получения факта: %s', result)
                facts.append(None)
            else:
                facts.append(result)
        rows: Iterator[tuple[ComplexAdv, FactData | None]] = zip(advs, facts)
        adv_to_fact_map: dict[int, FactData] = {}
        for adv, fact in rows:
            if fact is not None:
                adv_to_fact_map[adv.adv_id] = fact
        return adv_to_fact_map

    @staticmethod
    async def __get_fact_data(adv: ComplexAdv) -> FactData:
        keywords = await adv.get_keywords()
        provider = PlanFactProvider(adv.adv_setting)
        stat = await provider.get_stat_data(keywords)
        return await provider.get_fact_data(stat)


    @staticmethod
    def _get_plan_data(advs: list[ComplexAdv]) -> dict[int, PlanData]:
        plan_datas_map: dict[int, PlanData] = {}
        for adv in advs:
            plan = PlanFactProvider.get_plan_data(adv.adv_setting)
            if plan is not None:
                plan_datas_map[adv.adv_id] = plan

        return plan_datas_map


    @staticmethod
    async def _get_predict_bids_data(
                                     advs: list[ComplexAdv],
                                     auction_min_bids_by_nmid: dict[int, int]) \
        -> dict[int, (dict[int, dict[str, dict[int, int]]] | None)]:
        predict_keywords_target_manager_container = PredictKeywordsTargetPlaceContainer()
        predict_target_place_manager: PredictKeywordsTargetPlace = \
            predict_keywords_target_manager_container.predict_keywords_target_place_manager()
        adv_result: dict[int, (dict[int, dict[str, dict[int, int]]] | None)] = {}
        for adv in advs:
            search_adv_id = adv.auction_adv_id
            if search_adv_id is None:
                continue
            if adv.individual_keywords_target_place_mode is False:
                adv_result[search_adv_id] = None
                continue
            nmid_result = {}
            for nmid in adv.nmids:
                bid_positions_result:  dict[str, list[BidPosition]] = \
                    await predict_target_place_manager.get_bids_for_positions(nmid=nmid,
                                                                               min_bid=auction_min_bids_by_nmid[nmid])
                dict_result: dict[str, dict[int, int]] = {}
                for keyword_text, bid_positions in bid_positions_result.items():
                    bid_positions_dict = {pos.position: pos.bid for pos in bid_positions}
                    dict_result[keyword_text] = bid_positions_dict
                nmid_result[nmid] = dict_result
            adv_result[search_adv_id] = nmid_result

        return adv_result
