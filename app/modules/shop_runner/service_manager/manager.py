"""РћСЂРєРµСЃС‚СЂР°С‚РѕСЂ С„РѕРЅРѕРІС‹С… РєРѕСЂСѓС‚РёРЅ shop_runner Рё РёС… РёРЅС„СЂР°СЃС‚СЂСѓРєС‚СѓСЂРЅС‹С… Р·Р°РІРёСЃРёРјРѕСЃС‚РµР№."""

import asyncio
import functools
import logging
import os
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterable, Sequence
from datetime import datetime
from typing import (
    Any,
    TypeVar,
)



from app.core.di.wb_manager_hub import WBManagerHubFactory, WBManagerHub
from app.core.redis_manager_v2.redis_client import RedisClient
from sqlalchemy import or_, update

from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    KeywordSetting,
)
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy
from app.modules.common_slaves.wildberries.models.models import BidderCoroutineType
from app.modules.auto_budget_manager import (
    AutoBudgetEnsureResult,
    AutoBudgetEnsureStatus,
    AutoBudgetService,
)
from app.shared.domains.wb.dto.wb_adv_dto import WBAdvDTO
from app.shared.domains.wb.enums import (
    AdvType,
)
from app.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater
from app.modules.full_stat_adv_updater import wb_data_getter
from app.modules.full_stat_adv_updater.types.full_adv_stat import FullAdvStat
from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.shop_runner.service_manager.services.update_commot_bid_in_search_advs_manager.redis_common_bid_timestamp_manager import (
    RedisCommonBidTimestampManager,
)
from app.modules.shop_runner.service_manager.services.update_commot_bid_in_search_advs_manager.redis_common_bid_value_manager import (
    RedisCommonBidValueManager,
)
from app.modules.shop_runner.wb_statistic_manager.redis_common_stat_timestamp_manager import (
    RedisCommonStatTimestampManager,
)
from app.modules.shop_runner.wb_statistic_manager.redis_cluster_stat_timestamp_manager import (
    RedisClusterStatTimestampManager,
)

from app.settings import settings

from .services.increment_fact_data_manager.increment_fact_data_manager import (
    IncrementFactDataManager,
)
from .services.auto_shelf_bid_increment_manager import AutoShelfBidIncrementManager
from .services.auto_shelf_bid_increment_manager.redis_auto_recommendations_bid_value_manager import (
    RedisAutoRecommendationsBidValueManager,
)
from .services.auto_shelf_bid_control_manager import (
    AutoShelfBidControlManager,
    AutoShelfBidSetter,
)
from .services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider import (
    AutoShelfBidControlViewProvider,
)
from .services.plan_fact_controller.plan_fact_reader import PlanFactReader
from .wb_shop_data_manager import WBShopDataManager
from .wb_shop_data_manager import ComplexAdv
from .wb_shop_data_manager.dto.pre_complex_adv import PreComplexAdv
from .while_coroutines_decorator import while_coroutine_decorator
from ..bidder.bidder_func import (
    build_v3_safety_cap_by_keyword_setting_original_id,
    run_bidder_process_for_adv,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.modules.shop_runner.tasks_manager.tasks_manager import (
    TasksManager,
    run_tasks,
)
from ..wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from ...wb_adv_updater import data_manager
from .services.auto_adv_active_control import AutoAdvActiveControlService
from .services.redis_campaign_activity_reason_manager import (
    RedisCampaignActivityReasonManager,
)
from .services.auto_reset_bid_service import AutoResetBidService
from .services.clusters_adv_stat_updater.clusters_adv_stat_updater import (
    ClustersAdvStatUpdater,
)
from .services.clusters_adv_stat_updater.di import ClustersAdvStatUpdaterContainer
from .services.delete_keywords_from_wl_by_mean_auto_ctr_manager.delete_keywords_from_wl_by_mean_auto_ctr_manager import (
    delete_keywords_from_wl_by_mean_auto_ctr,
)
from .services.adv_strategy_selector import AdvStrategySelector, StrategySelection
from .services.stats_freshness_cache_manager import RedisStatsFreshnessStateCacheManager
from .services.stats_freshness_guard import StatsFreshnessState
from .services.stats_freshness_manager import StatsFreshnessManager
from .services.v3_status_mode_sync import (
    is_v3_campaign,
    keyword_strategy_mode_for_adv_strategy,
)
from .services.update_cluster_bids_manager.cluster_bid_trace import (
    is_trace_cell,
    is_trace_enabled,
    log_cluster_bid_trace,
    trace_target_defaults,
)
from .services.update_cluster_bids_manager.new_bids_calculator.update_bids_command import (
    DirectEnum,
    NewBid,
    UpdateBidsCommand,
)
from app.shared.domains.wb.dto.redis_keyword_bidder_status_manager.bidder_keyword_status import (
    BidderKeywordStatus,
)
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)

def _cluster_stats_diagnostic_enabled() -> bool:
    """Р’РєР»СЋС‡Р°РµС‚ РїРѕРґСЂРѕР±РЅС‹Рµ DEBUG-Р»РѕРіРё РґР»СЏ cluster freshness path."""
    value = os.environ.get("CLUSTER_STATS_DIAGNOSTIC_ENABLED", "")
    return value.strip().lower() in {"1", "true", "yes", "on"}

T = TypeVar("T")


def _collect_plan_fact_refresh_adv_ids(pre_advs: list[PreComplexAdv]) -> list[int]:
    """РЎРѕР±РёСЂР°РµС‚ СѓРЅРёРєР°Р»СЊРЅС‹Рµ adv_id РґР»СЏ РЅРµРјРµРґР»РµРЅРЅРѕРіРѕ refresh plan-fact РєРµС€Р°.

    РЎРѕСЂС‚РёСЂРѕРІРєР° РЅСѓР¶РЅР° РґР»СЏ СЃС‚Р°Р±РёР»СЊРЅС‹С… С‚РµСЃС‚РѕРІ Рё РїСЂРµРґСЃРєР°Р·СѓРµРјРѕРіРѕ РїРѕСЂСЏРґРєР° С‡С‚РµРЅРёСЏ РёР· CH.
    """
    return sorted({int(pre_adv.adv_id) for pre_adv in pre_advs})


