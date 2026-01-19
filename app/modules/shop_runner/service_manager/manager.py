import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable, Coroutine, Iterable, Sequence
from datetime import datetime
from typing import (
    Any,
    TypeVar,
)



from app.core.redis_manager_v2.redis_client import RedisClient

from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
)
from app.modules.common_slaves.wildberries.models.models import BidderCoroutineType
from app.modules.auto_budget_manager import (
    AutoBudgetEnsureResult,
    AutoBudgetEnsureStatus,
    AutoBudgetService,
)
from app.shared.domains.wb.enums import (
    AdvType,
)
from app.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater
from app.modules.full_stat_adv_updater import wb_data_getter
from app.modules.full_stat_adv_updater.types.full_adv_stat import FullAdvStat
from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.modules.shop_runner.wb_statistic_manager.redis_common_stat_timestamp_manager import (
    RedisCommonStatTimestampManager,
)

from app.settings import settings


from .old_modules.setting_auto_updater_v2 import AdvControlSystem
from .wb_shop_data_manager import WBShopDataManager
from .wb_shop_data_manager import ComplexAdv
from .while_coroutines_decorator import while_coroutine_decorator
from ..bidder.bidder_func import run_bidder_process_for_adv
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.modules.shop_runner.tasks_manager.tasks_manager import (
    TasksManager,
    run_tasks,
)
from ...wb_adv_updater import data_manager

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CoroutinesManager:
    def __init__(
        self,
        wb_api: WBApi,
        redis_client_wrapper: RedisClient,
        db_tasks_manager: TasksManager,
        http_tasks_manager: TasksManager,
    ):
        wb_cabinet = wb_api.wb_cabinet
        assert wb_cabinet
        self._wb_shop_data_manager = WBShopDataManager(wb_cabinet)

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
        self._auto_budget_service = AutoBudgetService(redis_client_wrapper)
        self._db_tasks_manager = db_tasks_manager
        self._http_tasks_manager = http_tasks_manager

    @staticmethod
    def _max_workers_for(handler_count: int, cap: int) -> int:
        return max(1, min(handler_count, cap))

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
            tasks_manager=self._db_tasks_manager,
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

    @while_coroutine_decorator(60 * 15)
    async def update_common_sale_stat(self) -> None:
        advs = await self._wb_shop_data_manager.get_complex_advs()
        if not advs:
            return None
        from .services.common_sale_stat_updater import (
            CommonSaleStatUpdater,
            CommonSaleStatUpdaterContainer,
        )
        from app.core.di.wb_manager_hub import WBManagerHubFactory

        wb_manager_hub = WBManagerHubFactory.get_wb_manager_from_context()
        container = CommonSaleStatUpdaterContainer(_wb_manager_hub=wb_manager_hub)
        updater: CommonSaleStatUpdater = container.common_sale_stat_updater()

        await updater.update_last_week_stats(advs)
        for adv in advs:
            for adv_id in adv.all_adv_ids:
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
        wb_api = self._wb_api
        advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs()
        all_adv_ids: set[int] = set()
        for adv in advs:
            all_adv_ids.update(adv.all_adv_ids)
        full_stats: list[FullAdvStat] = (
            await wb_data_getter.get_full_adv_stat_for_adv_ids(
                wb_api, all_adv_ids, threshold_dates=settings.FULL_STAT_THRESHOLD_DATES
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


    @while_coroutine_decorator(60 * 15)
    async def update_cards_data_from_wb_to_pg(self) -> None:
        wb_api = self._wb_api
        shop_data_updater = ShopDataUpdater(wb_api)
        await self._update_cards_data_from_wb_to_pg(shop_data_updater)
        logger.debug("Обновление карточек завершено")

    @while_coroutine_decorator(5 * 60)
    async def adv_settings_auto_update(self):
        advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs()
        advs = [adv for adv in advs if adv.is_part_auto_setting_active]
        advs = [adv for adv in advs if adv.search_adv_active_status or adv.auto_adv_active_status]
        advs = [adv for adv in advs if adv.bot_active]
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
            tasks_manager=self._db_tasks_manager,
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
        tasks: list[asyncio.Task[None]] = []
        for adv in advs:
            if not adv.auto_update_white_list:
                continue
            adv_setting = adv.adv_setting
            updater = FirstKeyUpdater(adv_setting)
            update_coroutine: Coroutine[Any, Any, None] = updater.top_key_auto_update(
                adv
            )
            task = asyncio.create_task(update_coroutine)
            tasks.append(task)

        for task in tasks:
            try:
                await task
            except FirstKeyUpdaterError as exc:
                logger.error("Ошибка обновления верхнего ключа: %s", exc, exc_info=True)
                raise exc

    @while_coroutine_decorator(15, 60)
    async def delete_keywords_from_wl_by_mean_auto_ctr(self) -> None:
        # TODO: Добавить функцию-фильтр для ComplexAdvs getter
        from .services import delete_keywords_from_wl_by_mean_auto_ctr

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
            tasks_manager=self._db_tasks_manager,
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
        from app.core.di.wb_manager_hub import WBManagerHubFactory
        from .services.keyword_stamp_manager import (
            KeywordStampManagerContainer,
            KeywordStampManager,
        )

        wb_manager_hub = WBManagerHubFactory.get_wb_manager_from_context()
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
            tasks_manager=self._db_tasks_manager,
        )

        for result in results:
            if isinstance(result, BaseException):
                logger.error(
                    "Ошибка обновления позиций из Api: %s", result, exc_info=True
                )

        return None

    @while_coroutine_decorator(24 * 60 * 60 * 60, 60)
    async def update_keywords_positions_history(self) -> None:
        from app.core.di.wb_manager_hub import WBManagerHubFactory
        from .services.keyword_stamp_manager import (
            KeywordStampManagerContainer,
            KeywordStampManager,
        )

        wb_manager_hub = WBManagerHubFactory.get_wb_manager_from_context()
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
            tasks_manager=self._db_tasks_manager,
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
        from app.core.di.wb_manager_hub import WBManagerHubFactory

        wb_manager_hub = WBManagerHubFactory.get_wb_manager_from_context()
        container = MinusPhraseManagerContainer(_wb_api_manager_hub=wb_manager_hub)
        minus_phrase_manager = container.minus_phrase_manager()

        complex_advs = await self._wb_shop_data_manager.get_complex_advs()
        complex_advs = [adv for adv in complex_advs if adv.bot_active]
        handlers: list[Callable[[], Awaitable[Any]]] = [
            lambda complex_adv=adv: minus_phrase_manager.update_minus_phrases(
                complex_adv
            )
            for adv in complex_advs
        ]

        if not handlers:
            return None

        results: list[BaseException | None] = await run_tasks(
            handlers,
            max_workers=self._max_workers_for(len(handlers), cap=16),
            tasks_manager=self._db_tasks_manager,
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

    @while_coroutine_decorator(settings.UPDATE_FULL_ADV_STAT_PERIOD, 60)
    async def auto_budget_watchdog(self) -> None:
        advs = await self._wb_shop_data_manager.get_complex_advs()
        if not advs:
            return None
        candidates: list[ComplexAdv] = [
            adv
            for adv in advs
            if (
                ((adv.auto_budget_daily_limit or 0) > 0 and adv.adv_id)
                or ((adv.search_auto_budget_daily_limit or 0) > 0 and adv.search_adv_id)
            )
        ]
        candidates = [adv for adv in candidates if adv.auto_budget_watchdog_enabled]
        if not candidates:
            return None
        from app.core.di.wb_manager_hub import WBManagerHubFactory

        wb_manager_hub = WBManagerHubFactory.get_wb_manager_from_context()
        handlers: list[Callable[[], Awaitable[AutoBudgetEnsureResult | None]]] = []
        task_specs: list[tuple[AdvSetting, AdvType, int]] = []

        for adv in candidates:
            campaign_checks: list[tuple[AdvType, int]] = []
            if (adv.auto_budget_daily_limit or 0) > 0 and adv.adv_id:
                campaign_checks.append((AdvType.AUTO, adv.adv_id))
            if (adv.search_auto_budget_daily_limit or 0) > 0 and adv.search_adv_id:
                campaign_checks.append(
                    (AdvType.SEARCH, adv.search_adv_id)
                )
            adv_setting = adv.adv_setting
            adv_setting_id = adv_setting.id
            for campaign_type, adv_id in campaign_checks:
                handlers.append(
                    lambda adv_setting_id_=adv_setting_id,
                           campaign_type_=campaign_type,
                           wb_manager_hub_=wb_manager_hub:
                    (
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
            tasks_manager=self._db_tasks_manager,
        )

        for (adv_setting, campaign_type, adv_id), result in zip(task_specs, results):
            if isinstance(result, Exception):
                logger.error(
                    "Auto budget ensure failed for shop_id=%s, adv_id=%s, campaign=%s: %s",
                    self.shop_id,
                    adv_id,
                    campaign_type,
                    result,
                    exc_info=True,
                )
                continue
            self._log_auto_budget_result(
                adv_setting, result, campaign_type, adv_id
            )
        return None

    @while_coroutine_decorator(5 * 60, 60)
    async def update_clusters_adv_stats_today(self) -> None:
        """Обновление статистики кластеров за сегодня."""
        from .services import ClustersAdvStatUpdater, ClustersAdvStatUpdaterContainer
        from app.core.di.wb_manager_hub import WBManagerHubFactory

        wb_manager_hub = WBManagerHubFactory.get_wb_manager_from_context()
        container = ClustersAdvStatUpdaterContainer(_wb_manager_hub=wb_manager_hub)
        updater: ClustersAdvStatUpdater = container.clusters_adv_stat_updater()
        complex_advs = await self._wb_shop_data_manager.get_complex_advs()

        await updater.update_today_stats(complex_advs)
        return None

    @while_coroutine_decorator(24 * 60 * 60, 60)
    async def update_clusters_adv_stats_history(self) -> None:
        """Обновление статистики кластеров за прошлые дни."""
        from .services import ClustersAdvStatUpdater, ClustersAdvStatUpdaterContainer
        from app.core.di.wb_manager_hub import WBManagerHubFactory

        wb_manager_hub = WBManagerHubFactory.get_wb_manager_from_context()
        container = ClustersAdvStatUpdaterContainer(_wb_manager_hub=wb_manager_hub)
        updater: ClustersAdvStatUpdater = container.clusters_adv_stat_updater()
        complex_advs = await self._wb_shop_data_manager.get_complex_advs()

        await updater.update_past_days_stats(complex_advs, for_last_days=365)

    @while_coroutine_decorator(60 * 15, 60)
    async def update_cluster_bids(self) -> None:
        from .services.update_cluster_bids_manager.di import ClusterBidsManagerContainer
        from app.core.di.wb_manager_hub import WBManagerHubFactory
        wb_manager_hub = WBManagerHubFactory.get_wb_manager_from_context()
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
               and adv.bidder_coroutine_type == BidderCoroutineType.UPDATE_CLUSTER_BIDS
        ]
        advs = [adv for adv in advs if adv.search_adv_active_status]
        if not advs:
            return None
        await update_clusters_bid_manager.update_cluster_bids(advs)
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




# TODO: Переделать граф зависимостей

# TODO: Частая ошибка - остановка РК в период раскрутки - сделать статью
