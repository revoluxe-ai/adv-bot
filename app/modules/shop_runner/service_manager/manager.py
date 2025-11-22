import asyncio
import logging
from collections import defaultdict
from collections.abc import AsyncGenerator, Awaitable, Coroutine, Iterable, Sequence
from datetime import datetime
from typing import (
    Any,
    TypeVar,
)

from app.core.mp.wb.api.wb_manager_hub_factory import WBManagerHubFactory
from app.core.wb_api.ping_manager import PingManager
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
)
from app.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater
from app.modules.full_stat_adv_updater import wb_data_getter
from app.modules.full_stat_adv_updater.types.full_adv_stat import FullAdvStat
from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.modules.shop_runner.wb_statistic_manager.backend.common_stat_manager import (
    WBCommonStatManager,
)
from app.modules.wb_adv_updater import data_manager
from app.modules.wb_keywords_parser.global_parsing_queue_manager import (
    GlobalParsingQueueManager,
)
from app.settings import settings
from .old_modules.setting_auto_updater import (
    AdvSettingAutoUpdater,
)
from .old_modules.setting_auto_updater_v2 import AdvControlSystem
from .wb_shop_data_manager import WBShopDataManager
from .wb_shop_data_manager import ComplexAdv
from .while_coroutines_decorator import while_coroutine_decorator
from ..bidder.bidder_func import run_bidder_process_for_adv

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

    @while_coroutine_decorator(60, 60)
    async def update_cpm_bid(self) -> None:
        adv_settings = await self._wb_shop_data_manager.get_active_advs()
        if not adv_settings:
            return None
        adv_settings = [adv for adv in adv_settings if adv.bidder_active]
        if not adv_settings:
            return None
        logger.debug("Обновляю ставки для магазина %s", self.shop_id)
        await asyncio.gather(
            *[
                self.__run_bidder_process_for_adv(adv, self._wb_api)
                for adv in adv_settings
            ]
        )
        logger.debug(f"Все ставки обновлены для магазина {self.shop_id}")
        return None

    async def __run_bidder_process_for_adv(
        self, adv_setting: AdvSetting, wb_api: WBApi
    ) -> None:
        keywords = await self._wb_shop_data_manager.get_calculated_keywords(adv_setting)
        await run_bidder_process_for_adv(adv_setting, wb_api, keywords)

    @while_coroutine_decorator(5 * 60)
    async def update_common_sale_stat(self) -> None:
        wb_api = self._wb_api
        ping_manager = PingManager(wb_api.access, self._session)
        await ping_manager.ping_analytics_rights_and_connect()
        wb_stat_manager = WBCommonStatManager(wb_api)
        advs = await self._wb_shop_data_manager.get_active_advs()
        active_nmids = [adv.nmids[0] for adv in advs]
        await wb_stat_manager.update_common_statistic(active_nmids)

    @staticmethod
    async def _update_full_stat_in_click_house(stats: Iterable[FullAdvStat]) -> None:
        await full_wb_adv_stat.insert(stats)

    @while_coroutine_decorator(5 * 60, 1)
    async def update_full_adv_stat(self) -> None:
        wb_api = self._wb_api
        auto_advs: list[AdvSetting] = await self._wb_shop_data_manager.get_active_advs()

        all_adv_ids = set()
        for adv in auto_advs:
            all_adv_ids.add(adv.adv_id)
            if auction_adv_id := adv.search_adv_id:
                all_adv_ids.add(auction_adv_id)

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
        await data_manager.update_advs_data_from_wb_to_pg(self._wb_api)

    @staticmethod
    async def _async_zip_longest(
        *async_gens, fillvalue=None
    ) -> AsyncGenerator[tuple[Any, ...], None]:
        iterators = [gen.__aiter__() for gen in async_gens]
        finished = [False] * len(iterators)

        while not all(finished):
            row = []
            for i, it in enumerate(iterators):
                if finished[i]:
                    row.append(fillvalue)
                    continue
                try:
                    item = await it.__anext__()
                    row.append(item)
                except StopAsyncIteration:
                    finished[i] = True
                    row.append(fillvalue)
            yield tuple(row)

    @while_coroutine_decorator(60 * 15)
    async def update_cards_data_from_wb_to_pg(self) -> None:
        wb_api = self._wb_api
        shop_data_updater = ShopDataUpdater(wb_api)
        await self._update_cards_data_from_wb_to_pg(shop_data_updater)
        logger.debug("Обновление карточек завершено")

    @while_coroutine_decorator(60, 1)
    async def parsing_keywords_run(self) -> None:
        from .services import parsing_keywords_from_wb

        active_advs = await self._wb_shop_data_manager.get_active_advs()
        generators = []
        for adv in active_advs:
            keywords = self._wb_shop_data_manager.get_calculated_keywords(adv)

            generator: AsyncGenerator[tuple[str, int], None] = (
                parsing_keywords_from_wb.parsing_keywords_for_adv_generator(
                    adv, keywords
                )
            )
            generators.append(generator)
        zipped_generators = self._async_zip_longest(*generators)
        parsing_queue = GlobalParsingQueueManager()
        async for row in zipped_generators:
            for item in row:
                if item:  # Check if not fillvalue
                    text, nmid = item
                    await parsing_queue.add_or_update_task(text, {nmid})
                    await asyncio.sleep(
                        settings.PARSING_KEYWORDS_DELAY_BETWEEN_TASKS
                    )  # Добавляем небольшую задержку между задачами
                    logger.info(
                        "Добавлен ключ '%s' для артикула %s в очередь парсинга",
                        text,
                        nmid,
                    )

    @while_coroutine_decorator(5 * 60)
    async def adv_settings_auto_update(self):
        advs: list[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs()
        advs = [adv for adv in advs if adv.is_part_auto_setting_active]
        advs = [adv for adv in advs if adv.search_adv_active_status]
        update_tasks = []
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

        all_active_advs: list[AdvSetting] = (
            await self._wb_shop_data_manager.get_active_advs()
        )
        tasks = []
        for adv in all_active_advs:
            if not adv.auto_update_white_list:
                continue
            keywords: Awaitable[list[CalculatedKeyword]] = (
                self._wb_shop_data_manager.get_calculated_keywords(adv)
            )
            updater = FirstKeyUpdater(adv)
            update_coroutine: Coroutine[Any, Any, None] = updater.top_key_auto_update(
                keywords
            )
            task = asyncio.create_task(update_coroutine)
            tasks.append(task)

        for task in tasks:
            try:
                await task
            except FirstKeyUpdaterError as exc:
                logger.error("Ошибка обновления верхнего ключа: %s", exc, exc_info=True)
                raise exc

    @while_coroutine_decorator(60, 10)
    async def update_predict_ctr(self) -> None:
        """Обновление прогнозов CTR для всех активных кампаний"""
        from .services.predict_ctr_update_manager import PredictCTRUpdateManager

        advs = await self._wb_shop_data_manager.get_active_advs()

        if not advs:
            logger.debug("Нет активных кампаний для магазина %s", self.shop_id)
            return

        predict_ctr_manager = PredictCTRUpdateManager()

        try:
            all_coroutines = []

            logger.info(
                "Начинаем обновление прогнозов CTR для %s кампаний магазина %s",
                len(advs),
                self.shop_id,
            )

            # Собираем корутины для всех кампаний
            for adv in advs:
                # Получаем корутину для ключевых слов (не await!)
                keywords_coro = self._wb_shop_data_manager.get_calculated_keywords(adv)

                # Создаем корутину обновления прогнозов CTR
                update_coro = predict_ctr_manager.update_predict_ctr(adv, keywords_coro)
                all_coroutines.append(update_coro)

            await asyncio.gather(*all_coroutines)

        finally:
            # Закрываем соединения
            await predict_ctr_manager.close()

    @while_coroutine_decorator(15, 60)
    async def delete_keywords_from_wl_by_mean_auto_ctr(self) -> None:
        # TODO: Добавить функцию-фильтр для ComplexAdvs getter
        from .services import delete_keywords_from_wl_by_mean_auto_ctr
        complex_advs: Sequence[ComplexAdv] = await self._wb_shop_data_manager.get_complex_advs()
        complex_advs_with_white_list_by_mean_auto_ctr_active =\
            [adv for adv in complex_advs if adv.rec_system_promotion_mode_active
             and adv.auto_update_setting_version == 2
             and adv.is_white_list_control_enabled]

        tasks = []
        for adv in complex_advs_with_white_list_by_mean_auto_ctr_active:
            task = delete_keywords_from_wl_by_mean_auto_ctr(complex_adv=adv)
            tasks.append(task)

        results: Sequence[None | Exception] = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error('Ошибка удаления ключей из БС по сред.авто стр, shop_id: %s, adv_id: %s)',
                             self.shop_id, complex_advs[i].adv_id)



        return None
    @while_coroutine_decorator(15 * 60, 60)
    async def update_keywords_stamp(self) -> None:
        from .services.keyword_stamp_manager import KeywordStampManagerContainer, KeywordStampManager
        wb_manager_hub = WBManagerHubFactory.get_wb_manager_from_context()
        keyword_stamp_manager_container = KeywordStampManagerContainer(_wb_api_manager_hub=wb_manager_hub)
        keyword_stamp_manager: KeywordStampManager = keyword_stamp_manager_container.keyword_stamp_manager()

        advs = await self._wb_shop_data_manager.get_complex_advs()
        if not advs:
            return None
        update_tasks = []
        for adv in advs:
            task = keyword_stamp_manager.update_keywords_position_stamp(adv)
            update_tasks.append(task)

        results: list[Exception | None] = await asyncio.gather(*update_tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error('Ошибка обновления позиций из Api: %s', result, exc_info=True)


        return None

    @while_coroutine_decorator(24 * 60 * 60 * 60, 60)
    async def update_keywords_positions_history(self) -> None:
        from .services.keyword_stamp_manager import KeywordStampManagerContainer, KeywordStampManager
        wb_manager_hub = WBManagerHubFactory.get_wb_manager_from_context()
        keyword_stamp_manager_container = KeywordStampManagerContainer(_wb_api_manager_hub=wb_manager_hub)
        keyword_stamp_manager: KeywordStampManager = keyword_stamp_manager_container.keyword_stamp_manager()

        advs = await self._wb_shop_data_manager.get_complex_advs()
        if not advs:
            return None
        update_tasks = []
        for adv in advs:
            task = keyword_stamp_manager.update_keyword_history(adv)
            update_tasks.append(task)

        results: list[Exception | None] = await asyncio.gather(*update_tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error('Ошибка обновления позиций из Api: %s', result, exc_info=True)

        return None






# TODO: Частая ошибка - остановка РК в период раскрутки - сделать статью