class CoroutinesManager:
    def __init__(
        self,
        wb_api: WBApi,
        redis_client_wrapper: RedisClient,
        tasks_manager: TasksManager,
        plan_fact_reader: PlanFactReader | None = None,
        wb_manager_hub: WBManagerHub | None = None,

    ):
        wb_cabinet = wb_api.wb_cabinet
        assert wb_cabinet
        if not wb_api.shop_id:
            raise ValueError("CoroutinesManager requires non-empty shop_id")
        if wb_manager_hub is None:
            wb_manager_hub = WBManagerHubFactory.get_wb_manager_from_context()  # fallback for tests
        self._wb_manager_hub = wb_manager_hub
        self._plan_fact_reader = plan_fact_reader or PlanFactReader(
            redis_client=redis_client_wrapper
        )
        self._wb_shop_data_manager = WBShopDataManager(
            wb_cabinet,
            tasks_manager=tasks_manager,
            wb_api_data_manager=wb_manager_hub.wb_data_manager,
            wb_manager=wb_manager_hub.wb_manager,
            plan_fact_reader=self._plan_fact_reader,
        )

        self._wb_api = wb_api
        self._access = wb_api.access
        self.shop_id = wb_api.shop_id
        self.__keywords_for_advs: dict[int, list[CalculatedKeyword]] = defaultdict(
            list[CalculatedKeyword]
        )
        self._adv_settings_dict: dict[int, AdvSetting] | None = None
        self._adv_settings_list: list[AdvSetting] | None = None
        self._session = wb_api.session
        self._redis_common_stat_timestamp_manager = RedisCommonStatTimestampManager(
            redis_client=redis_client_wrapper
        )
        self._redis_cluster_stat_timestamp_manager = RedisClusterStatTimestampManager(
            redis_client=redis_client_wrapper
        )
        self._redis_common_bid_timestamp_manager = RedisCommonBidTimestampManager(
            redis_client_wrapper
        )
        self._redis_common_bid_value_manager = RedisCommonBidValueManager(
            redis_client_wrapper
        )
        self._redis_auto_recommendations_bid_value_manager = (
            RedisAutoRecommendationsBidValueManager(redis_client_wrapper)
        )
        self._auto_budget_service = AutoBudgetService(redis_client_wrapper)
        self._tasks_manager = tasks_manager
        self._increment_fact_data_manager = IncrementFactDataManager(
            redis_client_wrapper,
        )
        self._auto_shelf_bid_increment_manager = AutoShelfBidIncrementManager(
            redis_client=redis_client_wrapper,
            wb_manager_hub=self._wb_manager_hub,
            auto_recommendations_bid_cache_manager=self._redis_auto_recommendations_bid_value_manager,
        )
        self._auto_shelf_bid_control_view_provider = AutoShelfBidControlViewProvider(
            redis_client=redis_client_wrapper,
            plan_fact_reader=self._plan_fact_reader,
        )
        self._auto_shelf_bid_control_manager = AutoShelfBidControlManager(
            bid_cache_manager=self._redis_auto_recommendations_bid_value_manager,
            wb_bid_setter=AutoShelfBidSetter(
                self._wb_manager_hub.wb_modifier,
                bid_cache_manager=self._redis_auto_recommendations_bid_value_manager,
            ),
        )
        self._redis_campaign_activity_reason_manager = RedisCampaignActivityReasonManager(
            redis_client_wrapper
        )
        self._adv_strategy_selector = AdvStrategySelector()
        self._redis_stats_freshness_cache = RedisStatsFreshnessStateCacheManager(
            redis_client_wrapper
        )
        # РџРѕРєР° РёРґС‘С‚ РїСЂРёРѕСЂРёС‚РµС‚РЅР°СЏ РґРѕРіСЂСѓР·РєР° miss вЂ” СЃР»РµРґСѓСЋС‰РёР№ С†РёРєР» old Р¶РґС‘С‚ Event.
        # РћС‚РґРµР»СЊРЅС‹Р№ Lock: Event РЅРµ РѕСЃС‚Р°РЅР°РІР»РёРІР°РµС‚ СѓР¶Рµ РЅР°С‡Р°С‚С‹Р№ refresh_min_bids_cache,
        # Р±РµР· Lock miss Рё old РјРѕРіР»Рё Р±С‹ РґРµСЂРіР°С‚СЊ WB API РїР°СЂР°Р»Р»РµР»СЊРЅРѕ (РЅР°РїСЂ. РїРѕСЃР»Рµ РѕР±С‰РµРіРѕ initial delay).
        self._min_bids_old_refresh_permitted = asyncio.Event()
        self._min_bids_old_refresh_permitted.set()
        self._min_bids_wb_refresh_lock = asyncio.Lock()


    @staticmethod
    def _max_workers_for(handler_count: int, cap: int) -> int:
        return max(1, min(handler_count, cap))

    async def _split_advs_by_stats_freshness(
        self,
        advs: list[ComplexAdv],
        *,
        operation_name: str,
    ) -> tuple[list[ComplexAdv], list[ComplexAdv]]:
        """Р Р°Р·РґРµР»СЏРµС‚ Р Рљ РЅР° fresh Рё stale_over_6h РїРѕ Redis-РєРµС€Сѓ СЃРІРµР¶РµСЃС‚Рё СЃС‚Р°С‚С‹.

        РџСЂРё ``settings.STATS_FRESHNESS_GUARD_ENABLED=False`` РІРѕР·РІСЂР°С‰Р°РµС‚ ``(advs, [])``
        Р±РµР· РѕР±СЂР°С‰РµРЅРёСЏ Рє Redis.
        """
        if not advs:
            return [], []
        if not settings.STATS_FRESHNESS_GUARD_ENABLED:
            logger.info(
                "stats_freshness_guard disabled: shop_id=%s op=%s total=%s",
                self.shop_id,
                operation_name,
                len(advs),
            )
            return advs, []
        adv_ids = [adv.adv_id for adv in advs]
        entries = await self._redis_stats_freshness_cache.mget_entries(
            self.shop_id, adv_ids
        )
        cache_hits = 0
        cache_misses = 0
        invalid_payloads = 0
        fresh: list[ComplexAdv] = []
        stale_over_6h: list[ComplexAdv] = []
        for adv, (_adv_id, state, kind, _cache_updated_at) in zip(
            advs, entries, strict=True
        ):
            assert adv.adv_id == _adv_id
            if kind == "hit":
                cache_hits += 1
            elif kind == "miss":
                cache_misses += 1
            else:
                invalid_payloads += 1
            if kind != "hit":
                logger.error(
                    "stats_freshness_cache fail-open (treat as fresh): shop_id=%s "
                    "adv_id=%s op=%s kind=%s",
                    self.shop_id,
                    adv.adv_id,
                    operation_name,
                    kind,
                )
                fresh.append(adv)
                continue
            assert state is not None
            if state.is_stale_over_6h:
                stale_over_6h.append(adv)
                if (
                    operation_name == "update_cluster_bids"
                    and is_trace_enabled()
                    and is_trace_cell(shop_id=self.shop_id, adv_id=adv.adv_id)
                ):
                    log_cluster_bid_trace(
                        step="tick_filtered",
                        shop_id=self.shop_id,
                        adv_id=adv.adv_id,
                        in_advs_filtred=False,
                        stale_reason="stale_over_6h",
                        stats_freshness_kind=kind,
                    )
            elif state.is_fresh:
                fresh.append(adv)
                if (
                    operation_name == "update_cluster_bids"
                    and is_trace_enabled()
                    and is_trace_cell(shop_id=self.shop_id, adv_id=adv.adv_id)
                ):
                    log_cluster_bid_trace(
                        step="tick_filtered",
                        shop_id=self.shop_id,
                        adv_id=adv.adv_id,
                        in_advs_filtred=True,
                        stale_reason="",
                        stats_freshness_kind=kind,
                    )
            else:
                if (
                    operation_name == "update_cluster_bids"
                    and is_trace_enabled()
                    and is_trace_cell(shop_id=self.shop_id, adv_id=adv.adv_id)
                ):
                    log_cluster_bid_trace(
                        step="tick_filtered",
                        shop_id=self.shop_id,
                        adv_id=adv.adv_id,
                        in_advs_filtred=False,
                        stale_reason=state.reason,
                        stats_freshness_kind=kind,
                    )
                logger.debug(
                    "Automation skipped by stale stats: shop_id=%s adv_id=%s op=%s reason=%s",
                    self.shop_id,
                    adv.adv_id,
                    operation_name,
                    state.reason,
                )
        logger.info(
            "stats_freshness_cache shop_id=%s op=%s hits=%s misses=%s invalid=%s total=%s",
            self.shop_id,
            operation_name,
            cache_hits,
            cache_misses,
            invalid_payloads,
            len(advs),
        )
        return fresh, stale_over_6h

    @while_coroutine_decorator(60, 5)
    async def refresh_stats_freshness_cache(self, only_bot_active: bool) -> None:
        """Р¤РѕРЅРѕРІРѕРµ РѕР±РЅРѕРІР»РµРЅРёРµ Redis-РєРµС€Р° РєР»Р°СЃСЃРёС„РёРєР°С†РёРё СЃРІРµР¶РµСЃС‚Рё СЃС‚Р°С‚С‹ (CH в†’ Redis)."""
        advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs(
            only_bot_active=only_bot_active,
            load_extras=False
        )
        if not advs:
            return None
        stats_freshness_manager = StatsFreshnessManager()
        entries: list[tuple[int, StatsFreshnessState]] = []
        for adv in advs:
            try:
                state = await stats_freshness_manager.evaluate(adv)
                entries.append((adv.adv_id, state))
            except Exception as exc:
                logger.error(
                    "Stats freshness evaluation failed in refresh coroutine: "
                    "shop_id=%s adv_id=%s err=%s",
                    self.shop_id,
                    adv.adv_id,
                    exc,
                    exc_info=True,
                )
        if entries:
            await self._redis_stats_freshness_cache.mset_states(self.shop_id, entries)
        return None

    @while_coroutine_decorator(1, 60)
    async def update_cpm_bid(self) -> None:
        advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs(
            load_extras=False
        )
        if not advs:
            return None
        advs = [adv for adv in advs if adv.bot_active]
        advs = [adv for adv in advs if adv.bidder_active]
        if not advs:
            return None
        advs = [
            adv
            for adv in advs
            if adv.bidder_coroutine_type == BidderCoroutineType.OLD_UPDATE_CPM_BIDDER
        ]
        advs, _ = await self._split_advs_by_stats_freshness(
            advs, operation_name="update_cpm_bid"
        )
        if not advs:
            return None
        logger.debug("РћР±РЅРѕРІР»СЏСЋ СЃС‚Р°РІРєРё РґР»СЏ РјР°РіР°Р·РёРЅР° %s", self.shop_id)
        handlers = [
            lambda complex_adv=adv: self.__run_bidder_process_for_adv(
                complex_adv, self._wb_api
            )
            for adv in advs
        ]
        max_workers = self._max_workers_for(len(handlers), cap=16)
        results = await run_tasks(
            handlers,
            max_workers=max_workers,
            tasks_manager=self._tasks_manager,
        )

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                adv_setting = advs[i]
                logger.error(
                    "РћС€РёР±РєР° РѕР±РЅРѕРІР»РµРЅРёСЏ Р Рљ : %s, adv_id: %s, shop_id: %s",
                    result,
                    adv_setting.adv_id,
                    self.shop_id,
                )


        logger.debug("Р’СЃРµ СЃС‚Р°РІРєРё РѕР±РЅРѕРІР»РµРЅС‹ РґР»СЏ РјР°РіР°Р·РёРЅР° %s", self.shop_id)
        return None

    async def __run_bidder_process_for_adv(
        self, complex_adv: ComplexAdv, wb_api: WBApi
    ) -> None:
        adv_setting: AdvSetting = complex_adv.adv_setting
        keywords = await complex_adv.get_keywords()
        v3_safety_cap_by_keyword_setting_original_id = (
            await build_v3_safety_cap_by_keyword_setting_original_id(
                complex_adv,
                keywords,
                wb_shop_data_manager=self._wb_shop_data_manager,
            )
        )
        await run_bidder_process_for_adv(
            adv_setting,
            wb_api,
            keywords,
            v3_safety_cap_by_keyword_setting_original_id=v3_safety_cap_by_keyword_setting_original_id,
        )

    @while_coroutine_decorator(60 * 5, 5)
    async def update_common_sale_stat(self, only_bot_active: bool = False) -> None:
        """Shop-wide coordinator: A/E/U partition, disjoint collect, coverage evidence."""
        from .services.common_sale_stat_updater import (
            CommonSaleStatUpdater,
            CommonSaleStatUpdaterContainer,
        )
        from .services.shop_wide_common_sales.coordinator import (
            run_shop_wide_common_sale_stat_tick,
        )

        wb_manager_hub = self._wb_manager_hub
        container = CommonSaleStatUpdaterContainer(_wb_manager_hub=wb_manager_hub)
        updater: CommonSaleStatUpdater = container.common_sale_stat_updater()

        _ = await run_shop_wide_common_sale_stat_tick(
            shop_id=self.shop_id,
            wb_manager_hub=wb_manager_hub,
            wb_shop_data_manager=self._wb_shop_data_manager,
            updater=updater,
            redis_client=wb_manager_hub.redis_client_wrapper,
            redis_common_stat_timestamp_manager=self._redis_common_stat_timestamp_manager,
        )
        return None

    @staticmethod
    async def _update_full_stat_in_click_house(stats: Iterable[FullAdvStat]) -> None:
        await full_wb_adv_stat.insert(stats)
        date_time = datetime.now()
        for stat in stats:
            await data_manager.set_last_full_stat_update(stat.advertId, date_time)


    @while_coroutine_decorator(5 * 60, 1)
    async def collect_shop_wide_campaign_advertising(self) -> None:
        """Shop-wide dual-path tick: discovery → route → inventory → unmanaged (§8.1).

        Spec ``connected-shop-campaign-ad-data-collection``.
        Debt: ``openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md``.
        Decision: ``decisions/shop-runner-shop-wide-collection/decision.md``.

        Managed RECORD coroutines остаются отдельными задачами ``WBShop.run``.
        Unmanaged slice стартует только при ``DUAL_PATH_ACTIVE`` per-shop flag.
        **MUST NOT** delegate to ``scripts/`` Job; **MUST NOT** management writes.
        """
        from ..shop_wide_collection.feature_flag import (
            ShopWideCollectionMode,
            apply_shop_wide_collection_gate,
        )
        from ..shop_wide_collection.tick_wiring import run_shop_wide_unmanaged_tick

        decision = apply_shop_wide_collection_gate(self.shop_id)
        if decision.mode is not ShopWideCollectionMode.DUAL_PATH_ACTIVE:
            return None

        loader_complex_advs = await self._wb_shop_data_manager.get_complex_advs(
            only_bot_active=False,
            load_extras=False,
        )
        _ = await run_shop_wide_unmanaged_tick(
            shop_id=self.shop_id,
            loader_complex_advs=loader_complex_advs,
            wb_manager_hub=self._wb_manager_hub,
        )
        return None

    @while_coroutine_decorator(5 * 60, 1)
    async def update_full_adv_stat(self, only_bot_active: bool = False) -> None:
        """Managed RECORD: ``full_adv_wb_stat`` для loader ``all_adv_ids`` (задача 5.1).

        Search legs включаются через ``ComplexAdv.all_adv_ids``. Unmanaged slice
        не дублирует grain для id из этого universe (resolver §B.1, S09/S14).
        """
        advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs(
            only_bot_active=only_bot_active,
            load_extras=False
        )
        all_adv_ids: set[int] = set()
        for adv in advs:
            all_adv_ids.update(adv.all_adv_ids)
        full_stats: list[FullAdvStat] = (
            await wb_data_getter.get_full_adv_stat_for_adv_ids(
                self._wb_manager_hub.wb_data_manager,
                all_adv_ids,
                threshold_dates=settings.FULL_STAT_THRESHOLD_DATES,
            )
        )
        if full_stats:
            await self._update_full_stat_in_click_house(full_stats)
        logger.info(
            "heartbeat update_full_adv_stat shop_id=%s adv_count=%s stats_rows=%s",
            self.shop_id,
            len(all_adv_ids),
            len(full_stats),
        )
        return None

    @staticmethod
    async def _update_cards_data_from_wb_to_pg(
        shop_data_updater: ShopDataUpdater,
    ) -> None:
        await shop_data_updater.update_cards_data()

    @while_coroutine_decorator(1 * 60)
    async def update_advs_data_from_wb_to_pg(self) -> None:
        from app.modules.wb_adv_updater import data_manager
        await data_manager.update_advs_data_from_wb_to_pg(
            self._wb_api,
            auto_recommendations_bid_cache_manager=self._redis_auto_recommendations_bid_value_manager,
        )
        return None


    @while_coroutine_decorator(60 * 15)
    async def update_cards_data_from_wb_to_pg(self) -> None:
        wb_api = self._wb_api
        shop_data_updater = ShopDataUpdater(wb_api)
        await self._update_cards_data_from_wb_to_pg(shop_data_updater)
        logger.debug("РћР±РЅРѕРІР»РµРЅРёРµ РєР°СЂС‚РѕС‡РµРє Р·Р°РІРµСЂС€РµРЅРѕ")

    @while_coroutine_decorator(60 * 60, 60)
    async def hierarchical_ad_control_diagnostics(self) -> None:
        """Read-only V1 diagnostics. Не пишет WB и не вызывает Apply."""
        if not settings.HIERARCHICAL_AD_CONTROL_DIAGNOSTICS_ENABLED:
            return None
        from app.modules.shop_runner.hierarchical_ad_control_diagnostics import (
            run_enabled_shop_diagnostics,
        )

        _ = await run_enabled_shop_diagnostics(
            shop_id=str(self.shop_id),
            reports_manager=self._wb_manager_hub.wb_data_manager.reports_manager,
        )
        return None

    @while_coroutine_decorator(5 * 60)
    async def adv_settings_auto_update(self, only_bot_active: bool = False) -> None:
        if not settings.AUTO_SETTING_ACTIVE:
            return None
        advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs(
            only_bot_active=only_bot_active,
            load_extras=False
        )
        advs = [adv for adv in advs if adv.bot_active]
        advs = [adv for adv in advs if adv.is_part_auto_setting_active]
        # V3 must tick while Search is PAUSE (empty-keywords pause, budget, etc.):
        # plan/fact Redis, tick report, and keyword state need refresh before resume.
        from .services.auto_updater_v3 import process_adv_v3
        from .services.auto_updater_v3.card_ab_hold.mode import (
            CardAbHoldMode,
            normalize_card_ab_hold_mode,
        )
        from .services.auto_updater_v3.card_ab_hold.pipelines import (
            process_ab_hold,
            process_ab_setup,
            process_ab_setup_then_epoch,
        )
        # TODO: РЈР±СЂР°Р» С„РёР»СЊС‚СЂР°С†РёСЋ РІ РєР°С‡РµСЃС‚РІРµ Р±С‹СЃС‚СЂРѕРіРѕ С„РёРєСЃР°, С‚.Рє. РЅРѕРІР°СЏ РјРѕРґРµР»СЊ v3 РѕС‚РєР»СЋС‡Р°Р»Р° РІСЃРµ РєР»СЋС‡Рё, Рё РїРѕС‚РѕРј РЅРµ РІРєР»СЋС‡Р°Р»Р°, РїРѕС‚РѕРјСѓ С‡С‚Рѕ СЃС‚Р°С‚Р° РєР»Р°СЃС‚РµСЂРѕРІ РЅРµ СЃРІРµР¶Р°СЏ, Р° РѕРЅР° РЅРµ СЃРІРµР¶Р°СЏ, РїРѕС‚РѕРјСѓ С‡С‚Рѕ РєР»СЋС‡Рё РІСЃРµ OFF
        handlers: list[Callable[[], Awaitable[Any]]] = []
        # Spec/decision card-ab-hold В§2a: setup/hold РёР· РїРѕР»РЅРѕРіРѕ advs (РЅРµ С‚РѕР»СЊРєРѕ
        # advs_filtred) вЂ” РёРЅР°С‡Рµ PENDING Р·Р°РІРёСЃР°РµС‚ РїСЂРё stale РїРѕСЃР»Рµ ENTER.
        from .services.auto_updater_v3.card_ab_hold.scheduling import (
            filter_ab_hold_pipeline_candidates,
            should_run_ab_epoch,
        )

        fresh_advs, _stale_advs = await self._split_advs_by_stats_freshness(
            advs, operation_name="adv_settings_auto_update_ab_hold"
        )
        fresh_ids = {int(adv.adv_id) for adv in fresh_advs}

        ab_hold_candidates = filter_ab_hold_pipeline_candidates(advs)
        if ab_hold_candidates:
            await self._wb_shop_data_manager.attach_leg_cpo(
                [adv for adv, _mode in ab_hold_candidates]
            )
        for adv, ab_mode in ab_hold_candidates:
            stats_fresh = int(adv.adv_id) in fresh_ids
            if ab_mode == CardAbHoldMode.PENDING_SETUP:
                phase = getattr(adv.adv_setting, "card_ab_hold_phase", None)
                if should_run_ab_epoch(ab_mode, phase):
                    # PBH-006 / В§18.4.2: Classification FAILв†’OFF still via setup
                    # (epoch_managed=True); epoch tick owns WARM_UP/sync/ACTIVE.
                    # PERF-003: one serial handler (setupв†’epoch), not two parallel.
                    handlers.append(
                        functools.partial(
                            process_ab_setup_then_epoch,
                            adv,
                            wb_shop_data_manager=self._wb_shop_data_manager,
                            wb_manager_hub=self._wb_manager_hub,
                            stats_fresh=stats_fresh,
                        )
                    )
                else:
                    handlers.append(
                        functools.partial(
                            process_ab_setup,
                            adv,
                            wb_shop_data_manager=self._wb_shop_data_manager,
                            wb_manager_hub=self._wb_manager_hub,
                            stats_fresh=stats_fresh,
                        )
                    )
                continue
            if ab_mode == CardAbHoldMode.ACTIVE:
                handlers.append(
                    functools.partial(
                        process_ab_hold,
                        adv,
                        wb_shop_data_manager=self._wb_shop_data_manager,
                        wb_manager_hub=self._wb_manager_hub,
                        stats_fresh=stats_fresh,
                    )
                )
                continue

        for adv in advs:
            ab_mode = normalize_card_ab_hold_mode(adv.card_ab_hold_mode)
            if ab_mode != CardAbHoldMode.OFF:
                continue
            handlers.append(
                functools.partial(
                    process_adv_v3,
                    adv,
                    wb_shop_data_manager=self._wb_shop_data_manager,
                )
            )

        if not handlers:
            return None

        max_workers = self._max_workers_for(len(handlers), cap=16)
        _ = await run_tasks(
            handlers,
            max_workers=max_workers,
            return_exceptions=False,
            tasks_manager=self._tasks_manager,
        )
        return None

    @while_coroutine_decorator(60, 1)
    async def update_top_key_in_advs(self, only_bot_active: bool = False) -> None:
        """Legacy V2 FirstKeyUpdater path вЂ” retired; bot off has no auto-updater runtime."""
        return None

    @while_coroutine_decorator(15, 60)
    async def delete_keywords_from_wl_by_mean_auto_ctr(self) -> None:
        # TODO: Р”РѕР±Р°РІРёС‚СЊ С„СѓРЅРєС†РёСЋ-С„РёР»СЊС‚СЂ РґР»СЏ ComplexAdvs getter
        complex_advs: Sequence[ComplexAdv] = (
            await self._wb_shop_data_manager.get_complex_advs(load_extras=False)
        )
        complex_advs_with_white_list_by_mean_auto_ctr_active = [
            adv
            for adv in complex_advs
            if adv.rec_system_promotion_mode_active
            and adv.is_white_list_control_enabled
            and adv.bot_active
        ]
        complex_advs_with_white_list_by_mean_auto_ctr_active, _ = (
            await self._split_advs_by_stats_freshness(
                complex_advs_with_white_list_by_mean_auto_ctr_active,
                operation_name="delete_keywords_from_wl_by_mean_auto_ctr",
            )
        )
        # Spec card-ab-hold-mode: filter before WL mutation / WB write boundary.
        from .services.auto_updater_v3.card_ab_hold.scheduling import (
            filter_structural_act_candidates,
        )

        complex_advs_with_white_list_by_mean_auto_ctr_active = (
            filter_structural_act_candidates(
                complex_advs_with_white_list_by_mean_auto_ctr_active
            )
        )

        handlers: list[Callable[[], Awaitable[Any]]] = []
        for adv in complex_advs_with_white_list_by_mean_auto_ctr_active:
            handlers.append(
                lambda complex_adv=adv: delete_keywords_from_wl_by_mean_auto_ctr(
                    complex_adv=complex_adv
                )
            )

        if not handlers:
            return None

        results: Sequence[None | BaseException] = await run_tasks(
            handlers,
            max_workers=self._max_workers_for(len(handlers), cap=16),
        )

        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                logger.error(
                    "РћС€РёР±РєР° СѓРґР°Р»РµРЅРёСЏ РєР»СЋС‡РµР№ РёР· Р‘РЎ РїРѕ СЃСЂРµРґ.Р°РІС‚Рѕ СЃС‚СЂ, shop_id: %s, adv_id: %s)",
                    self.shop_id,
                    complex_advs[i].adv_id,
                )

        return None

    @while_coroutine_decorator(1, 60)
    async def update_keywords_stamp(self) -> None:
        from .services.keyword_stamp_manager import (
            KeywordStampManagerContainer,
            KeywordStampManager,
        )

        wb_manager_hub = self._wb_manager_hub
        keyword_stamp_manager_container = KeywordStampManagerContainer(
            _wb_api_manager_hub=wb_manager_hub
        )
        keyword_stamp_manager: KeywordStampManager = (
            keyword_stamp_manager_container.keyword_stamp_manager()
        )

        advs = await self._wb_shop_data_manager.get_complex_advs(load_extras=False)
        if not advs:
            return None
        handlers: list[Callable[[], Awaitable[Any]]] = []
        for adv in advs:
            handlers.append(
                lambda complex_adv=adv: keyword_stamp_manager.update_keywords_position_stamp(
                    complex_adv
                )
            )

        results: list[BaseException | None] = await run_tasks(
            handlers,
            max_workers=self._max_workers_for(len(handlers), cap=16),
        )

        for result in results:
            if isinstance(result, BaseException):
                logger.error(
                    "РћС€РёР±РєР° РѕР±РЅРѕРІР»РµРЅРёСЏ РїРѕР·РёС†РёР№ РёР· Api: %s", result, exc_info=True
                )

        return None

    @while_coroutine_decorator(24 * 60 * 60 * 60, 60)
    async def update_keywords_positions_history(self) -> None:
        from .services.keyword_stamp_manager import (
            KeywordStampManagerContainer,
            KeywordStampManager,
        )

        wb_manager_hub = self._wb_manager_hub
        keyword_stamp_manager_container = KeywordStampManagerContainer(
            _wb_api_manager_hub=wb_manager_hub
        )
        keyword_stamp_manager: KeywordStampManager = (
            keyword_stamp_manager_container.keyword_stamp_manager()
        )

        advs = await self._wb_shop_data_manager.get_complex_advs(load_extras=False)
        if not advs:
            return None
        handlers: list[Callable[[], Awaitable[Any]]] = []
        for adv in advs:
            handlers.append(
                lambda complex_adv=adv: keyword_stamp_manager.update_keyword_history(
                    complex_adv
                )
            )

        results: list[BaseException | None] = await run_tasks(
            handlers,
            max_workers=self._max_workers_for(len(handlers), cap=16),
        )

        for result in results:
            if isinstance(result, Exception):
                logger.error(
                    "РћС€РёР±РєР° РѕР±РЅРѕРІР»РµРЅРёСЏ РїРѕР·РёС†РёР№ РёР· Api: %s", result, exc_info=True
                )

        return None

    @while_coroutine_decorator(15, 60)
    async def update_minus_phrases_in_advs(self, only_bot_active: bool) -> None:
        """Фон автоминусов по ``auto_update_minus_phrases`` (free-пакет, default off).

        Это отдельный free write-path: явный флаг
        ``auto_update_minus_phrases`` является единственным продуктовым
        допуском, поэтому ``bot_active=False`` не блокирует синхронизацию.
        ``bot_active`` — gate платной автоматизации, а не автоминусов.
        A/B Hold PENDING/ACTIVE исключены (decision §8).
        """
        from .services.auto_updater_v3.card_ab_hold.scheduling import (
            filter_structural_act_candidates,
        )
        from .services.minus_phrase_manager import MinusPhraseManagerContainer

        wb_manager_hub = self._wb_manager_hub
        container = MinusPhraseManagerContainer(_wb_api_manager_hub=wb_manager_hub)
        minus_phrase_manager = container.minus_phrase_manager()

        complex_advs = await self._wb_shop_data_manager.get_complex_advs(
            only_bot_active=only_bot_active,
            load_extras=False
        )
        # Free package: автоминусы по флагу, без требования bot_active (paid).
        complex_advs = [
            adv for adv in complex_advs if adv.auto_update_minus_phrases
        ]
        # Spec card-ab-hold-mode В§8: filter before MinusPhraseManager / WB write.
        complex_advs = filter_structural_act_candidates(complex_advs)
        handlers: list[Callable[[], Awaitable[Any]]] = [
            lambda complex_adv_=adv: minus_phrase_manager.update_minus_phrases(
                complex_adv_
            )
            for adv in complex_advs
        ]

        if not handlers:
            return None

        results: list[BaseException | None] = await run_tasks(
            handlers,
            max_workers=self._max_workers_for(len(handlers), cap=16),
            tasks_manager=self._tasks_manager,
        )

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "РћС€РёР±РєР° РѕР±РЅРѕРІР»РµРЅРёСЏ РјРёРЅСѓСЃ С„СЂР°Р· РґР»СЏ shop_id: %s, adv_id: %s, РѕС€РёР±РєР°: %s",
                    complex_advs[i].shop_id,
                    complex_advs[i].adv_id,
                    result,
                    exc_info=True,
                )
        return None

    @while_coroutine_decorator(60, 60)
    async def auto_budget_watchdog(self, only_bot_active: bool = False) -> None:
        """Пополнить бюджеты, затем выполнить activity control кампаний.

        Перед refresh создаются ``ComplexAdv`` из уже сохранённого Redis
        promo-overlay. ``refresh_promo_state`` читает WB/PG, записывает
        более свежий snapshot и сразу пришивает его к этим DTO. Поэтому
        budget/activity paths используют новый promo multiplier в текущем
        watchdog-тике; при cache miss/stale остаётся консервативная база
        ``M=1``.

        Activity control запускается в ``finally`` каждого тика, в том числе
        если для auto-budget не нашлось кандидатов.
        """
        advs = await self._wb_shop_data_manager.get_complex_advs(only_bot_active=only_bot_active, load_extras=False)
        await self._wb_shop_data_manager.attach_leg_cpo(advs)
        try:
            await self._auto_budget_service.refresh_promo_state(
                advs,
                self._wb_manager_hub,
                self.shop_id,
            )
            if not advs:
                return None
            from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.emergency import (
                should_suppress_budget_and_activity_restart,
            )

            candidates: list[ComplexAdv] = [
                adv
                for adv in advs
                if adv.auto_budget_watchdog_enabled
                and not should_suppress_budget_and_activity_restart(
                    getattr(adv.adv_setting, "card_ab_hold_emergency_latch", False)
                )
                and (
                    (
                        adv.use_common_budget
                        and (adv.common_budget_daily_limit or 0) > 0
                        and (adv.adv_id or adv.search_adv_id)
                    )
                    or (
                        not adv.use_common_budget
                        and (
                            ((adv.auto_budget_daily_limit or 0) > 0 and adv.adv_id)
                            or (
                                (adv.search_auto_budget_daily_limit or 0) > 0
                                and adv.search_adv_id
                            )
                        )
                    )
                )
            ]
            wb_manager_hub = self._wb_manager_hub
            handlers: list[Callable[[], Awaitable[AutoBudgetEnsureResult | None]]] = []
            task_specs: list[tuple[AdvSetting, AdvType, int | None]] = []

            for adv in candidates:
                adv_setting = adv.adv_setting
                adv_setting_id = adv_setting.id
                if adv.use_common_budget:
                    handlers.append(
                        lambda adv_=adv,
                               adv_setting_id_=adv_setting_id,
                               wb_manager_hub_=wb_manager_hub: (
                            self._auto_budget_service.ensure_common_budget(
                                adv_,
                                adv_setting_id_,
                                wb_manager_hub_,
                            )
                        )
                    )
                    task_specs.append((adv_setting, AdvType.AUTO, None))
                else:
                    campaign_checks: list[tuple[AdvType, int]] = []
                    if (adv.auto_budget_daily_limit or 0) > 0 and adv.adv_id:
                        campaign_checks.append((AdvType.AUTO, adv.adv_id))
                    if (adv.search_auto_budget_daily_limit or 0) > 0 and adv.search_adv_id:
                        campaign_checks.append(
                            (AdvType.SEARCH, adv.search_adv_id)
                        )
                    for campaign_type, adv_id in campaign_checks:
                        handlers.append(
                            lambda  adv_=adv,
                            adv_setting_id_=adv_setting_id,
                                   campaign_type_=campaign_type,
                                   wb_manager_hub_=wb_manager_hub: (
                                self._auto_budget_service.ensure_budget(
                                    adv_,
                                    adv_setting_id_,
                                    campaign_type_,
                                    wb_manager_hub_,
                                )
                            )
                        )
                        task_specs.append((adv_setting, campaign_type, adv_id))

            if not handlers:
                return None

            max_workers = self._max_workers_for(len(handlers), cap=16)
            results = await run_tasks(
                handlers,
                max_workers=max_workers,
                tasks_manager=self._tasks_manager,
            )

            for (adv_setting, spec_campaign_type, spec_adv_id), result in zip(
                task_specs, results
            ):
                if isinstance(result, Exception):
                    logger.error(
                        "Auto budget ensure failed for shop_id=%s, adv_id=%s, campaign=%s: %s",
                        self.shop_id,
                        spec_adv_id,
                        spec_campaign_type,
                        result,
                        exc_info=True,
                    )
                    continue
                if result is not None:
                    self._log_auto_budget_result(
                        adv_setting,
                        result,
                        result.campaign_type,
                        result.adv_id,
                    )
            return None
        finally:
            await self._run_auto_adv_active_control(advs)
            logger.info(
                "heartbeat auto_budget_watchdog shop_id=%s advs=%s",
                self.shop_id,
                len(advs),
            )

    async def _run_auto_adv_active_control(self, advs: list[ComplexAdv]) -> None:
        wb_manager_hub = self._wb_manager_hub
        service = AutoAdvActiveControlService(
            wb_modifier=wb_manager_hub.wb_modifier,
            tasks_manager=self._tasks_manager,
            plan_fact_reader=self._plan_fact_reader,
            auto_shelf_bid_control_view_provider=self._auto_shelf_bid_control_view_provider,
            redis_campaign_activity_reason_manager=self._redis_campaign_activity_reason_manager,
            budget_ensure_before_start_retry=self._ensure_budget_for_campaign_start_retry,
        )
        await service.ensure_campaigns_active(advs)
        return None

    async def _ensure_budget_for_campaign_start_retry(
        self,
        adv: ComplexAdv,
        kind: str,
    ) -> None:
        """РџРѕРІС‚РѕСЂРЅС‹Р№ ensure РїРѕСЃР»Рµ РѕС‚РІРµС‚Р° WB Low Budget РЅР° СЃС‚Р°СЂС‚ Р Рљ.

        ``force_after_start_rejection`` РѕР±С…РѕРґРёС‚ РіРµР№С‚ В«stale full adv statsВ», РёРЅР°С‡Рµ
        РїРѕРІС‚РѕСЂРЅС‹Р№ ensure СЃСЂР°Р·Сѓ РІРѕР·РІСЂР°С‰Р°РµС‚ NOT_NEW_ADV_STATS Р±РµР· РїРѕРїРѕР»РЅРµРЅРёСЏ.
        """
        hub = self._wb_manager_hub
        setting_id = adv.adv_setting.id
        force = True
        if adv.use_common_budget:
            failure_ct = (
                AdvType.SEARCH if kind == "search" else AdvType.AUTO
            )
            _ = await self._auto_budget_service.ensure_common_budget(
                adv,
                setting_id,
                hub,
                force_after_start_rejection=force,
                start_failure_campaign=failure_ct,
            )
            return
        if kind == "search" and (adv.search_auto_budget_daily_limit or 0) > 0 and adv.search_adv_id:
            _ = await self._auto_budget_service.ensure_budget(
                adv,
                setting_id,
                AdvType.SEARCH,
                hub,
                force_after_start_rejection=force,
            )
            return
        if kind == "auto" and (adv.auto_budget_daily_limit or 0) > 0 and adv.adv_id:
            _ = await self._auto_budget_service.ensure_budget(
                adv,
                setting_id,
                AdvType.AUTO,
                hub,
                force_after_start_rejection=force,
            )

    @while_coroutine_decorator(5 * 60, 60)
    async def update_clusters_adv_stats_today(self, only_bot_active: bool = False) -> None:
        """Managed RECORD: clusters today для loader universe §B.1 (задачи 5.1, 5.2).

        ``refused`` с непустыми ``nmids`` остаётся в universe и **MAY** получить
        ``update_clusters_adv_stats_*``. Grain managed-only — unmanaged collector
        не пишет ``clusters_adv_stats``.
        """

        diag_enabled = _cluster_stats_diagnostic_enabled()
        started_at = time.perf_counter()
        wb_manager_hub = self._wb_manager_hub
        container = ClustersAdvStatUpdaterContainer(
            _wb_manager_hub=wb_manager_hub
        )
        updater: ClustersAdvStatUpdater = (
            container.clusters_adv_stat_updater()
        )
        complex_advs = await self._wb_shop_data_manager.get_complex_advs(
            only_bot_active=only_bot_active,
            load_extras=False
        )
        if diag_enabled:
            logger.debug(
                "cluster_stats_diagnostic step=start shop_id=%s complex_advs_count=%s",
                self.shop_id,
                len(complex_advs),
            )
        if not complex_advs:
            elapsed_sec = time.perf_counter() - started_at
            logger.warning(
                "cluster_stats_diagnostic step=empty shop_id=%s complex_advs_count=0 "
                "updated_original_adv_ids_count=0 duration_sec=%.3f "
                "timestamp_not_updated=true",
                self.shop_id,
                elapsed_sec,
            )
            return None
        try:
            updated_original_adv_ids = await updater.update_today_stats(
                complex_advs
            )
        except Exception as exc:
            elapsed_sec = time.perf_counter() - started_at
            logger.exception(
                "cluster_stats_diagnostic step=error shop_id=%s complex_advs_count=%s "
                "updated_original_adv_ids_count=0 duration_sec=%.3f "
                "exception_type=%s exception_message=%s timestamp_not_updated=true",
                self.shop_id,
                len(complex_advs),
                elapsed_sec,
                type(exc).__name__,
                exc,
            )
            raise
        if not updated_original_adv_ids:
            elapsed_sec = time.perf_counter() - started_at
            logger.warning(
                "cluster_stats_diagnostic step=skipped shop_id=%s "
                "complex_advs_count=%s updated_original_adv_ids_count=0 "
                "duration_sec=%.3f timestamp_not_updated=true",
                self.shop_id,
                len(complex_advs),
                elapsed_sec,
            )
            return None
        if diag_enabled:
            logger.debug(
                "cluster_stats_diagnostic step=end shop_id=%s complex_advs_count=%s "
                "updated_original_adv_ids_count=%s",
                self.shop_id,
                len(complex_advs),
                len(updated_original_adv_ids),
            )
        for adv_orig_id in updated_original_adv_ids:
            try:
                await self._redis_cluster_stat_timestamp_manager.set(adv_orig_id)
            except Exception as exc:
                elapsed_sec = time.perf_counter() - started_at
                logger.exception(
                    "cluster_stats_diagnostic step=error shop_id=%s "
                    "original_adv_id=%s updated_original_adv_ids_count=%s "
                    "duration_sec=%.3f exception_type=%s exception_message=%s "
                    "timestamp_not_updated=true",
                    self.shop_id,
                    adv_orig_id,
                    len(updated_original_adv_ids),
                    elapsed_sec,
                    type(exc).__name__,
                    exc,
                )
                raise

        return None

    @while_coroutine_decorator(24 * 60 * 60, 60)
    async def update_clusters_adv_stats_history(self, only_bot_active: bool = False) -> None:
        """Managed RECORD: clusters history для loader universe §B.1 (задачи 5.1, 5.2).

        Парный history path для ``refused`` и прочих non-``done`` строк loader'а.
        """
        wb_manager_hub = self._wb_manager_hub
        container = ClustersAdvStatUpdaterContainer(_wb_manager_hub=wb_manager_hub)
        updater: ClustersAdvStatUpdater = container.clusters_adv_stat_updater()
        complex_advs = await self._wb_shop_data_manager.get_complex_advs(
            only_bot_active=only_bot_active,
            load_extras=False
        )
        await updater.update_past_days_stats(complex_advs, for_last_days=365)

    @while_coroutine_decorator(60 * 5, 60)
    async def update_cluster_bids(self, only_bot_active: bool = False) -> None:
        if not settings.AUTO_SETTING_ACTIVE:
            return None
        from .services.update_cluster_bids_manager.di import ClusterBidsManagerContainer
        wb_manager_hub = self._wb_manager_hub
        container = ClusterBidsManagerContainer(
            shop_id=self.shop_id,
            redis_client=wb_manager_hub.redis_client_wrapper,
            tasks_manager=self._tasks_manager,
            plan_fact_reader=self._plan_fact_reader,
        )
        update_clusters_bid_manager = container.update_cluster_bids_manager()
        all_advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs(
            only_bot_active=only_bot_active,
            load_extras=False
        )
        trace_defaults = trace_target_defaults()
        trace_adv_id = trace_defaults.get("adv_id")
        trace_adv = next(
            (adv for adv in all_advs if adv.adv_id == trace_adv_id),
            None,
        ) if trace_adv_id is not None else None
        if trace_adv_id is not None and is_trace_cell(
            shop_id=self.shop_id, adv_id=trace_adv_id
        ):
            log_cluster_bid_trace(
                step="tick_enter",
                shop_id=self.shop_id,
                adv_id=trace_adv_id,
                in_complex_advs=trace_adv is not None,
                bot_active=trace_adv.bot_active if trace_adv is not None else None,
                bidder_active=trace_adv.bidder_active if trace_adv is not None else None,
            )
        advs = [adv for adv in all_advs if adv.bot_active]
        advs = [
            adv
            for adv in advs
            if adv.bidder_active
        ]
        if trace_adv_id is not None and is_trace_cell(
            shop_id=self.shop_id, adv_id=trace_adv_id
        ):
            log_cluster_bid_trace(
                step="tick_pre_stale",
                shop_id=self.shop_id,
                adv_id=trace_adv_id,
                passed_bot_active=trace_adv.bot_active if trace_adv is not None else None,
                passed_bidder_active=trace_adv.bidder_active if trace_adv is not None else None,
                in_bot_bidder_filtered=trace_adv is not None
                and trace_adv.adv_id in {adv.adv_id for adv in advs},
            )

        advs_filtred, _ = await self._split_advs_by_stats_freshness(
            advs, operation_name="update_cluster_bids"
        )
        if not advs_filtred:
            return None


        await update_clusters_bid_manager.update_cluster_bids(advs_filtred)
        logger.info(
            "heartbeat update_cluster_bids shop_id=%s advs=%s",
            self.shop_id,
            len(advs_filtred),
        )
        return None

    @while_coroutine_decorator(60 * 5, 60)
    async def cache_current_cluster_bids(self, only_bot_active: bool = False) -> None:
        # TODO: РћС‡РµРЅСЊ РґРѕР»РіРѕ СЂР°Р±РѕС‚Р°РµС‚, РЅР°РґРѕ РѕРїС‚РёРјРёР·РёСЂРѕРІР°С‚СЊ
        """Fetch current normquery bids from WB API and warm Redis for cluster bid reads."""
        if not settings.AUTO_SETTING_ACTIVE:
            return None
        from .services.update_cluster_bids_manager.di import ClusterBidsManagerContainer

        wb_manager_hub = self._wb_manager_hub
        container = ClusterBidsManagerContainer(
            shop_id=self.shop_id,
            redis_client=wb_manager_hub.redis_client_wrapper,
            tasks_manager=self._tasks_manager,
        )
        wb_manager = container.wb_manager()
        redis_api_cluster_bids_manager = container.redis_api_cluster_bids_manager()

        advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs(
            only_bot_active=only_bot_active,
            load_extras=False
        )
        advs = [adv for adv in advs if adv.bot_active]
        if not advs:
            return None

        try:
            bids = await wb_manager.get_current_bids(advs)
            written = await redis_api_cluster_bids_manager.replace_from_api(bids)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "cache_current_cluster_bids failed shop_id=%s: %s",
                self.shop_id,
                exc,
                exc_info=True,
            )
            return None
        logger.info(
            "Cached current cluster bids from WB API: shop_id=%s fetched=%s written=%s",
            self.shop_id,
            len(bids),
            written,
        )
        return None

    @while_coroutine_decorator(60 * 60, 60)
    async def preload_min_bids_cache_miss(self, only_bot_active: bool = False) -> None:
        """РџСЂРёРѕСЂРёС‚РµС‚РЅР°СЏ РґРѕРіСЂСѓР·РєР° cache miss РїРѕ min bids; РЅР° РІСЂРµРјСЏ Р·Р°РїСЂРѕСЃР° Р±Р»РѕРєРёСЂСѓРµС‚ old-РІРµС‚РєСѓ С‡РµСЂРµР· Event.

        Р”Рѕ Р·Р°РІРµСЂС€РµРЅРёСЏ РґРѕРіСЂСѓР·РєРё ``read_min_bids_cache_only`` РјРѕР¶РµС‚ РїРёСЃР°С‚СЊ WARNING
        ``min_bids cache miss`` (РЅРµ ERROR) вЂ” СЃРј. ``docks/snapshot_data_updater.md``.
        """
        if not settings.AUTO_SETTING_ACTIVE:
            return None
        from .services.update_cluster_bids_manager.di import ClusterBidsManagerContainer

        wb_manager_hub = self._wb_manager_hub
        container = ClusterBidsManagerContainer(
            shop_id=self.shop_id,
            redis_client=wb_manager_hub.redis_client_wrapper,
            tasks_manager=self._tasks_manager,
        )
        wb_manager = container.wb_manager()
        t0 = time.perf_counter()
        advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs(
            only_bot_active=only_bot_active,
            load_extras=False
        )
        advs = [adv for adv in advs if adv.bot_active]
        if not advs:
            return None
        miss_cells_count = 0
        miss_written = 0
        try:
            miss_cells = await wb_manager.find_min_bids_cache_miss_cells(advs)
            miss_cells_count = len(miss_cells)
            if not miss_cells:
                return None
            self._min_bids_old_refresh_permitted.clear()
            try:
                async with self._min_bids_wb_refresh_lock:
                    miss_written = await wb_manager.refresh_min_bids_cache_miss_cells(
                        miss_cells
                    )
                _ = await wb_manager.find_min_bids_cache_miss_cells(
                    advs,
                    emit_app_log=True,
                    log_label="min_bids_cache_miss after refresh",
                )
            finally:
                self._min_bids_old_refresh_permitted.set()
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "preload_min_bids_cache_miss failed shop_id=%s: %s",
                self.shop_id,
                exc,
                exc_info=True,
            )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "preload_min_bids_cache_miss done shop_id=%s miss_cells=%s "
            "miss_written=%s advs=%s elapsed_ms=%.0f",
            self.shop_id,
            miss_cells_count,
            miss_written,
            len(advs),
            elapsed_ms,
        )
        return None

    @while_coroutine_decorator(60 * 60 * 12, 60)
    async def preload_min_bids_cache_old(self, only_bot_active: bool = False) -> None:
        """Р¤РѕРЅРѕРІРѕРµ РѕР±РЅРѕРІР»РµРЅРёРµ СѓР¶Рµ Р·Р°РєСЌС€РёСЂРѕРІР°РЅРЅС‹С… min bids; Р¶РґС‘С‚ Event, РїРѕРєР° РёРґС‘С‚ miss-РґРѕРіСЂСѓР·РєР°."""
        if not settings.AUTO_SETTING_ACTIVE:
            return None
        from .services.update_cluster_bids_manager.di import ClusterBidsManagerContainer

        wb_manager_hub = self._wb_manager_hub
        container = ClusterBidsManagerContainer(
            shop_id=self.shop_id,
            redis_client=wb_manager_hub.redis_client_wrapper,
            tasks_manager=self._tasks_manager,
        )
        wb_manager = container.wb_manager()
        t0 = time.perf_counter()
        advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs(
            only_bot_active=only_bot_active,
            load_extras=False
        )
        advs = [adv for adv in advs if adv.bot_active]
        if not advs:
            return None
        try:
            _ = await self._min_bids_old_refresh_permitted.wait()
            async with self._min_bids_wb_refresh_lock:
                await wb_manager.refresh_min_bids_cache(advs)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "preload_min_bids_cache_old failed shop_id=%s: %s",
                self.shop_id,
                exc,
                exc_info=True,
            )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "preload_min_bids_cache_old done shop_id=%s advs=%s elapsed_ms=%.0f",
            self.shop_id,
            len(advs),
            elapsed_ms,
        )
        return None

    @while_coroutine_decorator(60 * 5, 60)
    async def handle_stats_stale_emergency(self, only_bot_active: bool = True) -> None:
        """Emergency mode: stale stats over 6 hours => keep one top key and min bid."""
        complex_advs = await self._wb_shop_data_manager.get_complex_advs(
            only_bot_active=only_bot_active,
            load_extras=False
        )
        complex_advs = [adv for adv in complex_advs if adv.bot_active]
        complex_advs = [adv for adv in complex_advs if adv.is_part_auto_setting_active]
        from .services.auto_updater_v3.card_ab_hold.scheduling import (
            filter_structural_act_candidates,
        )

        # Spec card-ab-hold-mode: no emergency structural mutations on PENDING/ACTIVE.
        complex_advs = filter_structural_act_candidates(complex_advs)
        if not complex_advs:
            return None
        _, stale_over_6h = await self._split_advs_by_stats_freshness(
            complex_advs, operation_name="handle_stats_stale_emergency"
        )
        if not stale_over_6h:
            return None

        handlers: list[Callable[[], Awaitable[None]]] = [
            lambda adv_=adv: self._apply_stats_stale_emergency(adv_) for adv in stale_over_6h
        ]
        results = await run_tasks(
            handlers,
            max_workers=self._max_workers_for(len(handlers), cap=16),
            tasks_manager=self._tasks_manager,
            return_exceptions=True,
        )
        for adv, result in zip(stale_over_6h, results):
            if isinstance(result, BaseException):
                logger.error(
                    "Emergency stale-stats handling failed: shop_id=%s adv_id=%s err=%s",
                    self.shop_id,
                    adv.adv_id,
                    result,
                    exc_info=True,
                )
        return None

    async def _apply_stats_stale_emergency(self, complex_adv: ComplexAdv) -> None:
        keywords = await complex_adv.get_keywords()
        candidates = [kw for kw in keywords if kw.hard_status in (1, 2)]
        if complex_adv.auto_add_only_relevant_phrase:
            candidates = [kw for kw in candidates if kw.relevant]
        if not candidates:
            if complex_adv.auto_add_only_relevant_phrase:
                logger.warning(
                    "Emergency stale-stats handling skipped (no relevant candidates): "
                    "shop_id=%s adv_id=%s",
                    self.shop_id,
                    complex_adv.adv_id,
                )
            return None
        top_keyword = max(candidates, key=lambda kw: kw.rating or 0)
        top_keyword_id = top_keyword.keyword_setting_original_id
        candidate_ids = [kw.keyword_setting_original_id for kw in candidates]
        demote_ids = [kw_id for kw_id in candidate_ids if kw_id != top_keyword_id]

        async with sm(read_only=False) as session:
            if demote_ids:
                stmt_demote = update(KeywordSetting).where(
                    KeywordSetting.id.in_(demote_ids)
                )
                if is_v3_campaign(complex_adv.bot_active):
                    stmt_demote = stmt_demote.values(
                        hard_status=1,
                        strategy_mode=KeywordStrategyMode.OFF,
                    )
                else:
                    stmt_demote = stmt_demote.values(hard_status=1)
                _ = await session.execute(stmt_demote)
            stmt_promote = update(KeywordSetting).where(
                KeywordSetting.id == top_keyword_id
            )
            if is_v3_campaign(complex_adv.bot_active):
                stmt_promote = stmt_promote.values(
                    hard_status=2,
                    strategy_mode=keyword_strategy_mode_for_adv_strategy(
                        complex_adv.strategy
                    ),
                )
            else:
                stmt_promote = stmt_promote.values(hard_status=2)
            _ = await session.execute(stmt_promote)
            await session.commit()

        await self._set_min_search_bid_for_keyword(complex_adv, top_keyword.text)
        logger.warning(
            "Emergency stale-stats mode applied: shop_id=%s adv_id=%s top_keyword=%s",
            self.shop_id,
            complex_adv.adv_id,
            top_keyword.text,
        )
        return None

    async def _set_min_search_bid_for_keyword(
        self, complex_adv: ComplexAdv, keyword_text: str
    ) -> None:
        search_adv_id = complex_adv.auction_adv_id
        if search_adv_id is None:
            return None
        wb_manager_hub = self._wb_manager_hub
        min_bids = await wb_manager_hub.wb_manager.get_min_bids_cache_only(
            [complex_adv],
            context="stats_stale_emergency_set_min_search_bid",
        )
        missing_nmids = [nmid for nmid in complex_adv.nmids if nmid not in min_bids.search]
        if missing_nmids:
            logger.warning(
                "stats_stale_emergency: min search bids cache miss, fallback to WB API "
                "shop_id=%s adv_id=%s missing_nmids=%s",
                self.shop_id,
                complex_adv.adv_id,
                missing_nmids,
            )
            try:
                fresh_min_bids = await wb_manager_hub.wb_manager.get_min_bids(
                    [complex_adv],
                    cache_possible=False,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "stats_stale_emergency: fallback WB API get_min_bids failed; "
                    "refusing emergency search bid update to avoid unsafe default bid "
                    "shop_id=%s adv_id=%s missing_nmids=%s err=%s",
                    self.shop_id,
                    complex_adv.adv_id,
                    missing_nmids,
                    exc,
                    exc_info=True,
                )
                return None
            # Keep cache hits and backfill only missing nmids from live WB response.
            for nmid in missing_nmids:
                fresh_bid = fresh_min_bids.search.get(nmid)
                if fresh_bid is not None:
                    min_bids.search[nmid] = fresh_bid
        new_bids: list[NewBid] = []
        for nmid in complex_adv.nmids:
            raw_min = min_bids.search.get(nmid)
            if raw_min is None:
                logger.warning(
                    "stats_stale_emergency: min search bid unknown, using default "
                    "shop_id=%s adv_id=%s nmid=%s default_rub=%s",
                    self.shop_id,
                    complex_adv.adv_id,
                    nmid,
                    settings.MIN_BID_SEARCH_DEFAULT,
                )
                min_bid = int(settings.MIN_BID_SEARCH_DEFAULT)
            else:
                min_bid = int(raw_min)
            new_bids.append(
                NewBid(
                    new_bid=min_bid,
                    search_adv_id=search_adv_id,
                    nmid=nmid,
                    cluster=keyword_text,
                    bidder_keyword_status=BidderKeywordStatus.GOOD,
                    step=0,
                    direct=DirectEnum.DOWN,
                )
            )
        if not new_bids:
            logger.error(
                "stats_stale_emergency: no nmids to set search bid "
                "shop_id=%s adv_id=%s",
                self.shop_id,
                complex_adv.adv_id,
            )
            return None
        command = UpdateBidsCommand(new_bids=new_bids)
        await wb_manager_hub.wb_modifier.set_cluster_bids_for_adv(command)
        return None

    @while_coroutine_decorator(5 * 60, 60)
    async def update_plan_fact_stats(self, only_bot_active: bool = False) -> None:
        """Р¦РёРєР»РёС‡РµСЃРєР°СЏ РєРѕСЂСѓС‚РёРЅР° РґР»СЏ Р·Р°РїРёСЃРё РґР°РЅРЅС‹С… РїР»Р°РЅ-С„Р°РєС‚Р° РІ ClickHouse РєР°Р¶РґС‹Рµ 5 РјРёРЅСѓС‚."""
        # TODO: РџРµСЂРµРЅРµСЃС‚Рё Р·Р°РїРёСЃСЊ РґР°РЅРЅС‹С… РІ CH РІ РµРґРёРЅС‹Р№ РїР°Р№РїР»Р°Р№РЅ РїРѕРґ updater.py РґР»СЏ РµРґРёРЅРЅРѕР±СЂР°Р·РёСЏ
        from .services.plan_fact_controller.plan_fact_manager import PlanFactManager

        pre_advs: list[PreComplexAdv] = (
            await self._wb_shop_data_manager.get_pre_complex_advs(
                only_bot_active=only_bot_active
            )
        )
        if not pre_advs:
            return None

        manager = PlanFactManager()
        await manager.process_and_save_pre_complex_advs(pre_advs)
        adv_ids = _collect_plan_fact_refresh_adv_ids(pre_advs)
        await self._plan_fact_reader.refresh_cache_from_clickhouse(adv_ids)
        return None
    def _log_auto_budget_result(
        self,
        adv: AdvSetting,
        result: AutoBudgetEnsureResult | None,
        campaign_type: AdvType,
        adv_id: int | None,
    ) -> None:
        if result:
            message = (
                "[auto-budget] shop_id=%s adv_setting_id=%s adv_id=%s campaign=%s "
                "status=%s spend_today=%.2f planned=%s reason=%s"
            )
            params = (
                self.shop_id,
                adv.id,
                result.adv_id or adv_id,
                result.campaign_type,
                result.status.value,
                result.spend_today,
                result.planned_amount,
                result.reason,
            )
            if result.status in {
                AutoBudgetEnsureStatus.TOPPED_UP,
                AutoBudgetEnsureStatus.TOPUP_UNVERIFIED,
            }:
                logger.info(message, *params)
            elif result.status in {
                AutoBudgetEnsureStatus.LOCK_BUSY,
                AutoBudgetEnsureStatus.LIMIT_DISABLED,
                AutoBudgetEnsureStatus.BALANCE_SUFFICIENT,
                AutoBudgetEnsureStatus.LIMIT_REACHED,
            }:
                logger.debug(message, *params)
            else:
                logger.warning(message, *params)
        else:
            logger.error(
                "[auto-budget] shop_id=%s adv_setting_id=%s adv_id=%s campaign=%s: ensure_budget returned None (unexpected error)",
                self.shop_id,
                adv.id,
                adv_id,
                    campaign_type,
            )



    @while_coroutine_decorator(60 * 60 * 4, 60)
    async def auto_reset_bid_for_auto_adv(self, only_bot_active: bool = False) -> None:
        advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs(
            only_bot_active=only_bot_active,
            load_extras=False
        )
        advs = [adv for adv in advs if adv.bot_active]

        fresh_advs, _stale = await self._split_advs_by_stats_freshness(
            advs, operation_name="auto_reset_bid_for_auto_adv"
        )
        fresh_ids = {int(adv.adv_id) for adv in fresh_advs}
        from .services.auto_updater_v3.card_ab_hold.stale_stats_freeze import (
            filter_ab_hold_stale_mutation_candidates,
        )

        advs = filter_ab_hold_stale_mutation_candidates(advs, fresh_ids)

        wb_manager_hub = self._wb_manager_hub
        service = AutoResetBidService(
            wb_manager_hub=wb_manager_hub,
            tasks_manager=self._tasks_manager,
        )
        await service.ensure_auto_bids_minimum(advs)
        return None


    @while_coroutine_decorator(60 * 15, 15)
    async def update_common_bid_in_search_adv(self, only_bot_active: bool) -> None:
        """РћР±С‹С‡РЅС‹Р№ updater РѕР±С‰РµР№ СЃС‚Р°РІРєРё Search: Forbidden РїСЂРё structural A/B Hold.

        РџРёС€РµС‚ common-bid РІ WB С‚РѕР»СЊРєРѕ РґР»СЏ РєР°РјРїР°РЅРёР№ РІРЅРµ structural freeze
        (Allowed ``OFF``; Forbidden ``PENDING_SETUP`` / ``ACTIVE`` вЂ” OP-008 /
        card-ab-hold-write-path-ownership В§3/В§17). Bidder/cluster Hold path
        РЅРµ Р·Р°С‚СЂР°РіРёРІР°РµС‚СЃСЏ: Р·РґРµСЃСЊ С‚РѕР»СЊРєРѕ ordinary Search common-bid mutator.
        """
        if not settings.AUTO_SETTING_ACTIVE:
            return None

        # TODO: РЈСЃРєРѕСЂРёС‚СЊ СЂР°Р±РѕС‚Сѓ, РєР°Рє РІР°СЂРёР°РЅС‚ - РїРµСЂРµРґРµР»Р°С‚СЊ РЅР° РіРµРЅРµСЂР°С‚РѕСЂС‹
        from .services.update_commot_bid_in_search_advs_manager import (
            CurrentCommonBidsResolver,
            UpdateCommotBidInSearchAdvsManager,
        )
        wb_manager_hub = self._wb_manager_hub
        resolver = CurrentCommonBidsResolver(
            redis_common_bid_value_manager=self._redis_common_bid_value_manager,
            wb_data_manager=wb_manager_hub.wb_data_manager,
            wb_shop_data_manager=self._wb_shop_data_manager,
        )
        manager = UpdateCommotBidInSearchAdvsManager(
            wb_modifier=wb_manager_hub.wb_modifier,
            tasks_manager=self._tasks_manager,
            redis_common_bid_value_manager=self._redis_common_bid_value_manager,
        )
        complex_advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs(
            only_bot_active=only_bot_active,
            load_extras=False
        )
        complex_advs = [adv for adv in complex_advs if adv.bot_active and
                adv.bidder_active and
                adv.updater_common_bid_in_search_adv_active_status and
                adv.search_adv_active_status is True]
        from .services.auto_updater_v3.card_ab_hold.scheduling import (
            filter_structural_act_candidates,
        )

        # Spec card-ab-hold-write-path-ownership OP-008 / В§3 / В§17:
        # ordinary Search common-bid Forbidden in PENDING_SETUP/ACTIVE
        # (Allowed OFF only; bidder/cluster is the Search bid holder under hold).
        complex_advs = filter_structural_act_candidates(complex_advs)
        complex_advs, _stale = await self._split_advs_by_stats_freshness(
            complex_advs, operation_name="update_common_bid_in_search_adv"
        )
        fresh_ids = {int(adv.adv_id) for adv in complex_advs}
        from .services.auto_updater_v3.card_ab_hold.stale_stats_freeze import (
            filter_ab_hold_stale_mutation_candidates,
        )

        complex_advs = filter_ab_hold_stale_mutation_candidates(
            complex_advs, fresh_ids
        )
        search_adv_bids = await resolver.get_merged_bids(complex_advs)
        advs: list[WBAdvDTO] = await self._wb_shop_data_manager.get_wb_advs_dto(
            complex_advs, search_adv_bids_override=search_adv_bids
        )

        if not advs:
            return None
        handlers: list[Callable[..., Any]] = []
        for adv in advs:
            handler = lambda adv_=adv:manager.update_common_bid_in_search_adv(adv_)
            handlers.append(handler)

        results = await run_tasks(
            handlers=handlers,
            max_workers=16,
            tasks_manager=self._tasks_manager,
        )

        for result, adv in zip(results, advs):
            if isinstance(result, Exception):
                logger.error(
                    "Auto adv active control handler failed: %s", result
                )
            else:
                await self._redis_common_bid_timestamp_manager.set(adv.adv_id)


        return None

    @while_coroutine_decorator(60 * 5, 60)
    async def increment_fact_data_stats(self, only_bot_active: bool = False) -> None:
        complex_advs = await self._wb_shop_data_manager.get_complex_advs(
            only_bot_active=only_bot_active,
            load_extras=False
        )
        if not complex_advs:
            return None
        if not complex_advs:
            return None

        handlers: list[Callable[[], Awaitable[None]]] = []
        for adv in complex_advs:
            handler = functools.partial(self._increment_fact_data_manager.update, adv)
            handlers.append(handler)

        max_workers = self._max_workers_for(len(handlers), 16)
        results = await run_tasks(
            handlers=handlers,
            max_workers=max_workers,
            tasks_manager=self._tasks_manager,
            return_exceptions=True,
        )

        for adv, result in zip(complex_advs, results):
            if isinstance(result, BaseException):
                logger.exception(
                    "increment_fact_data_stats failed for adv_id=%s shop_id=%s",
                    adv.auto_adv_id,
                    adv.shop_id,
                    exc_info=result,
                )

        return None

    @while_coroutine_decorator(60 * 5, 60)
    async def auto_shelf_bid_increment_stats(self, only_bot_active: bool = False) -> None:
        complex_advs = await self._wb_shop_data_manager.get_complex_advs(
            only_bot_active=only_bot_active,
            load_extras=False
        )
        if not complex_advs:
            return None

        handlers: list[Callable[[], Awaitable[None]]] = []
        for adv in complex_advs:
            handler = functools.partial(self._auto_shelf_bid_increment_manager.update, adv)
            handlers.append(handler)

        max_workers = self._max_workers_for(len(handlers), 16)
        results = await run_tasks(
            handlers=handlers,
            max_workers=max_workers,
            return_exceptions=True,
            tasks_manager=self._tasks_manager,
        )

        for adv, result in zip(complex_advs, results):
            if isinstance(result, BaseException):
                logger.exception(
                    "auto_shelf_bid_increment_stats failed for adv_id=%s shop_id=%s",
                    adv.auto_adv_id,
                    adv.shop_id,
                    exc_info=result,
                )

        return None

    @while_coroutine_decorator(60 * 5, 60)
    async def auto_shelf_bid_control(self, only_bot_active: bool = False) -> None:
        """Р¦РёРєР» СѓРїСЂР°РІР»РµРЅРёСЏ РѕР±С‰РµР№ СЃС‚Р°РІРєРѕР№ РїРѕР»РѕРє РґР»СЏ single-nmid Auto-Р Рљ."""
        complex_advs = await self._wb_shop_data_manager.get_complex_advs(only_bot_active=only_bot_active, load_extras=False)
        if not complex_advs:
            return None
        control_candidates = [
            adv
            for adv in complex_advs
            if self._auto_shelf_bid_control_manager.is_coroutine_candidate(adv)
        ]
        if not control_candidates:
            return None
        await self._wb_shop_data_manager.attach_leg_cpo(control_candidates)
        await self._wb_shop_data_manager.attach_min_nmids_bids(control_candidates)
        handlers: list[Callable[[], Awaitable[None]]] = []
        for adv in control_candidates:
            handler = functools.partial(self._auto_shelf_bid_control_manager.update, adv)
            handlers.append(handler)
        max_workers = self._max_workers_for(len(handlers), 16)
        results = await run_tasks(
            handlers=handlers,
            max_workers=max_workers,
            return_exceptions=True,
            tasks_manager=self._tasks_manager,
        )
        for adv, result in zip(control_candidates, results, strict=True):
            if isinstance(result, BaseException):
                logger.exception(
                    "auto_shelf_bid_control failed for adv_id=%s shop_id=%s",
                    adv.auto_adv_id,
                    adv.shop_id,
                    exc_info=result,
                )
        return None

    @while_coroutine_decorator(60, 60)
    async def white_list_tail_trimmer(self, only_bot_active: bool = False):
        """Legacy v2 tail trimmer вЂ” no-op: bot_active Р Рљ РѕР±СЂР°Р±Р°С‚С‹РІР°СЋС‚СЃСЏ РІ V3."""
        return None


    @while_coroutine_decorator(5 * 60, 60)
    async def update_individual_keyword_target_places(self, only_bot_active: bool = False) -> None:
        """Legacy V2 KeywordTargetPlaceUpdater вЂ” no-op РїРѕСЃР»Рµ v3-only (bot_active в†’ V3)."""
        return None

    @while_coroutine_decorator(60, 1)
    async def change_adv_strategy(self, only_bot_active: bool = False):
        """РџРµСЂРёРѕРґРёС‡РµСЃРєРё РІС‹СЃС‚Р°РІР»СЏРµС‚ ``AdvSetting.strategy`` (MIN_CPO / MAX_CONV).

        ``load_extras=True`` вЂ” РѕР±РѕРіР°С‰РµРЅРёРµ ``traffic_clicks_dto`` РґР»СЏ СЃСЂР°РІРЅРµРЅРёСЏ РѕСЂРі/РїРѕР».
        Р›РѕРіРёРєР° РїРѕР»РѕРє Рё РєР»РёРєРѕРІ: ``AdvStrategySelector`` (РјРѕРґСѓР»СЊРЅС‹Р№ РґРѕРєСЃС‚СЂРёРЅРі).
        РќРµ РјРµРЅСЏРµС‚ V3-Р»РµСЃС‚РЅРёС†Сѓ РєР»СЋС‡РµР№; РѕСЃРЅРѕРІРЅРѕР№ С†РёРєР» ``adv_settings_auto_update`` РёРґС‘С‚ Р±РµР· extras.
        """
        complex_advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs(
            only_bot_active=only_bot_active,
            load_extras=True
        )
        if not complex_advs:
            return None

        complex_advs = [adv for adv in complex_advs if adv.bot_active]
        complex_advs = [adv for adv in complex_advs if adv.is_part_auto_setting_active]
        complex_advs = [adv for adv in complex_advs if adv.auto_update_strategy]
        handlers: list[Callable[[], Awaitable[tuple[ComplexAdv, StrategySelection | None]]]] = []
        for adv in complex_advs:
            handlers.append(
                lambda complex_adv=adv: self._resolve_strategy_selection(complex_adv)
            )

        max_workers = self._max_workers_for(len(handlers), cap=16)
        results = await run_tasks(
            handlers,
            max_workers=max_workers,
            tasks_manager=self._tasks_manager,
        )

        strategy_updates: list[tuple[int, int, Strategy, Strategy, str]] = []
        for result in results:
            if isinstance(result, BaseException):
                logger.error(
                    "РћС€РёР±РєР° РІС‹С‡РёСЃР»РµРЅРёСЏ target strategy, shop_id=%s: %s",
                    self.shop_id,
                    result,
                )
                continue
            adv, selection = result
            if selection is None:
                continue
            current_strategy = adv.strategy
            if current_strategy == selection.strategy:
                continue
            strategy_updates.append(
                (
                    adv.adv_setting_original_id,
                    adv.adv_id,
                    current_strategy,
                    selection.strategy,
                    selection.reason,
                )
            )

        if not strategy_updates:
            return None

        await self._apply_strategy_updates(strategy_updates)
        return None

    async def _resolve_strategy_selection(
        self,
        complex_adv: ComplexAdv,
    ) -> tuple[ComplexAdv, StrategySelection | None]:
        selection = await self._adv_strategy_selector.select_target_strategy(
            complex_adv,
            plan_fact_reader=self._plan_fact_reader,
        )
        return complex_adv, selection

    async def _apply_strategy_updates(
        self,
        strategy_updates: list[tuple[int, int, Strategy, Strategy, str]],
    ) -> None:
        async with sm() as session:
            for adv_setting_id, adv_id, from_strategy, to_strategy, reason in strategy_updates:
                # Only update if auto_update_strategy is still on; otherwise user may have
                # disabled it and set strategy manually in the bot UI (race with change_adv_strategy).
                stmt = (
                    update(AdvSetting)
                    .where(AdvSetting.id == adv_setting_id)
                    .where(
                        or_(
                            AdvSetting.auto_update_strategy.is_(True),
                            AdvSetting.auto_update_strategy.is_(None),
                        )
                    )
                    .values({"strategy": to_strategy})
                )
                result = await session.execute(stmt)
                if getattr(result, "rowcount", -1) == 0:
                    logger.debug(
                        "РЎС‚СЂР°С‚РµРіРёСЏ Р Рљ РЅРµ РѕР±РЅРѕРІР»РµРЅР° (auto_update_strategy РІС‹РєР»СЋС‡РµРЅ), "
                        "shop_id=%s, adv_setting_id=%s",
                        self.shop_id,
                        adv_setting_id,
                    )
                    continue
                logger.info(
                    "Р�Р·РјРµРЅРµРЅР° СЃС‚СЂР°С‚РµРіРёСЏ Р Рљ, shop_id=%s, adv_id=%s, adv_setting_id=%s, %s -> %s, reason=%s",
                    self.shop_id,
                    adv_id,
                    adv_setting_id,
                    from_strategy,
                    to_strategy,
                    reason,
                )
            await session.commit()


# TODO: РџРµСЂРµРґРµР»Р°С‚СЊ РіСЂР°С„ Р·Р°РІРёСЃРёРјРѕСЃС‚РµР№

# TODO: Р§Р°СЃС‚Р°СЏ РѕС€РёР±РєР° - РѕСЃС‚Р°РЅРѕРІРєР° Р Рљ РІ РїРµСЂРёРѕРґ СЂР°СЃРєСЂСѓС‚РєРё - СЃРґРµР»Р°С‚СЊ СЃС‚Р°С‚СЊСЋ
