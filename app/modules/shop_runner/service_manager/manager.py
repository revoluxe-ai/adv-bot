import functools
import logging
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
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.modules.shop_runner.wb_statistic_manager.redis_common_stat_timestamp_manager import (
    RedisCommonStatTimestampManager,
)
from app.modules.shop_runner.wb_statistic_manager.redis_cluster_stat_timestamp_manager import (
    RedisClusterStatTimestampManager,
)

from app.settings import settings

from .old_modules.setting_auto_updater_v2 import AdvControlSystem
from .services.increment_fact_data_manager.increment_fact_data_manager import (
    IncrementFactDataManager,
)
from .services.plan_fact_controller.plan_fact_reader import PlanFactReader
from .wb_shop_data_manager import WBShopDataManager
from .wb_shop_data_manager import ComplexAdv
from .while_coroutines_decorator import while_coroutine_decorator
from ..bidder.bidder_func import run_bidder_process_for_adv
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.modules.shop_runner.tasks_manager.tasks_manager import (
    TasksManager,
    run_tasks,
)
from ...common_slaves.wildberries.models.white_list_mode import WhiteListMode
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
from .services.stats_freshness_guard import StatsFreshnessState
from .services.stats_freshness_manager import StatsFreshnessManager
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

T = TypeVar("T")


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
        self._wb_shop_data_manager = WBShopDataManager(
            wb_cabinet,
            tasks_manager=tasks_manager,
            wb_api_data_manager=wb_manager_hub.wb_data_manager,
            wb_manager=wb_manager_hub.wb_manager,
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
        self._auto_budget_service = AutoBudgetService(redis_client_wrapper)
        self._tasks_manager = tasks_manager
        self._plan_fact_reader = plan_fact_reader or PlanFactReader()
        self._increment_fact_data_manager = IncrementFactDataManager(
            redis_client_wrapper,
        )
        self._redis_campaign_activity_reason_manager = RedisCampaignActivityReasonManager(
            redis_client_wrapper
        )
        self._adv_strategy_selector = AdvStrategySelector()

    @staticmethod
    def _max_workers_for(handler_count: int, cap: int) -> int:
        return max(1, min(handler_count, cap))

    async def _split_advs_by_stats_freshness(
        self,
        advs: list[ComplexAdv],
        *,
        operation_name: str,
    ) -> tuple[list[ComplexAdv], list[ComplexAdv]]:
        if not advs:
            return [], []
        handlers: list[Callable[[], Awaitable[tuple[ComplexAdv, StatsFreshnessState]]]] = [
            lambda adv_=adv: self._evaluate_adv_freshness(adv_) for adv in advs
        ]
        results = await run_tasks(
            handlers,
            max_workers=self._max_workers_for(len(handlers), cap=16),
            tasks_manager=self._tasks_manager,
            return_exceptions=True,
        )
        fresh: list[ComplexAdv] = []
        stale_over_6h: list[ComplexAdv] = []
        for adv, result in zip(advs, results):
            if isinstance(result, BaseException):
                logger.error(
                    "Stats freshness evaluation failed, skip automation: shop_id=%s adv_id=%s op=%s err=%s",
                    self.shop_id,
                    adv.adv_id,
                    operation_name,
                    result,
                )
                continue
            _, state = result
            if state.is_stale_over_6h:
                stale_over_6h.append(adv)
            elif state.is_fresh:
                fresh.append(adv)
            else:
                logger.debug(
                    "Automation skipped by stale stats: shop_id=%s adv_id=%s op=%s reason=%s",
                    self.shop_id,
                    adv.adv_id,
                    operation_name,
                    state.reason,
                )
        return fresh, stale_over_6h


    @staticmethod
    async def _evaluate_adv_freshness( adv: ComplexAdv
    ) -> tuple[ComplexAdv, StatsFreshnessState]:
        state = await StatsFreshnessManager().evaluate(adv)
        return adv, state

    @while_coroutine_decorator(1, 60)
    async def update_cpm_bid(self) -> None:
        advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs()
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
        logger.debug("Обновляю ставки для магазина %s", self.shop_id)
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
                    "Ошибка обновления РК : %s, adv_id: %s, shop_id: %s",
                    result,
                    adv_setting.adv_id,
                    self.shop_id,
                )


        logger.debug("Все ставки обновлены для магазина %s", self.shop_id)
        return None

    @staticmethod
    async def __run_bidder_process_for_adv(complex_adv:  ComplexAdv, wb_api: WBApi) -> None:
        adv_setting: AdvSetting = complex_adv.adv_setting
        keywords = await complex_adv.get_keywords()
        await run_bidder_process_for_adv(adv_setting, wb_api, keywords)

    @while_coroutine_decorator(60 * 5)
    async def update_common_sale_stat(self) -> None:
        advs = await self._wb_shop_data_manager.get_complex_advs()
        if not advs:
            return None
        from .services.common_sale_stat_updater import (
            CommonSaleStatUpdater,
            CommonSaleStatUpdaterContainer,
        )
        wb_manager_hub = self._wb_manager_hub
        container = CommonSaleStatUpdaterContainer(_wb_manager_hub=wb_manager_hub)
        updater: CommonSaleStatUpdater = container.common_sale_stat_updater()

        updated_nmids = await updater.update_last_week_stats(advs)
        nmid_to_adv_ids: dict[int, set[int]] = {}
        for adv in advs:
            nmid_to_adv_ids.setdefault(adv.main_nmid, set()).update(adv.all_adv_ids)
        for nmid in updated_nmids:
            for adv_id in nmid_to_adv_ids.get(nmid, set()):
                await self._redis_common_stat_timestamp_manager.set(adv_id)
        return None

    @staticmethod
    async def _update_full_stat_in_click_house(stats: Iterable[FullAdvStat]) -> None:
        await full_wb_adv_stat.insert(stats)
        date_time = datetime.now()
        for stat in stats:
            await data_manager.set_last_full_stat_update(stat.advertId, date_time)


    @while_coroutine_decorator(5 * 60, 1)
    async def update_full_adv_stat(self) -> None:
        advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs()
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
        return None

    @staticmethod
    async def _update_cards_data_from_wb_to_pg(
        shop_data_updater: ShopDataUpdater,
    ) -> None:
        await shop_data_updater.update_cards_data()

    @while_coroutine_decorator(1 * 60)
    async def update_advs_data_from_wb_to_pg(self) -> None:
        from app.modules.wb_adv_updater import data_manager
        await data_manager.update_advs_data_from_wb_to_pg(self._wb_api)
        return None


    @while_coroutine_decorator(60 * 15)
    async def update_cards_data_from_wb_to_pg(self) -> None:
        wb_api = self._wb_api
        shop_data_updater = ShopDataUpdater(wb_api)
        await self._update_cards_data_from_wb_to_pg(shop_data_updater)
        logger.debug("Обновление карточек завершено")

    @while_coroutine_decorator(5 * 60)
    async def adv_settings_auto_update(self) -> None:
        if not settings.AUTO_SETTING_ACTIVE:
            return None
        advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs()
        advs = [adv for adv in advs if adv.bot_active]
        advs = [adv for adv in advs if adv.is_part_auto_setting_active]
        # Автоуправление настройками относится по сути только к Аукциону (Поиск), поэтому оставляем
        # в фильтре только проверку активности аукциона
        advs = [adv for adv in advs if adv.search_adv_active_status]
        advs = [adv for adv in advs if adv.bot_active]
        advs, _ = await self._split_advs_by_stats_freshness(
            advs, operation_name="adv_settings_auto_update"
        )
        control_system_v2 = AdvControlSystem(max_last_period=2)
        # TODO: Внедрить в бот плату за оборот
        handlers: list[Callable[[], Awaitable[Any]]] = []
        for adv in advs:
            handlers.append(
                lambda complex_adv=adv: control_system_v2.process_adv(complex_adv)
            )

        if not handlers:
            return None

        max_workers = self._max_workers_for(len(handlers), cap=16)
        _ = await run_tasks(
            handlers,
            max_workers=max_workers,
            return_exceptions=False,
        )
        return None

    @while_coroutine_decorator(60, 1)
    async def update_top_key_in_advs(self) -> None:
        from .old_modules.setting_auto_updater.modules.first_key_updater import (
            FirstKeyUpdaterError,
            FirstKeyUpdater,
        )

        advs: list[ComplexAdv] = (
            await self._wb_shop_data_manager.get_complex_advs()
        )
        advs = [adv for adv in advs if adv.bot_active]
        advs_with_whitelist = [
            adv for adv in advs if adv.auto_update_white_list
        ]

        handlers: list[Callable[[], Awaitable[Any]]] = []
        for adv in advs_with_whitelist:
            adv_setting = adv.adv_setting
            updater = FirstKeyUpdater(adv_setting)
            handlers.append(
                lambda complex_adv=adv, upd=updater: upd.top_key_auto_update(
                    complex_adv
                )
            )

        results = await run_tasks(
            handlers,
            max_workers=self._max_workers_for(len(handlers), cap=16),
        )

        for adv, result in zip(advs_with_whitelist, results):
            if isinstance(result, FirstKeyUpdaterError):
                logger.error(
                    "Ошибка обновления верхнего ключа для adv_id %s: %s",
                    adv.adv_id,
                    result,
                    exc_info=True,
                )
                raise result
            if isinstance(result, Exception):
                logger.error(
                    "Ошибка обновления верхнего ключа для adv_id %s: %s",
                    adv.adv_id,
                    result,
                    exc_info=True,
                )
                raise result

        return None

    @while_coroutine_decorator(15, 60)
    async def delete_keywords_from_wl_by_mean_auto_ctr(self) -> None:
        # TODO: Добавить функцию-фильтр для ComplexAdvs getter
        complex_advs: Sequence[ComplexAdv] = (
            await self._wb_shop_data_manager.get_complex_advs()
        )
        complex_advs_with_white_list_by_mean_auto_ctr_active = [
            adv
            for adv in complex_advs
            if adv.rec_system_promotion_mode_active
            and adv.auto_update_setting_version == 2
            and adv.is_white_list_control_enabled
            and adv.bot_active
        ]
        complex_advs_with_white_list_by_mean_auto_ctr_active, _ = (
            await self._split_advs_by_stats_freshness(
                complex_advs_with_white_list_by_mean_auto_ctr_active,
                operation_name="delete_keywords_from_wl_by_mean_auto_ctr",
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
                    "Ошибка удаления ключей из БС по сред.авто стр, shop_id: %s, adv_id: %s)",
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

        advs = await self._wb_shop_data_manager.get_complex_advs()
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
                    "Ошибка обновления позиций из Api: %s", result, exc_info=True
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

        advs = await self._wb_shop_data_manager.get_complex_advs()
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
                    "Ошибка обновления позиций из Api: %s", result, exc_info=True
                )

        return None

    @while_coroutine_decorator(60 * 15, 60)
    async def update_minus_phrases_in_advs(self):
        from .services.minus_phrase_manager import MinusPhraseManagerContainer

        wb_manager_hub = self._wb_manager_hub
        container = MinusPhraseManagerContainer(_wb_api_manager_hub=wb_manager_hub)
        minus_phrase_manager = container.minus_phrase_manager()

        complex_advs = await self._wb_shop_data_manager.get_complex_advs()
        complex_advs = [adv for adv in complex_advs if adv.bot_active]
        complex_advs, _ = await self._split_advs_by_stats_freshness(
            complex_advs, operation_name="update_minus_phrases_in_advs"
        )
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
        )

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Ошибка обновления минус фраз для shop_id: %s, adv_id: %s, ошибка: %s",
                    complex_advs[i].shop_id,
                    complex_advs[i].adv_id,
                    result,
                    exc_info=True,
                )
        return None

    @while_coroutine_decorator(60, 60)
    async def auto_budget_watchdog(self) -> None:
        advs = await self._wb_shop_data_manager.get_complex_advs()
        if not advs:
            return None
        candidates: list[ComplexAdv] = [
            adv
            for adv in advs
            if adv.auto_budget_watchdog_enabled
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
                    lambda adv_setting_id_=adv_setting_id,
                           wb_manager_hub_=wb_manager_hub: (
                        self._auto_budget_service.ensure_common_budget(
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
                        lambda adv_setting_id_=adv_setting_id,
                               campaign_type_=campaign_type,
                               wb_manager_hub_=wb_manager_hub: (
                            self._auto_budget_service.ensure_budget(
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

    @while_coroutine_decorator(5 * 60, 60)
    async def update_clusters_adv_stats_today(self) -> None:
        """Обновление статистики кластеров за сегодня."""
        wb_manager_hub = self._wb_manager_hub
        container = ClustersAdvStatUpdaterContainer(_wb_manager_hub=wb_manager_hub)
        updater: ClustersAdvStatUpdater = container.clusters_adv_stat_updater()
        complex_advs = await self._wb_shop_data_manager.get_complex_advs()
        updated_original_adv_ids = await updater.update_today_stats(complex_advs)
        for adv_orig_id in updated_original_adv_ids:
            await self._redis_cluster_stat_timestamp_manager.set(adv_orig_id)
        return None

    @while_coroutine_decorator(24 * 60 * 60, 60)
    async def update_clusters_adv_stats_history(self) -> None:
        """Обновление статистики кластеров за прошлые дни."""
        wb_manager_hub = self._wb_manager_hub
        container = ClustersAdvStatUpdaterContainer(_wb_manager_hub=wb_manager_hub)
        updater: ClustersAdvStatUpdater = container.clusters_adv_stat_updater()
        complex_advs = await self._wb_shop_data_manager.get_complex_advs()
        await updater.update_past_days_stats(complex_advs, for_last_days=365)

    @while_coroutine_decorator(60 * 5, 60)
    async def update_cluster_bids(self) -> None:
        if not settings.AUTO_SETTING_ACTIVE:
            return None
        from .services.update_cluster_bids_manager.di import ClusterBidsManagerContainer
        wb_manager_hub = self._wb_manager_hub
        container = ClusterBidsManagerContainer(
            shop_id=self.shop_id,
            redis_client=wb_manager_hub.redis_client_wrapper,
        )
        update_clusters_bid_manager = container.update_cluster_bids_manager()
        advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs()
        advs = [adv for adv in advs if adv.bot_active]
        advs = [
            adv
            for adv in advs
            if adv.bidder_active
        ]
        advs_filtred, _ = await self._split_advs_by_stats_freshness(
            advs, operation_name="update_cluster_bids"
        )
        if not advs_filtred:
            return None
        await update_clusters_bid_manager.update_cluster_bids(advs_filtred)
        return None

    @while_coroutine_decorator(60 * 5, 60)
    async def handle_stats_stale_emergency(self) -> None:
        """Emergency mode: stale stats over 6 hours => keep one top key and min bid."""
        complex_advs = await self._wb_shop_data_manager.get_complex_advs()
        complex_advs = [adv for adv in complex_advs if adv.bot_active]
        complex_advs = [adv for adv in complex_advs if adv.is_part_auto_setting_active]
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
        if not candidates:
            return None
        top_keyword = max(candidates, key=lambda kw: kw.rating or 0)
        top_keyword_id = top_keyword.keyword_setting_original_id
        candidate_ids = [kw.keyword_setting_original_id for kw in candidates]
        demote_ids = [kw_id for kw_id in candidate_ids if kw_id != top_keyword_id]

        async with sm(read_only=False) as session:
            if demote_ids:
                stmt_demote = (
                    update(KeywordSetting)
                    .where(KeywordSetting.id.in_(demote_ids))
                    .values(hard_status=1)
                )
                _ = await session.execute(stmt_demote)
            stmt_promote = (
                update(KeywordSetting)
                .where(KeywordSetting.id == top_keyword_id)
                .values(hard_status=2)
            )
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
        min_bids = await wb_manager_hub.wb_manager.get_min_bids(
            [complex_adv], cache_possible=True
        )
        new_bids: list[NewBid] = []
        for nmid in complex_adv.nmids:
            min_bid = min_bids.search.get(nmid)
            if min_bid is None:
                continue
            new_bids.append(
                NewBid(
                    new_bid=int(min_bid),
                    adv_id=search_adv_id,
                    nmid=nmid,
                    cluster=keyword_text,
                    bidder_keyword_status=BidderKeywordStatus.GOOD,
                    step=0,
                    direct=DirectEnum.DOWN,
                )
            )
        if not new_bids:
            return None
        command = UpdateBidsCommand(new_bids=new_bids)
        await wb_manager_hub.wb_modifier.set_cluster_bids_for_adv(command)
        return None

    @while_coroutine_decorator(5 * 60, 60)
    async def update_plan_fact_stats(self) -> None:
        """Циклическая корутина для записи данных план-факта в ClickHouse каждые 5 минут"""
        from .services.plan_fact_controller.plan_fact_manager import PlanFactManager

        advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs()
        if not advs:
            return None

        manager = PlanFactManager()
        await manager.process_and_save(advs)
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

    @while_coroutine_decorator(1 * 60, 60)
    async def auto_adv_active_control(self) -> None:
        advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs()
        advs = [adv for adv in advs if adv.bot_active]
        wb_manager_hub = self._wb_manager_hub
        service = AutoAdvActiveControlService(
            wb_modifier=wb_manager_hub.wb_modifier,
            tasks_manager=self._tasks_manager,
            plan_fact_reader=self._plan_fact_reader,
            redis_campaign_activity_reason_manager=self._redis_campaign_activity_reason_manager,
        )
        await service.ensure_campaigns_active(advs)
        return None

    @while_coroutine_decorator(60 * 60 * 4, 60)
    async def auto_reset_bid_for_auto_adv(self) -> None:
        advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs()
        advs = [adv for adv in advs if adv.bot_active]

        wb_manager_hub = self._wb_manager_hub
        service = AutoResetBidService(
            wb_manager_hub=wb_manager_hub,
            tasks_manager=self._tasks_manager,
        )
        await service.ensure_auto_bids_minimum(advs)
        return None


    @while_coroutine_decorator(60 * 15, 15)
    async def update_common_bid_in_search_adv(self) -> None:
        if not settings.AUTO_SETTING_ACTIVE:
            return None

        # TODO: Ускорить работу, как вариант - переделать на генераторы
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
        complex_advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs()
        complex_advs = [adv for adv in complex_advs if adv.bot_active and
                adv.bidder_active and
                adv.updater_common_bid_in_search_adv_active_status and
                adv.search_adv_active_status is True]
        complex_advs, _ = await self._split_advs_by_stats_freshness(
            complex_advs, operation_name="update_common_bid_in_search_adv"
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
    async def increment_fact_data_stats(self) -> None:
        complex_advs = await self._wb_shop_data_manager.get_complex_advs()
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

    @while_coroutine_decorator(60, 60)
    async def white_list_tail_trimmer(self):
        from .services.white_list_trimmer import WhiteListTrimmer
        complex_advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs()
        complex_advs = [adv for adv in complex_advs if adv.bot_active]
        complex_advs = [adv for adv in complex_advs if adv.auto_update_white_list]
        complex_advs = [
            adv
            for adv in complex_advs
            if adv.white_list_mode
            in (WhiteListMode.TAIL_TRIMMING, WhiteListMode.REPLACE_ON_TRIM)
        ]
        complex_advs, _ = await self._split_advs_by_stats_freshness(
            complex_advs, operation_name="white_list_tail_trimmer"
        )
        if not complex_advs:
            return None
        trimmer = WhiteListTrimmer()
        handlers: list[Callable[[], Awaitable[None]]] = []
        for adv in complex_advs:
            handler = functools.partial(trimmer.trim, adv)
            handlers.append(handler)

        results = await run_tasks(handlers=handlers, max_workers=16, tasks_manager=self._tasks_manager)

        for adv, result in zip(complex_advs, results):
            if isinstance(result, BaseException):
                logger.exception("Ошибка срезания БС adv_id: %s:  %s", adv.adv_id,
                                 result)

        return None


    @while_coroutine_decorator(5 * 60, 60)
    async def update_individual_keyword_target_places(self):
        from .services.keywords_target_place_updater import KeywordTargetPlaceUpdater
        from app.modules.predict_keywords_target_place import (build_predict_keywords_target_place,
                                                               PredictKeywordsTargetPlace)
        complex_advs = await self._wb_shop_data_manager.get_complex_advs()
        if not complex_advs:
            return None
        complex_advs = [adv for adv in complex_advs if adv.bot_active]
        complex_advs: list[ComplexAdv] = [adv for adv in complex_advs if adv.individual_keywords_target_place_mode]
        complex_advs, _ = await self._split_advs_by_stats_freshness(
            complex_advs, operation_name="update_individual_keyword_target_places"
        )
        wb_adv_dto: list[WBAdvDTO] = await self._wb_shop_data_manager.get_wb_advs_dto(complex_advs)

        predict_keyword_target_place: PredictKeywordsTargetPlace = build_predict_keywords_target_place()

        updater = KeywordTargetPlaceUpdater(predict_keyword_target_place)
        handlers: list[Callable[[], Awaitable[None]]] = []
        for adv in wb_adv_dto:
            handler = functools.partial(updater.update_individual_keyword_target_places, adv)
            handlers.append(handler)

        results = await run_tasks(
            handlers=handlers,
            max_workers=16,
        )
        for result, adv in zip(results,  wb_adv_dto):
            if isinstance(result, BaseException):
                logger.exception('Ошибка обновления keywords target places for adv_id:  %s',
                                 adv.adv_id,)

        return None

    @while_coroutine_decorator(60, 1)
    async def change_adv_strategy(self):
        complex_advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs()
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
                    "Ошибка вычисления target strategy, shop_id=%s: %s",
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
                        "Стратегия РК не обновлена (auto_update_strategy выключен), "
                        "shop_id=%s, adv_setting_id=%s",
                        self.shop_id,
                        adv_setting_id,
                    )
                    continue
                logger.info(
                    "Изменена стратегия РК, shop_id=%s, adv_id=%s, adv_setting_id=%s, %s -> %s, reason=%s",
                    self.shop_id,
                    adv_id,
                    adv_setting_id,
                    from_strategy,
                    to_strategy,
                    reason,
                )
            await session.commit()


# TODO: Переделать граф зависимостей

# TODO: Частая ошибка - остановка РК в период раскрутки - сделать статью
