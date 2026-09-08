import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, cast

from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.dto import (
    NormqueryBidDTO,
)
from app.core.mp.wb.dto.adv_min_bids import AdvMinNmidsBids
from app.modules.predict_keywords_target_place.di import (
    PredictKeywordsTargetPlaceContainer,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)
from .dto.bidder_update_data import BidderUpdateData
from .mappers.adv_id_item_map import AdvIdItemCalculateData
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_keyword_bidder_status_manager import (
    RedisKeywordBidderStatusManager,
)
from app.modules.shop_runner.service_manager.services.v3_status_mode_sync import (
    is_v3_keyword_eligible_for_cluster_bidding,
    is_v3_status_mode_consistent,
)
from app.modules.shop_runner.service_manager.coroutine_phase_trace import (
    AdvPhaseTrace,
    ShopBatchPhaseTrace,
)


from app.modules.cluster_bids_redis import (
    ClusterBidKey,
    RedisApiClusterBidsManager,
    RedisClusterBidsManager,
    RedisClusterBidsTimestampManager,
)
from app.modules.cluster_bids_redis.redis_cluster_bids_manager import ClusterBidEntry
from .wb_manager import WBManager

from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
)
from ...old_modules.setting_auto_updater.data_classes import FactData, PlanData
from ...wb_shop_data_manager.dto.complex_adv import ComplexAdv
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.new_bids_calculator.update_bids_command import (
    DirectEnum,
    UpdateBidsCommand,
    NewBid,
)
from .new_bids_calculator.calculation_input import CalculationInput
from .dto.calculate_data import BidderCalculateData
from .cluster_bid_trace import (
    format_error_detail,
    is_trace_bid_cell,
    is_trace_cell,
    is_trace_enabled,
    log_cluster_bid_trace,
    trace_target_defaults,
)

from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager, run_tasks

# TODO: Внедрить в ректрай WB Api декораторы всплески


_COROUTINE_CLUSTER_BIDS = "update_cluster_bids"

logger = logging.getLogger(__name__)


def _max_workers_for(handler_count: int, cap: int) -> int:
    return max(1, min(handler_count, cap))


def _normalize_cluster_bids_to_search_adv_id(
    fresh: list[NormqueryBidDTO],
    sub_advs: list[ComplexAdv],
    needed_search_adv_ids: set[int],
) -> dict[ClusterBidKey, NormqueryBidDTO]:
    """Приводит WB normquery bids к ключам search auction РК.

    Legacy-ответы с auto ``advert_id`` маппятся через ``auto_adv_id → auction_adv_id``.
    """
    auto_to_search = {
        adv.auto_adv_id: adv.auction_adv_id
        for adv in sub_advs
        if adv.auction_adv_id is not None
    }
    by_key: dict[ClusterBidKey, NormqueryBidDTO] = {}
    for bid in fresh:
        search_id = bid.advert_id
        if search_id not in needed_search_adv_ids:
            mapped = auto_to_search.get(bid.advert_id)
            if mapped is None:
                continue
            search_id = mapped
        key = ClusterBidKey(
            search_adv_id=search_id, nmid=bid.nm_id, cluster=bid.norm_query
        )
        by_key[key] = NormqueryBidDTO(
            advert_id=search_id,
            nm_id=bid.nm_id,
            norm_query=bid.norm_query,
            bid=bid.bid,
        )
    return by_key


