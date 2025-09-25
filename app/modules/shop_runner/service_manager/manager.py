import asyncio
import logging
from collections import defaultdict
from collections.abc import AsyncGenerator, Awaitable, Coroutine, Iterable
from datetime import datetime
from typing import (
    Any,
    Protocol,
    TypeVar,
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
from .wb_shop_data_manager import WBShopDataManager
from .while_coroutines_decorator import while_coroutine_decorator

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CoroutinesManagerProtocol(Protocol):
    def test(self): ...


class CoroutinesManager:
    def __init__(self, wb_api: WBApi):
        wb_cabinet = wb_api.wb_cabinet
        assert wb_cabinet
        self._wb_shop_data_manager = WBShopDataManager(wb_cabinet)

        self._wb_api = wb_api
        self.shop_id = wb_api.shop_id
        self.__keywords_for_advs: dict[int, list[CalculatedKeyword]] = defaultdict(list[CalculatedKeyword])
        self._adv_settings_dict: dict[int, AdvSetting] | None = None
        self._adv_settings_list: list[AdvSetting] | None = None
        self._session = wb_api.session

    @while_coroutine_decorator(1 * 60, 60)
    async def update_cpm_bid_in_search_advs(self) -> None:
        from .services.update_cpm import UpdateCPMManager

        adv_settings = await self._wb_shop_data_manager.get_active_advs()
        if not adv_settings:
            return None
        adv_keywords_coro: list[tuple[AdvSetting, Awaitable[list[CalculatedKeyword]]]] = []
        for adv in adv_settings:
            keywords_coro = self._wb_shop_data_manager.get_calculated_keywords(adv)
            adv_keywords_coro.append((adv, keywords_coro))
        update_cpm_manager = UpdateCPMManager(self.shop_id)
        await update_cpm_manager.update_cpms_in_search_advs(adv_keywords_coro)

        return None

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

        full_stats: list[FullAdvStat] = await wb_data_getter.get_full_adv_stat_for_adv_ids(
            wb_api, all_adv_ids, threshold_dates=settings.FULL_STAT_THRESHOLD_DATES
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
        wb_api = self._wb_api
        shop_data_updater = ShopDataUpdater(wb_api)
        await shop_data_updater.update_advs_data()

    @staticmethod
    async def _async_zip_longest(*async_gens, fillvalue=None) -> AsyncGenerator[tuple[Any, ...], None]:
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
                parsing_keywords_from_wb.parsing_keywords_for_adv_generator(adv, keywords)
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
                    logger.info(f"Добавлен ключ '{text}' для артикула {nmid} в очередь парсинга")

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
                exc.__traceback__ = None
                del exc

    @while_coroutine_decorator(60, 1)
    async def update_top_key_in_advs(self) -> None:
        from .old_modules.setting_auto_updater.modules.first_key_updater import (
            FirstKeyUpdater,
            FirstKeyUpdaterError,
        )

        all_active_advs: list[AdvSetting] = await self._wb_shop_data_manager.get_active_advs()
        tasks = []
        for adv in all_active_advs:
            if not adv.auto_update_white_list:
                continue
            keywords: Awaitable[list[CalculatedKeyword]] = self._wb_shop_data_manager.get_calculated_keywords(adv)
            updater = FirstKeyUpdater(adv)
            update_coroutine: Coroutine[Any, Any, None] = updater.top_key_auto_update(keywords)
            task = asyncio.create_task(update_coroutine)
            tasks.append(task)

        for task in tasks:
            try:
                await task
            except FirstKeyUpdaterError as exc:
                logger.error(f"Ошибка обновления верхнего ключа: {exc}", exc_info=True)
                raise exc

    @while_coroutine_decorator(60, 1)
    async def update_features_in_redis(self):
        from .services.redis_features_update_manager import (
            Neo4jtoRedisFeaturesUpdateManager,
        )

        advs = await self._wb_shop_data_manager.get_active_advs()
        redis_update_manager = Neo4jtoRedisFeaturesUpdateManager()
        all_coroutines = []
        for adv in advs:
            item_features_update_coro = redis_update_manager.update_items_features(adv)
            all_coroutines.append(item_features_update_coro)
            keywords = self._wb_shop_data_manager.get_calculated_keywords(adv)
            keywords_features_update_coroutines = redis_update_manager.update_keyword_features(keywords)
            all_coroutines.append(keywords_features_update_coroutines)

        await asyncio.gather(*all_coroutines)

    @while_coroutine_decorator(60, 10)
    async def update_data_in_neo4j(self) -> None:
        from .services.neo4j_data_update_manager import Neo4jDataUpdateManager

        advs = await self._wb_shop_data_manager.get_active_advs()
        neo4j_update_manager = Neo4jDataUpdateManager()

        try:
            all_coroutines = []

            # Обрабатываем товары для каждого объявления
            for adv in advs:
                item_update_coro = neo4j_update_manager.update_item(adv)
                all_coroutines.append(item_update_coro)

                # Получаем ключевые слова для объявления
                keywords = self._wb_shop_data_manager.get_calculated_keywords(adv)
                keywords_list = await keywords

                # Обрабатываем каждое ключевое слово
                for keyword in keywords_list:
                    keyword_update_coro = neo4j_update_manager.update_keyword_phrase(keyword.text)
                    all_coroutines.append(keyword_update_coro)

            # Выполняем все задачи параллельно
            await asyncio.gather(*all_coroutines)

        finally:
            # Закрываем gRPC каналы
            await neo4j_update_manager.close_channels()

    @while_coroutine_decorator(60, 10)
    async def update_predict_ctr(self) -> None:
        """Обновление прогнозов CTR для всех активных кампаний"""
        from .services.predict_ctr_update_manager import PredictCTRUpdateManager

        advs = await self._wb_shop_data_manager.get_active_advs()

        if not advs:
            logger.debug(f"Нет активных кампаний для магазина {self.shop_id}")
            return

        predict_ctr_manager = PredictCTRUpdateManager()

        try:
            all_coroutines = []

            logger.info(f"Начинаем обновление прогнозов CTR для {len(advs)} кампаний магазина {self.shop_id}")

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
