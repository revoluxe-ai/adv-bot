import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import (
    Iterable,
    AsyncGenerator,
    TypeVar,
    Tuple,
    Awaitable,
    Any,
    Coroutine,
    Protocol,
)

from app.core.wb_api.ping_manager import PingManager
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
)
from app.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater
from app.modules.full_stat_adv_updater import wb_data_getter
from app.modules.full_stat_adv_updater.types import FullAdvStat
from app.modules.shop_runner.bidder.bidder_func import run_bidder_process_for_adv
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
from .old_modules.setting_auto_updater.modules.white_list_updater.auto_white_list_updater.exceptions import (
    AutoUpdateWhiteListFatalError,
)
from .wb_shop_data_manager import WBShopDataManager
from .while_coroutines_decorator import while_coroutine_decorator

logger = logging.getLogger(__name__)


T = TypeVar("T")


class CoroutinesManagerProtocol(Protocol):
    def test(self): ...


class CoroutinesManager:

    def __init__(self, wb_api: WBApi):
        wb_cabinet = wb_api.wb_cabinet
        self._wb_shop_data_manager = WBShopDataManager(wb_cabinet)

        self._wb_api = wb_api
        self.shop_id = wb_api.shop_id
        self.__keywords_for_advs: dict[int, list[CalculatedKeyword]] = defaultdict(
            list[CalculatedKeyword]
        )
        self._adv_settings_dict: dict[int, AdvSetting] | None = None
        self._adv_settings_list: list[AdvSetting] | None = None

    @while_coroutine_decorator(10 * 60, 60)
    async def update_cpm_bid(self) -> None:
        adv_settings = await self._wb_shop_data_manager.get_active_advs()
        if not adv_settings:
            return None
        adv_settings = [adv for adv in self._adv_settings_list if adv.bidder_active]
        if not adv_settings:
            return None
        logger.debug(f"Обновляю ставки для магазина {self.shop_id}")
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

    @while_coroutine_decorator(15 * 60)
    async def update_common_sale_stat(self) -> None:
        wb_api = self._wb_api
        ping_manager = PingManager(wb_api.access)
        await ping_manager.ping_analytics_rights_and_connect()
        wb_stat_manager = WBCommonStatManager(wb_api)
        advs = await self._wb_shop_data_manager.get_active_advs()
        active_nmids = [adv.adv_id for adv in advs]
        await wb_stat_manager.update_common_statistic(active_nmids)

    @staticmethod
    async def _update_full_stat_in_click_house(stats: Iterable[FullAdvStat]) -> None:
        await full_wb_adv_stat.insert(stats)

    @while_coroutine_decorator(15 * 60, 1)
    async def update_full_adv_stat(self) -> None:
        wb_api = self._wb_api
        auto_advs: list[AdvSetting] = await self._wb_shop_data_manager.get_active_advs()

        all_adv_ids = set()
        for adv in auto_advs:
            all_adv_ids.add(adv.adv_id)
            all_adv_ids.add(adv.auction_adv_id)

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
    @while_coroutine_decorator(15 * 60, 5)
    async def _update_adv_data_from_wb_to_pg(
        shop_data_updater: ShopDataUpdater,
    ) -> None:
        await shop_data_updater.update_advs_data()

    @staticmethod
    @while_coroutine_decorator(15 * 60, 5)
    async def _update_cards_data_from_wb_to_pg(
        shop_data_updater: ShopDataUpdater,
    ) -> None:
        await shop_data_updater.update_cards_data()

    @while_coroutine_decorator(15 * 60, 1)
    async def update_advs_data_from_wb_to_pg(self) -> None:
        wb_api = self._wb_api
        shop_data_updater = ShopDataUpdater(wb_api)
        await shop_data_updater.update_advs_data()

    @staticmethod
    async def async_zip_longest(
        *async_gens, fillvalue=None
    ) -> AsyncGenerator[Tuple[Any, ...], None]:
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

    @while_coroutine_decorator(60 * 60)
    async def update_cards_data_from_wb_to_pf(self) -> None:
        wb_api = self._wb_api
        shop_data_updater = ShopDataUpdater(wb_api)
        await self._update_cards_data_from_wb_to_pg(shop_data_updater)
        logger.debug("Обновление карточек завершено")

    @while_coroutine_decorator(1, 1)
    async def parsing_keywords_run(self) -> None:
        from .services import parsing_keywords_from_wb

        active_advs = await self._wb_shop_data_manager.get_active_advs()
        generators = []
        for adv in active_advs:
            keywords = self._wb_shop_data_manager.get_calculated_keywords(adv)

            generator: AsyncGenerator[Tuple[str, int], None] = (
                parsing_keywords_from_wb.parsing_keywords_for_adv_generator(
                    adv, keywords
                )
            )
            generators.append(generator)
        zipped_generators = self.async_zip_longest(*generators)
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
                        f"Добавлен ключ '{text}' для артикула {nmid} в очередь парсинга"
                    )

    async def _update_phrases_in_white_list_run(self) -> None:
        """
        Проверяет себестоимость заказа и убирает ключи из белого списка, если себес превышен
        Returns:
            None
        """
        try:
            await self._update_advs_models()
        except Exception as exc:
            raise AutoUpdateWhiteListFatalError from exc

        advs = self._adv_settings

        from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.modules.white_list_updater.auto_white_list_updater import (
            WhiteListUpdateManager,
        )

        update_manager = WhiteListUpdateManager()

        tasks = []
        for adv in advs:
            if adv.auto_update_white_list:
                try:
                    keywords = await self.get_calculated_keywords(adv.adv_id)
                except Exception as exc:
                    raise AutoUpdateWhiteListFatalError from exc

                task = asyncio.create_task(
                    update_manager.auto_update_phrases_in_white_list(adv, keywords)
                )
                tasks.append(task)
        for task in tasks:
            try:
                await task
            except AutoUpdateWhiteListFatalError as exc:
                logger.error(
                    f"Ошибка автообновления белого списка {exc}", exc_info=True
                )

    #
    # async def update_phrases_in_white_list_run(self) -> None:
    #     while True:
    #         try:
    #             await self._update_phrases_in_white_list_run()
    #             await asyncio.sleep(60 * 15)
    #         except AutoUpdateWhiteListFatalError as exc:
    #             logger.error(f"Ошибка обновления белого списка: {exc}", exc_info=True)
    #             await asyncio.sleep(60 * 15)

    @while_coroutine_decorator(5 * 60)
    async def adv_settings_auto_update(self):

        active_advs = await self._wb_shop_data_manager.get_active_advs()

        update_tasks = []
        last_days_for_analyze = 2
        for adv in active_advs:
            if not (adv.auto_update_white_list or adv.auto_update_target_place):
                continue
            adv_updater = AdvSettingAutoUpdater(adv, last_days_for_analyze)
            keywords = self._wb_shop_data_manager.get_calculated_keywords(adv)
            adv_update = adv_updater.update(keywords)
            adv_update_task = asyncio.create_task(adv_update)
            update_tasks.append(adv_update_task)

        for task in update_tasks:
            try:
                await task
            except Exception as exc:
                logger.error(
                    f"Критическая ошибка автообновления настроек РК {exc}",
                    exc_info=True,
                )

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
                logger.error(f"Ошибка обновления верхнего ключа: {exc}", exc_info=True)
                raise exc
