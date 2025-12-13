import asyncio
import copy
import logging
from collections import defaultdict
from collections.abc import  Awaitable, Coroutine, Iterable, Sequence
from datetime import datetime
from typing import (
    Any,
    TypeVar,
)



from app.core.wb_api.ping_manager import PingManager

from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
)
from app.modules.common_slaves.wildberries.models.models import BidderCoroutineType
from app.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater
from app.modules.full_stat_adv_updater import wb_data_getter
from app.modules.full_stat_adv_updater.types.full_adv_stat import FullAdvStat
from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.modules.shop_runner.wb_statistic_manager.backend.common_stat_manager import (
    WBCommonStatManager,
)

from app.settings import settings


from .old_modules.setting_auto_updater_v2 import AdvControlSystem
from .wb_shop_data_manager import WBShopDataManager
from .wb_shop_data_manager import ComplexAdv
from .while_coroutines_decorator import while_coroutine_decorator
from ..bidder.bidder_func import run_bidder_process_for_adv
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CoroutinesManager:
    def __init__(self, wb_api: WBApi):
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

    @while_coroutine_decorator(1, 60)
    async def update_cpm_bid(self) -> None:
        advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs()
        if not advs:
            return None
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
        results = await asyncio.gather(
            *[
                self.__run_bidder_process_for_adv(adv, self._wb_api)
                for adv in advs
            ],
            return_exceptions=True,
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

        logger.debug(f"Все ставки обновлены для магазина {self.shop_id}")
        return None

    @staticmethod
    async def __run_bidder_process_for_adv(complex_adv:  ComplexAdv, wb_api: WBApi) -> None:
        adv_setting: AdvSetting = complex_adv.adv_setting
        keywords = await complex_adv.get_keywords()
        await run_bidder_process_for_adv(adv_setting, wb_api, keywords)

    @while_coroutine_decorator(5 * 60)
    async def update_common_sale_stat(self) -> None:
        wb_api = self._wb_api
        ping_manager = PingManager(wb_api.access, self._session)
        await ping_manager.ping_analytics_rights_and_connect()
        wb_stat_manager = WBCommonStatManager(wb_api)
        advs = await self._wb_shop_data_manager.get_complex_advs()
        active_nmids = [adv.nmids[0] for adv in advs]
        await wb_stat_manager.update_common_statistic(active_nmids)

    @staticmethod
    async def _update_full_stat_in_click_house(stats: Iterable[FullAdvStat]) -> None:
        await full_wb_adv_stat.insert(stats)

    @while_coroutine_decorator(5 * 60, 1)
    async def update_full_adv_stat(self) -> None:
        from app.modules.wb_adv_updater import data_manager
        wb_api = self._wb_api
        advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs()
        all_adv_ids: set[int] = set()
        for adv in advs:
            all_adv_ids.add(adv.auto_adv_id)
            if search_adv_id := adv.search_adv.adv_id:
                all_adv_ids.add(search_adv_id)
        full_stats: list[FullAdvStat] = (
            await wb_data_getter.get_full_adv_stat_for_adv_ids(
                wb_api, all_adv_ids, threshold_dates=settings.FULL_STAT_THRESHOLD_DATES
            )
        )
        if full_stats:
            await self._update_full_stat_in_click_house(full_stats)
            date_time = datetime.now()
            for stat in full_stats:
                await data_manager.set_last_full_stat_update(stat.advertId, date_time)
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
        from .old_modules.setting_auto_updater import (
            AdvSettingAutoUpdater,
        )
        advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs()
        advs = [adv for adv in advs if adv.is_part_auto_setting_active]
        advs = [adv for adv in advs if adv.search_adv_active_status or adv.auto_adv_active_status]
        update_tasks: list[asyncio.Task[None] | Awaitable[None]] = []
        last_days_for_analyze = 2
        control_system_v2 = AdvControlSystem(max_last_period=2)
        # TODO: Внедрить в бот плату за оборот
        for adv in advs:
            if adv.auto_update_setting_version == 1:
                adv_setting = adv.adv_setting
                adv_updater = AdvSettingAutoUpdater(adv_setting, last_days_for_analyze)
                keywords_coro = adv.get_keywords()
                adv_update = adv_updater.update(keywords_coro)
                adv_update_task = asyncio.create_task(adv_update)
                update_tasks.append(adv_update_task)
            elif adv.auto_update_setting_version == 2:
                adv_update_task = control_system_v2.process_adv(adv)
                update_tasks.append(adv_update_task)
            else:
                logger.error(
                    "[adv_id=%s] Неизвестная версия автообновления настроек: %s",
                    adv.adv_setting.adv_id,
                    adv.auto_update_setting_version,
                )

        await asyncio.gather(*update_tasks)
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
        ]

        tasks: list[Awaitable[None]] = []
        for adv in complex_advs_with_white_list_by_mean_auto_ctr_active:
            task = delete_keywords_from_wl_by_mean_auto_ctr(complex_adv=adv)
            tasks.append(task)

        results: Sequence[None | BaseException] = await asyncio.gather(
            *tasks, return_exceptions=True
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
        update_tasks: list[Awaitable[None]] = []
        for adv in advs:
            task = keyword_stamp_manager.update_keywords_position_stamp(adv)
            update_tasks.append(task)

        results: list[BaseException | None] = await asyncio.gather(
            *update_tasks, return_exceptions=True
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
        update_tasks: list[Awaitable[None]] = []
        for adv in advs:
            task = keyword_stamp_manager.update_keyword_history(adv)
            update_tasks.append(task)

        results: list[BaseException | None] = await asyncio.gather(
            *update_tasks, return_exceptions=True
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

        update_tasks: list[Awaitable[None]] = []
        for adv in complex_advs:
            task = minus_phrase_manager.update_minus_phrases(adv)
            update_tasks.append(task)

        results: list[BaseException | None] = await asyncio.gather(*update_tasks, return_exceptions=True)

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
        advs = [
            adv
            for adv in advs
            if adv.bidder_active
               and adv.bidder_coroutine_type == BidderCoroutineType.UPDATE_CLUSTER_BIDS
        ]
        if not advs:
            return None
        advs_for_this_coroutine = copy.deepcopy(advs)
        # TODO: ТУт костыль, чтобы корутина применялась только к белому списку
        for adv in advs_for_this_coroutine:
            adv.white_list_mode = True
        await update_clusters_bid_manager.update_cluster_bids(advs_for_this_coroutine)
        return None



# TODO: Переделать граф зависимостей

# TODO: Частая ошибка - остановка РК в период раскрутки - сделать статью
