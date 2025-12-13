import asyncio
from collections.abc import Awaitable
import datetime

from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.dto import NormqueryBidDTO
from app.core.mp.wb.dto import AdvMinNmidsBids
from .dto.bidder_update_data import BidderUpdateData
from .mappers.adv_id_item_map import AdvIdItemCalculateData
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_keyword_bidder_status_manager import RedisKeywordBidderStatusManager
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_cluster_bids_manager import (
    RedisClusterBidsManager,
    ClusterBidKey,
)
from .wb_manager import WBManager
from ...old_modules.setting_auto_updater import AdvSettingAutoUpdater
from ...old_modules.setting_auto_updater.data_classes import FactData, PlanData
from ...wb_shop_data_manager.dto.complex_adv import ComplexAdv
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.\
    new_bids_calculator.update_bids_command import UpdateBidsCommand, NewBid
from .new_bids_calculator.calculation_input import CalculationInput
from .dto.calculate_data import BidderCalculateData
import logging
from typing import Iterator, Coroutine, Any
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_cluster_bids_timestamp_manager import RedisClusterBidsTimestampManager

# TODO: Внедрить в ректрай WB Api декораторы всплески


logger = logging.getLogger(__name__)

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
        self._redis_cluster_bids_timestamp_manager = redis_cluster_bids_timestamp_manager


    async def _get_local_data(self, advs: list[ComplexAdv]) -> set[AdvIdItemCalculateData]:
        return await self._get_maps(advs)

    async def _get_data_from_wb_api(
        self,
        advs: list[ComplexAdv],
        map_datas: set[AdvIdItemCalculateData],
    ) -> BidderUpdateData:
        return await self._get_bidder_update_data(advs, map_datas)

    async def _get_calculate_data(self, advs: list[ComplexAdv]) -> BidderCalculateData:
        local_data = await self._get_local_data(advs)
        remote_data = await self._get_data_from_wb_api(advs, local_data)
        return BidderCalculateData(
            data_from_local=local_data,
            data_from_wb_api=remote_data,
        )

    async def update_cluster_bids(self, advs: list[ComplexAdv]) -> None:
         calculate_data = await self._get_calculate_data(advs)
         calculation_inputs: set[CalculationInput] = self._get_calculation_inputs(calculate_data)
         new_bids_command: UpdateBidsCommand = self._get_bids_command(calculation_inputs)
         await self._apply_command(new_bids_command)
         await self._redis_cluster_bids_timestamp_manager.set(datetime.datetime.now())

    async def _get_bidder_update_data(
        self,
        advs: list[ComplexAdv],
        map_datas: set[AdvIdItemCalculateData],
    ) -> BidderUpdateData:
        cluster_bids_task = asyncio.create_task(
            self._get_cluster_bids_for_maps(map_datas, advs)
        )
        min_bids_task = asyncio.create_task(self._wb_manager.get_min_bids(advs))
        fact_datas_task = asyncio.create_task(self._get_fact_datas(advs))
        current_bids: list[NormqueryBidDTO]
        min_bids: AdvMinNmidsBids
        fact_data: dict[int, FactData]
        current_bids, min_bids, fact_data = await asyncio.gather(
            cluster_bids_task,
            min_bids_task,
            fact_datas_task,
        )
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

    @staticmethod
    def _get_calculation_inputs(calculate_data: BidderCalculateData) -> set[CalculationInput]:
        from .mappers import Mapper
        bidder_update_data = calculate_data.data_from_wb_api
        maps_data: set[AdvIdItemCalculateData] = calculate_data.data_from_local
        mapper = Mapper(bidder_update_data)
        inputs: set[CalculationInput] = set()
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
            calculate_input = CalculationInput(
                adv_id=map_data.adv_id,
                nmid=map_data.nmid,
                current_bid=current_bid,
                current_position=current_position,
                target_position=target_position,
                cluster=map_data.cluster,
                step=map_data.step,
                min_bid=mapper.get_min_bid(map_data),
                auto_max_bid=map_data.auto_max_bid_cpm,
                max_bid=map_data.max_cpm
            )
            inputs.add(calculate_input)
        return inputs

    @staticmethod
    async def __get_calculate_data(adv: ComplexAdv) -> set[AdvIdItemCalculateData]:
        from app.modules.shop_runner.service_manager.services.minus_phrase_manager\
            .click_house_manager.click_house_manager import ClickHouseManager
        search_adv_id = adv.search_adv.adv_id
        if search_adv_id is None:
            logger.warning('Нет поисковой компании у комплекса: %s', adv.adv_id)
            return set()
        ch_manager = ClickHouseManager()
        texts_in_this_adv = set(await ch_manager.get_cluster_texts_for_adv(search_adv_id))

        keywords = await adv.get_keywords()

        keywords = [kw for kw in keywords if kw.text in texts_in_this_adv]

        map_datas: set[AdvIdItemCalculateData] = set()
        for nmid in adv.nmids:
            for kw in keywords:
                kw_cpm = getattr(kw, "cpm", None)
                current_cpm = int(kw_cpm + 0.5) if kw_cpm is not None else None
                map_data = AdvIdItemCalculateData(
                    adv_id=adv.search_adv.adv_id,
                    nmid=nmid,
                    cluster=kw.text,
                    current_position=kw.position,
                    max_cpm=adv.max_user_cpm,
                    target_position=adv.target_place,
                    step=adv.bid_cpm_step,
                    auto_max_bid_cpm=kw.auto_max_bid_cpm if adv.bidder_mode else None,
                    current_cpm=current_cpm,
                )
                map_datas.add(map_data)
        return map_datas


    async def _get_maps(self, advs: list[ComplexAdv]) -> set[AdvIdItemCalculateData]:
        calculate_data_tasks: list[Awaitable[set[AdvIdItemCalculateData]]] = []
        for adv in advs:
            get_data_task = self.__get_calculate_data(adv)
            calculate_data_tasks.append(get_data_task)

        results: list[ set[AdvIdItemCalculateData] | BaseException] \
            = await asyncio.gather(*calculate_data_tasks, return_exceptions=True)
        datas: set[AdvIdItemCalculateData] = set()
        for result in results:
            if isinstance(result, BaseException):
                logger.error('Ошибка получения данных для расчета новой ставки: %s', result)
            elif result:
                datas.update(result)
        return datas

    async def _apply_command(self, update_bids_command: UpdateBidsCommand):
        tasks = await asyncio.gather(
            self._redis_keyword_bidder_status_manager.update_statuses(
                update_bids_command
            ),
            self._wb_manager.set_new_cluster_bids(update_bids_command),
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
                await self._redis_cluster_bids_manager.remember_bids(
                    update_bids_command.new_bids
                )
            except Exception as error:  # noqa: BLE001
                logger.error("Не удалось сохранить ставки в Redis: %s", error)

    @staticmethod
    def _get_bids_command(calculation_inputs: set[CalculationInput]):
        from .new_bids_calculator import new_bid_calculate
        new_bids: list[NewBid] = []
        for input_dto in calculation_inputs:
            new_bid: NewBid | None = new_bid_calculate(input_dto)
            if new_bid:
                new_bids.append(new_bid)
        return UpdateBidsCommand(new_bids)

    async def _get_fact_datas(self, advs: list[ComplexAdv])-> dict[int, FactData]:
        tasks: list[Coroutine[Any, Any, FactData]] = []
        for adv in advs:
            task = self.__get_fact_data(adv)
            tasks.append(task)
        results = await asyncio.gather(*tasks, return_exceptions=True)
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
        auto_updater = AdvSettingAutoUpdater(adv.adv_setting)
        fact_data = await auto_updater.get_fact_data(keywords)
        return fact_data


    @staticmethod
    def _get_plan_data(advs: list[ComplexAdv]) -> dict[int, PlanData]:
        plan_datas_map: dict[int, PlanData] = {}
        for adv in advs:
            plan = AdvSettingAutoUpdater.get_plan_data(adv.adv_setting)
            if plan is not None:
                plan_datas_map[adv.adv_id] = plan

        return plan_datas_map





