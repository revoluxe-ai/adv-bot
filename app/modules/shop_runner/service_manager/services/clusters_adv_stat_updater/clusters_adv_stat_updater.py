import asyncio
import logging
from collections import defaultdict
from collections.abc import AsyncGenerator
from datetime import date, timedelta
from typing import TYPE_CHECKING, Awaitable, Any

if TYPE_CHECKING:
    from app.core.mp.wb.api.adapter.promotion_client.normquery_stats import NormqueryStatsDTO
    from app.core.di.wb_manager_hub import WBManagerHub
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import ComplexAdv
from .click_house_clusters_stat_manager import click_house_clusters_stat_manager as ch

logger = logging.getLogger(__name__)



class ClustersAdvStatUpdater:
    def __init__(self, wb_manager_hub: "WBManagerHub"):
        self._wb_manager_hub = wb_manager_hub

    async def update_today_stats(self, complex_advs: list[ComplexAdv]) -> set[int]:
        """
        Обновляет статистику кластеров за сегодня (без проверки наличия данных).

        Предназначен для частого вызова в отдельной корутине.
        """
        if not complex_advs:
            return set()

        today = date.today()
        stats = await self._get_stats_for_day(complex_advs, today)
        adv_ids_to_ids: dict[int, int] = {}
        for adv in complex_advs:
            if adv_id := adv.adv_id:
                adv_ids_to_ids[adv_id] = adv.original_adv_setting_id
            if adv_id := adv.search_adv_id:
                adv_ids_to_ids[adv_id] = adv.original_adv_setting_id

        if stats:
            await ch.update_clusters_adv_stats(stats)
            logger.info("Обновлена статистика за сегодня: %d записей", len(stats))
            await self._create_keyword_setting(complex_advs, stats)
            success_adv_original_ids: set[int] = set()
            for stat in stats:
                original_adv_id: int = adv_ids_to_ids[stat.adv_id]
                success_adv_original_ids.add(original_adv_id)
            return success_adv_original_ids
        return set()


    async def update_past_days_stats(
        self, complex_advs: list[ComplexAdv], for_last_days: int = 365
    ) -> None:
        """
        Обновляет статистику кластеров за прошлые дни.

        Проверяет наличие данных в ClickHouse и загружает только недостающие.
        Предназначен для редкого вызова в отдельной корутине.
        """
        if not complex_advs:
            return

        # Получить словарь недостающих дат для прошлых дней
        missing_dates_map = await self._get_missing_dates_map(complex_advs, for_last_days)

        if not missing_dates_map:
            logger.info("Все данные за прошлые дни уже есть в ClickHouse")
            return
        # Собрать статистику за все недостающие даты
        all_stats_generator: AsyncGenerator[list[NormqueryStatsDTO], Any] \
            = self.__get_all_stats_generator(missing_dates_map)
        from app.modules.keywords_manager.keywords_manager import KeywordsManager
        keywords_manager = KeywordsManager()
        # Записать все данные одним батчем
        async for all_stats in all_stats_generator:
            # TODO: Объединить обе задачи и тут, и в подневной записи, запараллелить
            await ch.update_clusters_adv_stats(all_stats)
            await keywords_manager.create_new_keyword_settings_for_complex_advs(complex_advs, all_stats)
            logger.debug(
                "Записано %d записей статистики за %d дней",
                len(all_stats),
                len(missing_dates_map)
            )
    @staticmethod
    async def _get_missing_dates_map(
        complex_advs: list[ComplexAdv], for_last_days: int
    ) -> dict[date, list[ComplexAdv]]:
        """
        Возвращает словарь {дата: список ComplexAdv без статистики за эту дату}.

        Проверяет наличие данных в ClickHouse по комбинации (adv_id, nmid, date).
        """
        if not complex_advs:
            return {}

        today = date.today()
        yesterday = today - timedelta(days=1)
        start_date = today - timedelta(days=for_last_days)

        # Собираем пары (adv_id, nmid) из complex_advs
        adv_nmid_pairs: list[tuple[int, int]] = [
            (adv.adv_id, adv.main_nmid) for adv in complex_advs
        ]

        # Создаем маппинг (adv_id, nmid) -> ComplexAdv для быстрого поиска
        adv_by_pair: dict[tuple[int, int], ComplexAdv] = {
            (adv.adv_id, adv.main_nmid): adv for adv in complex_advs
        }

        # Получаем существующие комбинации из ClickHouse
        existing = await ch.get_existing_adv_nmid_dates(
            adv_nmid_pairs, start_date, yesterday
        )

        # Формируем словарь недостающих дат
        missing_map: dict[date, list[ComplexAdv]] = defaultdict(list)

        # Для каждой даты в диапазоне проверяем какие adv отсутствуют
        current_date = yesterday
        while current_date >= start_date:
            for pair, adv in adv_by_pair.items():
                adv_id, nmid = pair
                if (adv_id, nmid, current_date) not in existing:
                    missing_map[current_date].append(adv)
            current_date -= timedelta(days=1)

        # Преобразуем defaultdict в обычный dict
        return dict(missing_map)

    async def _get_stats_for_day(
        self, complex_advs: list[ComplexAdv], day: date
    ) -> list["NormqueryStatsDTO"]:
        """Получает статистику за один день для списка ComplexAdv."""
        result = await self._wb_manager_hub.wb_data_manager.get_norn_query_stat_for_date_range(
            complex_advs=complex_advs,
            date_from=day,
            date_to=day
        )
        if result:
            # Устанавливаем день для каждого DTO
            for dto in result:
                dto.day = day
            return result
        return []


    async def get_stats_for_days(
        self, complex_advs: list[ComplexAdv], days: list[date]
    ) -> list["NormqueryStatsDTO"]:
        """Получает статистику за несколько дней параллельно."""
        tasks: list[Awaitable[list["NormqueryStatsDTO"]]] = []
        for day in days:
            task = self._get_stats_for_day(complex_advs, day)
            tasks.append(task)

        raw_results: list[list["NormqueryStatsDTO"]  | BaseException] = await asyncio.gather(*tasks,
                                                                                             return_exceptions=True)
        dtos: list["NormqueryStatsDTO"] = []
        for n, result in enumerate(raw_results):
            day = days[n]
            if isinstance(result, list):
                dtos.extend(result)
            elif isinstance(result, Exception):
                logger.error(
                    "Ошибка получения статистики за %s", day, exc_info=True
                )
        return dtos

    @staticmethod
    def __check_empty_stats(day_stats: list["NormqueryStatsDTO"]) -> bool:
        for stat in day_stats:
           if stat.stats:
               return False
        else:
            return True
    @staticmethod
    async def _create_keyword_setting(complex_advs: list[ComplexAdv],
                                      stats: list["NormqueryStatsDTO"]) -> None:
        from app.modules.keywords_manager.keywords_manager import KeywordsManager
        # TODO: Сюда прошла ошибка в рантайм
        keywords_manager = KeywordsManager()
        await keywords_manager.create_new_keyword_settings_for_complex_advs(complex_advs, stats)
        return None



    async def __get_all_stats_generator(self, missing_dates_map: dict[date, list[ComplexAdv]]):
        for day, advs_for_day in missing_dates_map.items():
            day_stats = await self._get_stats_for_day(advs_for_day, day)
            if self.__check_empty_stats(day_stats):
                break
            yield day_stats

