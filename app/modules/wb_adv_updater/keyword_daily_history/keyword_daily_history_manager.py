"""ClickHouse-менеджер для детальной дневной истории одного ключа."""

from __future__ import annotations

from datetime import date
from typing import cast

from clickhouse_connect.driver.query import QueryResult

from app.core.clickhouse_manager import BaseClickHouseManager
from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.common_slaves.wildberries.rebind_wb_adv_ids_history import (
    get_rebound_wb_adv_ids,
)
from app.modules.wb_adv_updater.keyword_daily_history.date_pagination import (
    get_total_pages,
    page_to_date_range,
)
from app.modules.wb_adv_updater.keyword_daily_history.dto import KeywordDailyStat
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.client import get_clickhouse_client as get_client


class KeywordDailyHistoryManager(BaseClickHouseManager):
    """Собирает статистику по одному ключевому запросу для bot UI."""

    async def get_history_page(
        self,
        keyword_setting: KeywordSetting,
        adv_setting: AdvSetting,
        page: int,
        page_size: int = 7,
    ) -> tuple[
        list[KeywordDailyStat],
        int,
        int,
        tuple[date, date] | None,
    ]:
        """Возвращает страницу дневной истории по ключу.

        Args:
            keyword_setting: Ключевое слово из PostgreSQL.
            adv_setting: Настройки кампании, к которой принадлежит ключ.
            page: Номер страницы, где page=1 соответствует самым свежим дням.
            page_size: Количество дней на страницу.

        Returns:
            Кортеж из списка строк истории, текущей страницы, общего числа
            страниц и минимальной даты данных.
        """
        if not adv_setting.nmids:
            return [], 1, 1, None

        adv_ids = await self._collect_adv_ids(adv_setting)
        earliest_date = await self.get_earliest_date(
            keyword_setting,
            adv_setting,
            adv_ids=adv_ids,
        )
        total_pages = get_total_pages(earliest_date, page_size=page_size)
        current_page = min(max(page, 1), total_pages)
        page_range = page_to_date_range(
            current_page,
            page_size=page_size,
            earliest_date=earliest_date,
        )
        if page_range is None:
            return [], current_page, total_pages, None

        start_date, end_date = page_range
        rows = await self._load_history_rows(
            keyword_setting=keyword_setting,
            adv_setting=adv_setting,
            adv_ids=adv_ids,
            start_date=start_date,
            end_date=end_date,
        )
        return rows, current_page, total_pages, page_range

    async def get_earliest_date(
        self,
        keyword_setting: KeywordSetting,
        adv_setting: AdvSetting,
        adv_ids: list[int] | None = None,
    ) -> date | None:
        """Возвращает первую дату, доступную для истории по ключу."""
        if not adv_setting.nmids:
            return None
        query = self._get_query("get_keyword_earliest_date")
        if adv_ids is None:
            adv_ids = await self._collect_adv_ids(adv_setting)
        if not adv_ids:
            return None
        params = self._build_query_params(
            keyword_setting,
            adv_setting,
            adv_ids=adv_ids,
        )
        async with anti_ch_crash_semaphore:
            async with get_client() as client:
                result: QueryResult = await client.query(query, parameters=params)
        if not result.result_rows:
            return None
        earliest_date = result.result_rows[0][0]
        return cast(date | None, earliest_date)

    async def _load_history_rows(
        self,
        *,
        keyword_setting: KeywordSetting,
        adv_setting: AdvSetting,
        start_date: date,
        end_date: date,
        adv_ids: list[int] | None = None,
    ) -> list[KeywordDailyStat]:
        """Выгружает строки истории за один диапазон дат."""
        if not adv_setting.nmids:
            return []
        query = self._get_query("get_keyword_daily_history")
        if adv_ids is None:
            adv_ids = await self._collect_adv_ids(adv_setting)
        if not adv_ids:
            return []
        params = self._build_query_params(
            keyword_setting,
            adv_setting,
            adv_ids=adv_ids,
            start_date=start_date,
            end_date=end_date,
        )
        async with anti_ch_crash_semaphore:
            async with get_client() as client:
                result: QueryResult = await client.query(query, parameters=params)

        history: list[KeywordDailyStat] = []
        for obj in result.named_results():  # pyright: ignore
            history.append(KeywordDailyStat.model_validate(obj))
        return history

    async def _collect_adv_ids(self, adv_setting: AdvSetting) -> list[int]:
        """Собирает current/rebind adv_id для фильтрации ClickHouse."""
        adv_ids: set[int] = set()
        adv_ids.add(adv_setting.adv_id)
        if adv_setting.search_adv_id is not None:
            adv_ids.add(adv_setting.search_adv_id)

        rebound_auto, rebound_auction = await get_rebound_wb_adv_ids(adv_setting.id)
        adv_ids.update(rebound_auto)
        adv_ids.update(rebound_auction)
        return sorted(adv_ids)

    def _build_query_params(
        self,
        keyword_setting: KeywordSetting,
        adv_setting: AdvSetting,
        adv_ids: list[int],
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, object]:
        """Формирует параметры запросов истории."""
        params: dict[str, object] = {
            "text": keyword_setting.text,
            "adv_ids": adv_ids,
            "nmids": list(adv_setting.nmids),
        }
        if start_date is not None:
            params["start_date"] = start_date
        if end_date is not None:
            params["end_date"] = end_date
        return params