_PREDICT_BIDS_MAX_CONCURRENT = 16

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
        redis_api_cluster_bids_manager: RedisApiClusterBidsManager,
        redis_cluster_bids_timestamp_manager: RedisClusterBidsTimestampManager,
        tasks_manager: TasksManager,
        plan_fact_reader: PlanFactReader | None = None,
    ):
        self._wb_manager = wb_manager
        self._redis_keyword_bidder_status_manager = redis_keyword_bidder_status_manager
        self._redis_cluster_bids_manager = redis_cluster_bids_manager
        self._redis_api_cluster_bids_manager = redis_api_cluster_bids_manager
        self._redis_cluster_bids_timestamp_manager: RedisClusterBidsTimestampManager = (
            redis_cluster_bids_timestamp_manager
        )
        self._tasks_manager = tasks_manager
        self._plan_fact_reader = plan_fact_reader or PlanFactReader()
    @staticmethod
    async def _get_keywords_for_cluster_bids(
         adv: ComplexAdv
    ) -> list[CalculatedKeyword]:
        """Keywords для расчёта карт: snapshot adapter (shadow/read) или strict Redis."""
        from app.snapshot_data_updater.config import get_snapshot_config

        cfg = get_snapshot_config()
        if cfg.cluster_bids_read_from_snapshot or cfg.cluster_bids_shadow_compare:
            from app.snapshot_data_updater.adapters.cluster_bids_adapter import (
                ClusterBidsSnapshotAdapter,
            )

            adapter = ClusterBidsSnapshotAdapter(config=cfg)
            return await adapter.get_keywords_for_adv(
                adv, redis_getter=adv.get_keywords
            )
        return await adv.get_keywords()

    async def _get_local_data(
        self, advs: list[ComplexAdv]
    ) -> set[AdvIdItemCalculateData]:
        return await self._get_maps(advs)

    async def _get_data_from_wb_api(
        self,
        advs: list[ComplexAdv],
        map_datas: set[AdvIdItemCalculateData],
    ) -> BidderUpdateData:
        return await self._get_bidder_update_data(advs, map_datas)

    async def _get_calculate_data(self, advs: list[ComplexAdv]) -> BidderCalculateData:
        local_data: set[AdvIdItemCalculateData] = await self._get_local_data(advs)
        remote_data: BidderUpdateData = await self._get_data_from_wb_api(
            advs, local_data
        )

        predict_bids_data: dict[
            int, (dict[int, dict[str, dict[int, int]]] | None)
        ] = await self._get_predict_bids_data(advs, remote_data.min_bids.search)

        return BidderCalculateData(
            data_from_local=local_data,
            data_from_wb_api=remote_data,
            predict_bids_data=predict_bids_data,
        )

    async def update_cluster_bids(self, advs: list[ComplexAdv]) -> None:
        calculate_data: BidderCalculateData = await self._get_calculate_data(advs)
        calculation_inputs: list[CalculationInput] = await self._get_calculation_inputs(
                calculate_data)

        new_bids_command: UpdateBidsCommand = self._get_bids_command(
            calculation_inputs
        )
        trace_defaults = trace_target_defaults()
        if trace_defaults:
            shop_id = self._wb_manager._shop_id # pyright: ignore # type: ignore
            map_match = any(
                is_trace_cell(
                    shop_id=shop_id,
                    adv_id=cell.adv_id,
                    search_adv_id=cell.search_adv_id,
                    nmid=cell.nmid,
                    ks_id=cell.keyword_setting_original_id,
                    key=cell.cluster,
                )
                for cell in calculate_data.data_from_local
            )
            calc_match = sum(
                1
                for ci in calculation_inputs
                if is_trace_bid_cell(
                    shop_id=shop_id,
                    search_adv_id=ci.search_adv_id,
                    nmid=ci.nmid,
                    key=ci.cluster,
                )
            )
            cmd_match = sum(
                1
                for nb in new_bids_command.new_bids
                if is_trace_bid_cell(
                    shop_id=shop_id,
                    search_adv_id=nb.search_adv_id,
                    nmid=nb.nmid,
                    key=nb.cluster,
                )
            )
            log_cluster_bid_trace(
                step="tick_batch",
                shop_id=shop_id,
                adv_id=trace_defaults.get("adv_id"),
                search_adv_id=trace_defaults.get("search_adv_id"),
                nmid=trace_defaults.get("nmid"),
                ks_id=trace_defaults.get("ks_id"),
                key=trace_defaults.get("key"),
                map_cells_count=len(calculate_data.data_from_local),
                calc_inputs_count=len(calculation_inputs),
                command_bids_count=len(new_bids_command.new_bids),
                trace_in_map=map_match,
                trace_calc_inputs=calc_match,
                trace_in_command=cmd_match,
            )
        v3_cells = {
            cell for cell in calculate_data.data_from_local if cell.v3_managed
        }
        if v3_cells:
            from .v3_cluster_bid_safety_cap import (
                apply_v3_cluster_bid_safety_cap,
                build_keywords_by_cell,
                build_v3_matrix_cap_index,
            )

            bid_keys = [
                ClusterBidKey(
                    search_adv_id=cell.search_adv_id,
                    nmid=cell.nmid,
                    cluster=cell.cluster,
                )
                for cell in v3_cells
            ]
            stored_bids = await self._redis_cluster_bids_manager.get_bids(
                bid_keys
            )
            wb_data = calculate_data.data_from_wb_api
            cap_index = await build_v3_matrix_cap_index(
                advs=wb_data.advs,
                map_datas=v3_cells,
                min_bids=wb_data.min_bids,
                keywords_getter=self._get_keywords_for_cluster_bids,
            )
            keywords_by_cell = await build_keywords_by_cell(
                wb_data.advs,
                v3_cells,
                self._get_keywords_for_cluster_bids,
            )
            new_bids_command = apply_v3_cluster_bid_safety_cap(
                command=new_bids_command,
                map_datas=v3_cells,
                calculation_inputs=calculation_inputs,
                fact_datas=wb_data.fact_datas,
                plan_datas=wb_data.plan_datas,
                cap_index=cap_index,
                stored_bids=stored_bids,
                keywords_by_cell=keywords_by_cell,
            )

        await self._apply_command(new_bids_command)
        if advs:
            await self._redis_cluster_bids_timestamp_manager.set_many(advs)


    async def _get_bidder_update_data(
        self,
        advs: list[ComplexAdv],
        map_datas: set[AdvIdItemCalculateData],
    ) -> BidderUpdateData:
        trace = ShopBatchPhaseTrace.from_complex_advs(
            coroutine=_COROUTINE_CLUSTER_BIDS, advs=advs
        )
        trace.marker(
            "bidder_update_data_inputs",
            extra={"map_datas_count": len(map_datas)},
        )

        async def _get_cluster_bids() -> list[NormqueryBidDTO]:
            with trace.phase("parallel_get_cluster_bids"):
                return await self._get_cluster_bids_for_maps(
                    map_datas, advs, batch_trace=trace
                )

        async def _get_min_bids() -> AdvMinNmidsBids:
            with trace.phase("parallel_get_min_bids"):
                return await self._wb_manager.get_min_bids_cache_only(
                    advs, context="update_cluster_bids"
                )

        async def _get_fact_data() -> dict[int, FactData]:
            with trace.phase("parallel_get_fact_data"):
                return await self._get_fact_datas(advs, batch_trace=trace)

        handlers: list[Callable[[], Awaitable[Any]]] = [
            _get_cluster_bids,
            _get_min_bids,
            _get_fact_data,
        ]

        with trace.phase("manager_load_wb_parallel_data"):
            results = await run_tasks(
                handlers,
                max_workers=3,
                return_exceptions=False,
                tasks_manager=self._tasks_manager,
            )
        current_bids = cast(list[NormqueryBidDTO], results[0])
        min_bids = cast(AdvMinNmidsBids, results[1])
        fact_data = cast(dict[int, FactData], results[2])
        with trace.phase("manager_get_plan_data"):
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
        *,
        batch_trace: ShopBatchPhaseTrace | None = None,
    ) -> list[NormqueryBidDTO]:
        trace = batch_trace or ShopBatchPhaseTrace.from_complex_advs(
            coroutine=_COROUTINE_CLUSTER_BIDS, advs=advs
        )
        if not map_datas:
            trace.marker("cluster_bids_empty_map_datas")
            return []
        keys: list[ClusterBidKey] = [
            ClusterBidKey(
                search_adv_id=data.search_adv_id,
                nmid=data.nmid,
                cluster=data.cluster,
            )
            for data in map_datas
        ]
        with trace.phase("cluster_bids_redis_get"):
            cached = await self._redis_api_cluster_bids_manager.get_bids(keys)
        total = len(keys)
        cached_count = len(cached)
        if cached_count:
            logger.debug(
                "Cluster bid cache HIT for %s/%s combinations", cached_count, total
            )
        missing_keys = [key for key in keys if key not in cached]
        trace.marker(
            "cluster_bids_redis_result",
            extra={
                "keys_total": total,
                "keys_cached": cached_count,
                "keys_missing": len(missing_keys),
            },
        )
        bids_map: dict[ClusterBidKey, NormqueryBidDTO] = {
            key: NormqueryBidDTO(
                advert_id=key.search_adv_id,
                nm_id=key.nmid,
                norm_query=key.cluster,
                bid=value,
            )
            for key, value in cached.items()
        }
        if missing_keys:
            needed_adv_ids = {k.search_adv_id for k in missing_keys}
            sub_advs = [
                a
                for a in advs
                if a.auction_adv_id is not None and a.auction_adv_id in needed_adv_ids
            ]
            if sub_advs:
                logger.info(
                    "Cluster bid Redis API cache MISS for %s/%s keys; "
                    "loading from WB API for %s search campaign(s)",
                    len(missing_keys),
                    total,
                    len({a.auction_adv_id for a in sub_advs if a.auction_adv_id}),
                )
                try:
                    with trace.phase("cluster_bids_wb_fallback"):
                        fresh = await self._wb_manager.get_current_bids(sub_advs)
                except Exception:
                    logger.exception(
                        "Cluster bid WB API fallback failed (%s/%s miss)",
                        len(missing_keys),
                        total,
                    )
                else:
                    with trace.phase("cluster_bids_wb_fallback_redis_write"):
                        by_key = _normalize_cluster_bids_to_search_adv_id(
                            fresh, sub_advs, needed_adv_ids
                        )
                        normalized_fresh = list(by_key.values())
                        try:
                            _ = await self._redis_api_cluster_bids_manager.replace_from_api(
                                normalized_fresh
                            )
                        except Exception:
                            logger.exception(
                                "Cluster bid: failed to write WB fallback to Redis API cache"
                            )
                    for mk in missing_keys:
                        dto = by_key.get(mk)
                        if dto is not None:
                            bids_map[mk] = dto
                    trace.marker(
                        "cluster_bids_wb_fallback_done",
                        extra={"fresh_bids": len(fresh)},
                    )
            else:
                logger.debug(
                    "Cluster bid cache MISS for %s/%s combinations; "
                    "no ComplexAdv for WB fallback (auction_adv_id)",
                    len(missing_keys),
                    total,
                )
        return list(bids_map.values())

    async def _get_calculation_inputs(
        self,
        calculate_data: BidderCalculateData,
        *,
        batch_trace: ShopBatchPhaseTrace | None = None,
    ) -> list[CalculationInput]:
        from .mappers import Mapper

        advs = calculate_data.data_from_wb_api.advs
        trace = batch_trace or ShopBatchPhaseTrace.from_complex_advs(
            coroutine=_COROUTINE_CLUSTER_BIDS, advs=advs
        )
        bidder_update_data = calculate_data.data_from_wb_api
        maps_data: set[AdvIdItemCalculateData] = calculate_data.data_from_local
        mapper = Mapper(bidder_update_data)
        bid_keys = [
            ClusterBidKey(
                search_adv_id=map_data.search_adv_id, # TODO: ТУт поменять на явное search_adv_id
                nmid=map_data.nmid,
                cluster=map_data.cluster,
            )
            for map_data in maps_data
        ]
        with trace.phase("calc_inputs_redis_get_bid_states"):
            cached_states = await self._redis_cluster_bids_manager.get_bid_states(bid_keys)
        inputs: list[CalculationInput] = []
        skipped_no_bid = 0
        # Batch per-shop: WBManager/ClusterBidsManagerContainer создаются с одним shop_id;
        # advs здесь — только ComplexAdv этого магазина (см. DOTO/WORKLOG.md DEBUG_CLUSTER_BID_TRACE).
        trace_shop_id = self._wb_manager._shop_id # pyright: ignore # type: ignore
        trace_on = is_trace_enabled()
        for map_data in maps_data:
            current_bid = mapper.get_current_bid(map_data)
            if current_bid is None:
                fallback_bid = map_data.current_cpm
                if fallback_bid is None:
                    skipped_no_bid += 1
                    if trace_on and is_trace_cell(
                        shop_id=trace_shop_id,
                        adv_id=map_data.adv_id,
                        search_adv_id=map_data.search_adv_id,
                        nmid=map_data.nmid,
                        ks_id=map_data.keyword_setting_original_id,
                        key=map_data.cluster,
                    ):
                        log_cluster_bid_trace(
                            step="calc_input",
                            shop_id=trace_shop_id,
                            adv_id=map_data.adv_id,
                            search_adv_id=map_data.search_adv_id,
                            nmid=map_data.nmid,
                            ks_id=map_data.keyword_setting_original_id,
                            key=map_data.cluster,
                            created=False,
                            skip_reason="no_current_bid",
                        )
                    logger.debug(
                        "Нет текущей ставки для search_adv_id: %s, nmid: %s, cluster: %s",
                        map_data.search_adv_id,
                        map_data.nmid,
                        map_data.cluster,
                    )
                    continue
                current_bid = fallback_bid
            current_position = mapper.get_current_position(map_data)
            target_position: int | None = mapper.get_target_position(map_data)
            search_adv_id = map_data.search_adv_id
            nmid = map_data.nmid
            state_key = ClusterBidKey(
                search_adv_id=search_adv_id,
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
            predict_bids_data_for_adv = (
                calculate_data.predict_bids_data.get(search_adv_id)
                if calculate_data.predict_bids_data is not None
                else None
            )
            predict_target_bids = (
                predict_bids_data_for_adv.get(nmid)
                if isinstance(predict_bids_data_for_adv, dict)
                else None
            )
            calculate_input = CalculationInput(
                search_adv_id=search_adv_id,
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
                snap_to_min_bid_no_keyword_target=map_data.snap_to_min_bid_no_keyword_target,
            )
            if trace_on and is_trace_cell(
                shop_id=trace_shop_id,
                adv_id=map_data.adv_id,
                search_adv_id=map_data.search_adv_id,
                nmid=map_data.nmid,
                ks_id=map_data.keyword_setting_original_id,
                key=map_data.cluster,
            ):
                log_cluster_bid_trace(
                    step="calc_input",
                    shop_id=trace_shop_id,
                    adv_id=map_data.adv_id,
                    search_adv_id=map_data.search_adv_id,
                    nmid=map_data.nmid,
                    ks_id=map_data.keyword_setting_original_id,
                    key=map_data.cluster,
                    created=True,
                    current_bid=current_bid,
                    current_position=current_position,
                    target_position=target_position,
                    min_bid=calculate_input.min_bid,
                    max_bid=calculate_input.max_bid,
                    bidder_step=calculate_input.step,
                    prev_direct=prev_direct,
                    prev_step=prev_step,
                )
            inputs.append(calculate_input)

        return inputs

    async def __get_calculate_data(
        self,
        adv: ComplexAdv,
        cluster_texts_from_ch: set[str],
    ) -> set[AdvIdItemCalculateData]:
        """Построить набор карт (nmid × кластер) для расчёта ставок по одной ComplexAdv.

        Поле ``snap_to_min_bid_no_keyword_target`` выставляется в теле метода при
        ``individual_keywords_target_place_mode`` и отсутствии ``target_place`` у
        ключевого слова; интерпретация флага в калькуляторе — в ``new_bid_calculate``.
        В этом snap-случае ``target_position`` в карте — ``None`` (цель РК сюда не
        подставляется).
        """
        trace = AdvPhaseTrace.for_complex_adv(
            coroutine=_COROUTINE_CLUSTER_BIDS, adv=adv
        )
        search_adv_id = adv.auction_adv_id
        if search_adv_id is None:
            logger.warning("Нет поисковой компании у комплекса: %s", adv.adv_id)
            return set()
        texts_in_this_adv = cluster_texts_from_ch
        trace.marker(
            "per_adv_map_inputs",
            extra={"cluster_texts_ch": len(texts_in_this_adv)},
        )

        with trace.phase("per_adv_get_keywords_cache_only"):
            keywords: list[CalculatedKeyword] = await self._get_keywords_for_cluster_bids(
                adv
            )
        with trace.phase("per_adv_filter_keywords"):
            keywords_good = [kw for kw in keywords if kw.status == KeywordStatus.GOOD]
        # V3: торги только у согласованных БС/фикс.фраз; авто+MIN_CPA и OFF отсекаются.
        if adv.bot_active:
            adv_strategy = adv.strategy
            inconsistent = [
                kw
                for kw in keywords_good
                if not is_v3_status_mode_consistent(
                    hard_status=int(kw.hard_status),
                    strategy_mode=kw.strategy_mode,
                    adv_strategy=adv_strategy,
                )
            ]
            if inconsistent:
                logger.warning(
                    "V3 cache inconsistency detected for adv_id=%s: %s keywords "
                    "(hard_status vs strategy_mode mismatch)",
                    adv.adv_id,
                    len(inconsistent),
                )
            keywords_good = [
                kw
                for kw in keywords_good
                if is_v3_keyword_eligible_for_cluster_bidding(
                    hard_status=int(kw.hard_status),
                    strategy_mode=kw.strategy_mode,
                    adv_strategy=adv_strategy,
                )
            ]
        # clusters_adv_stats / WB API use norm_query; keyword_setting.text (kw.text) may differ.
        matched_in_ch = [
            kw
            for kw in keywords_good
            if kw.cluster_stat.text in texts_in_this_adv
            or kw.text in texts_in_this_adv
        ]
        # Если единственные GOOD не попали в snapshots clusters_adv_stats (срез может отличаться
        # от mv_clusters_*), всё равно участвуют в торгах по norm_query из cluster_stat.
        keywords = matched_in_ch if matched_in_ch else keywords_good
        map_datas: set[AdvIdItemCalculateData] = set()
        for nmid in adv.nmids:
            for kw in keywords:
                cluster_for_wb = kw.cluster_stat.text or kw.text
                kw_cpm = getattr(kw, "cpm", None)
                current_cpm = int(kw_cpm + 0.5) if kw_cpm is not None else None
                # snap_to_min: target_place is None или 0 — торг на минимум WB.
                # target_place > 0 — индивидуальная позиция из CH/V3.
                if adv.individual_keywords_target_place_mode:
                    keyword_target_place = kw.target_place
                    if (
                        keyword_target_place is not None
                        and keyword_target_place > 0
                    ):
                        target_position = keyword_target_place
                        snap_to_min = False
                    else:
                        target_position = None
                        snap_to_min = True
                else:
                    target_position = adv.target_place
                    snap_to_min = False
                v3_managed = adv.bot_active
                map_data = AdvIdItemCalculateData(
                    search_adv_id=search_adv_id,
                    adv_id=adv.adv_id,
                    nmid=nmid,
                    cluster=cluster_for_wb,
                    current_position=kw.position,
                    max_cpm=adv.max_user_cpm,
                    target_position=target_position,
                    step=adv.bid_cpm_step,
                    current_cpm=current_cpm,
                    keyword_setting_original_id=kw.keyword_setting_original_id,
                    strategy_mode=(
                        kw.strategy_mode if adv.bot_active else None
                    ),
                    v3_managed=v3_managed,
                    snap_to_min_bid_no_keyword_target=snap_to_min,
                )
                map_datas.add(map_data)
        trace_defaults = trace_target_defaults()
        if trace_defaults:
            target_nmid = trace_defaults.get("nmid")
            target_key = trace_defaults.get("key")
            target_ks_id = trace_defaults.get("ks_id")
            in_map = any(
                (
                    (target_nmid is None or cell.nmid == target_nmid)
                    and (target_key is None or cell.cluster == target_key)
                    and (
                        target_ks_id is None
                        or cell.keyword_setting_original_id == target_ks_id
                    )
                )
                for cell in map_datas
            )
            log_cluster_bid_trace(
                step="map_cell",
                shop_id=adv.shop_id,
                adv_id=adv.adv_id,
                search_adv_id=search_adv_id,
                nmid=target_nmid,
                ks_id=target_ks_id,
                key=target_key,
                in_map=in_map,
                map_cells_count=len(map_datas),
                cluster_texts_ch=len(texts_in_this_adv),
                keywords_good_count=len(keywords_good),
            )
        return map_datas

    async def _get_maps(self, advs: list[ComplexAdv]) -> set[AdvIdItemCalculateData]:
        from app.modules.shop_runner.service_manager.services.minus_phrase_manager.click_house_manager.click_house_manager import (
            ClickHouseManager,
        )

        auction_ids_unique: list[int] = []
        seen_auction: set[int] = set()
        for adv in advs:
            aid = adv.auction_adv_id
            if aid is not None and aid not in seen_auction:
                seen_auction.add(aid)
                auction_ids_unique.append(aid)
        trace = ShopBatchPhaseTrace.from_complex_advs(
            coroutine=_COROUTINE_CLUSTER_BIDS, advs=advs
        )
        ch_manager = ClickHouseManager()
        with trace.phase("manager_get_cluster_texts_from_ch"):
            texts_by_adv_id: dict[int, set[str]] = (
                await ch_manager.get_cluster_texts_for_adv_ids(auction_ids_unique)
                if auction_ids_unique
                else {}
            )
        handlers: list[Callable[[], Awaitable[set[AdvIdItemCalculateData]]]] = []
        for adv in advs:
            cluster_texts: set[str] = (
                texts_by_adv_id.get(adv.auction_adv_id, set())
                if adv.auction_adv_id is not None
                else set()
            )

            async def _run(
                a: ComplexAdv = adv,
                texts: set[str] = cluster_texts,
            ) -> set[AdvIdItemCalculateData]:
                adv_trace = AdvPhaseTrace.for_complex_adv(
                    coroutine=_COROUTINE_CLUSTER_BIDS, adv=a
                )
                with adv_trace.phase("per_adv_get_calculate_maps_total"):
                    return await self.__get_calculate_data(a, texts)

            handlers.append(_run)
        with trace.phase("manager_collect_calculate_data_parallel"):
            results = await run_tasks(
                handlers,
                max_workers=_max_workers_for(len(handlers), cap=16),
                tasks_manager=self._tasks_manager,
            )
        datas: set[AdvIdItemCalculateData] = set()
        for result in results:
            if isinstance(result, BaseException):
                logger.error(
                    "Ошибка получения данных для расчета новой ставки: %s", result
                )
            elif result:
                datas.update(result)
        return datas

    async def _apply_command(
        self,
        update_bids_command: UpdateBidsCommand,
        *,
        batch_trace: ShopBatchPhaseTrace | None = None,
    ) -> None:
        """Применить рассчитанные ставки: WB API → статусы ключей → кэш шага биддера в Redis.

        Порядок: сначала ``set_new_cluster_bids`` (обязателен), затем ``update_statuses``
        (best-effort), затем ``remember_bids`` (обязателен после успешного WB).

        Ошибки ``update_statuses`` перехватываются и логируются — сбой статусов не должен
        блокировать ``remember_bids``: иначе ставки уже на WB, а ``prev_step``/``prev_direct``
        в Redis не обновятся.

        Ошибки ``remember_bids`` **намеренно не перехватываются**: сбой записи в Redis
        прерывает весь ``update_cluster_bids`` (timestamp последнего цикла не обновится).
        Это fail-closed: без сохранённого состояния шага следующий расчёт может быть
        некорректным, поэтому цикл считается неуспешным, даже если WB уже принял ставки.
        """
        adv_ids = list({b.search_adv_id for b in update_bids_command.new_bids})
        trace_defaults = trace_target_defaults()
        if trace_defaults:
            shop_id = self._wb_manager._shop_id # pyright: ignore # type: ignore
            matching_bids = [
                b
                for b in update_bids_command.new_bids
                if is_trace_bid_cell(
                    shop_id=shop_id,
                    search_adv_id=b.search_adv_id,
                    nmid=b.nmid,
                    key=b.cluster,
                )
            ]
            for bid in matching_bids:
                log_cluster_bid_trace(
                    step="apply_before",
                    shop_id=shop_id,
                    adv_id=trace_defaults.get("adv_id"),
                    search_adv_id=bid.search_adv_id,
                    nmid=bid.nmid,
                    key=bid.cluster,
                    in_command=True,
                    outgoing_bid=bid.new_bid,
                    direct=bid.direct,
                    step_value=bid.step,
                    command_size=len(update_bids_command.new_bids),
                    wb_payload_advert_id=bid.search_adv_id,
                    wb_payload_nm_id=bid.nmid,
                    wb_payload_norm_query=bid.cluster,
                    wb_payload_bid=bid.new_bid,
                )
            if not matching_bids:
                log_cluster_bid_trace(
                    step="apply_before",
                    shop_id=shop_id,
                    adv_id=trace_defaults.get("adv_id"),
                    search_adv_id=trace_defaults.get("search_adv_id"),
                    nmid=trace_defaults.get("nmid"),
                    ks_id=trace_defaults.get("ks_id"),
                    key=trace_defaults.get("key"),
                    in_command=False,
                    command_size=len(update_bids_command.new_bids),
                )
        trace = batch_trace or ShopBatchPhaseTrace(
            coroutine=_COROUTINE_CLUSTER_BIDS,
            shop_id="unknown",
            adv_ids=adv_ids,
        )
        try:
            with trace.phase("apply_set_new_cluster_bids"):
                await self._wb_manager.set_new_cluster_bids(update_bids_command)
        except Exception as exc:
            if trace_defaults:
                log_cluster_bid_trace(
                    step="apply_after",
                    shop_id=self._wb_manager._shop_id, # pyright: ignore # type: ignore
                    adv_id=trace_defaults.get("adv_id"),
                    search_adv_id=trace_defaults.get("search_adv_id"),
                    nmid=trace_defaults.get("nmid"),
                    ks_id=trace_defaults.get("ks_id"),
                    key=trace_defaults.get("key"),
                    wb_ok=False,
                    error_detail=format_error_detail(exc),
                )
            raise
        if trace_defaults:
            log_cluster_bid_trace(
                step="apply_after",
                shop_id=self._wb_manager._shop_id, # pyright: ignore # type: ignore
                adv_id=trace_defaults.get("adv_id"),
                search_adv_id=trace_defaults.get("search_adv_id"),
                nmid=trace_defaults.get("nmid"),
                ks_id=trace_defaults.get("ks_id"),
                key=trace_defaults.get("key"),
                wb_ok=True,
            )
        try:
            with trace.phase("apply_update_keyword_statuses"):
                await self._redis_keyword_bidder_status_manager.update_statuses(
                    update_bids_command
                )
        except Exception:  # noqa: BLE001
            logger.exception("Не удалось обновить статусы ключей в Redis")
        entries = [
            ClusterBidEntry(
                search_adv_id=b.search_adv_id,
                nmid=b.nmid,
                cluster=b.cluster,
                new_bid=b.new_bid,
                step=b.step,
                direct=str(b.direct.value),
            )
            for b in update_bids_command.new_bids
        ]
        with trace.phase("apply_remember_bids_redis"):
            await self._redis_cluster_bids_manager.remember_bids(entries)


    @staticmethod
    def _get_bids_command(calculation_inputs: list[CalculationInput]):
        from .new_bids_calculator import new_bid_calculate

        new_bids: list[NewBid] = []
        trace_on = is_trace_enabled()
        trace_shop_id = trace_target_defaults().get("shop_id")
        for input_dto in calculation_inputs:
            new_bid: NewBid | None = new_bid_calculate(input_dto)
            if trace_on and is_trace_bid_cell(
                shop_id=trace_shop_id,
                search_adv_id=input_dto.search_adv_id,
                nmid=input_dto.nmid,
                key=input_dto.cluster,
            ):
                if new_bid is None:
                    log_cluster_bid_trace(
                        step="new_bid_calculate",
                        search_adv_id=input_dto.search_adv_id,
                        nmid=input_dto.nmid,
                        key=input_dto.cluster,
                        result="none",
                    )
                else:
                    log_cluster_bid_trace(
                        step="new_bid_calculate",
                        search_adv_id=input_dto.search_adv_id,
                        nmid=input_dto.nmid,
                        key=input_dto.cluster,
                        result="created",
                        new_bid=new_bid.new_bid,
                        direct=new_bid.direct,
                        step_value=new_bid.step,
                        status=new_bid.bidder_keyword_status,
                    )
            if new_bid:
                new_bids.append(new_bid)
        return UpdateBidsCommand(new_bids)

    async def _get_fact_datas(
        self,
        advs: list[ComplexAdv],
        *,
        batch_trace: ShopBatchPhaseTrace | None = None,
    ) -> dict[int, FactData]:
        if not advs:
            return {}
        trace = batch_trace or ShopBatchPhaseTrace.from_complex_advs(
            coroutine=_COROUTINE_CLUSTER_BIDS, advs=advs
        )
        adv_ids = [adv.adv_id for adv in advs]
        try:
            with trace.phase("fact_data_ch_get_latest_plan_facts"):
                summaries_by_adv_id = await self._plan_fact_reader.get_latest_plan_facts(
                    adv_ids
                )
        except Exception as error:
            logger.error("Ошибка batch-получения факта из CH: %s", error)
            return {}
        adv_to_fact_map: dict[int, FactData] = {}
        from app.modules.plan_fact.provider import PlanFactProvider
        for adv in advs:
            fact = PlanFactProvider.fact_data_from_plan_fact_summary(
                summaries_by_adv_id.get(adv.adv_id),
                adv.adv_setting,
            )
            if fact is not None:
                adv_to_fact_map[adv.adv_id] = fact
        return adv_to_fact_map

    @staticmethod
    def _get_plan_data(advs: list[ComplexAdv]) -> dict[int, PlanData]:
        plan_datas_map: dict[int, PlanData] = {}
        from app.modules.plan_fact.provider import PlanFactProvider
        for adv in advs:
            plan = PlanFactProvider.get_effective_plan_data(
                adv.adv_setting, complex_adv=adv
            )
            if plan is not None:
                plan_datas_map[adv.adv_id] = plan

        return plan_datas_map

    @staticmethod
    async def _get_predict_bids_data(
        advs: list[ComplexAdv],
        auction_min_bids_by_nmid: dict[int, int],
    ) -> dict[int, (dict[int, dict[str, dict[int, int]]] | None)]:
        trace = ShopBatchPhaseTrace.from_complex_advs(
            coroutine=_COROUTINE_CLUSTER_BIDS, advs=advs
        )
        container = PredictKeywordsTargetPlaceContainer()
        bids_for_positions_manager = container.bids_for_positions_manager()
        adv_result: dict[int, (dict[int, dict[str, dict[int, int]]] | None)] = {}
        for adv in advs:
            search_adv_id = adv.auction_adv_id
            if search_adv_id is None:
                continue
            if adv.individual_keywords_target_place_mode is False:
                adv_result[search_adv_id] = None
            else:
                adv_result[search_adv_id] = {}

        work: list[tuple[int, int, int]] = []
        for adv in advs:
            search_adv_id = adv.auction_adv_id
            if (
                search_adv_id is None
                or adv.individual_keywords_target_place_mode is False
            ):
                continue
            for nmid in adv.nmids:
                try:
                    min_bid = auction_min_bids_by_nmid[nmid]
                except KeyError:
                    logger.error(
                        "predict_bids: нет min_bid для nmid=%s в min_bids.search "
                        "(search_adv_id=%s), пропуск позиции",
                        nmid,
                        search_adv_id,
                    )
                    continue
                work.append((search_adv_id, nmid, min_bid))

        if not work:
            trace.marker("predict_bids_no_work")
            return adv_result

        trace.marker(
            "predict_bids_work",
            extra={"work_items": len(work), "advs": len(advs)},
        )
        sem = asyncio.Semaphore(_PREDICT_BIDS_MAX_CONCURRENT)

        async def _fetch(
            item: tuple[int, int, int],
        ) -> tuple[int, int, dict[str, dict[int, int]]]:
            sid, nmid, min_bid = item
            bid_positions_result = (
                await bids_for_positions_manager.get_bid_positions_normalized(
                    nmid=nmid, min_bid=min_bid, positions_size=300
                )
            )
            dict_result: dict[str, dict[int, int]] = {
                keyword_text: {pos.position: pos.bid for pos in row_list}
                for keyword_text, row_list in bid_positions_result.items()
            }
            return sid, nmid, dict_result

        async def _guarded(
            item: tuple[int, int, int],
        ) -> tuple[int, int, dict[str, dict[int, int]]]:
            async with sem:
                return await _fetch(item)

        with trace.phase("predict_bids_gather_normalized"):
            results: list[
                tuple[int, int, dict[str, dict[int, int]]] | BaseException
            ] = await asyncio.gather(
                *(_guarded(w) for w in work),
                return_exceptions=True,
            )
        errors_count = sum(1 for r in results if isinstance(r, BaseException))
        trace.marker(
            "predict_bids_gather_done",
            extra={"work_items": len(work), "errors": errors_count},
        )
        for item, result in zip(work, results, strict=False):
            if isinstance(result, BaseException):
                sid, nmid, _ = item
                logger.error(
                    "predict_bids: failed get_bid_positions_normalized "
                    "(search_adv_id=%s, nmid=%s): %s",
                    sid,
                    nmid,
                    result,
                )
                continue
            sid, nmid, dict_result = result
            bucket = adv_result.get(sid)
            if isinstance(bucket, dict):
                bucket[nmid] = dict_result

        return adv_result
