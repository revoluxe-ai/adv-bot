"""Чтение статистики из ClickHouse и контекста (ставка из Redis-кэша, цена из Postgres)."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, cast
from zoneinfo import ZoneInfo

from clickhouse_connect.driver.query import QueryResult
from sqlalchemy import select

from app.core.di.wb_manager_hub import WBManagerHub
from app.modules.common_slaves.wildberries.models import WBCard
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.client import get_clickhouse_client
from app.utils.db.session_maker import get_async_session_maker as sm

from .dto import AutoShelfBidSnapshot, AutoShelfRawStat
from .redis_auto_recommendations_bid_value_manager import (
    RedisAutoRecommendationsBidValueManager,
)

logger = logging.getLogger(__name__)


class AutoShelfBidRepository:
    """Загрузка SQL из sql/ и маппинг результатов в DTO."""

    def __init__(
        self,
        wb_manager_hub: WBManagerHub,
        tz_name: str = "Europe/Moscow",
        auto_recommendations_bid_cache_manager: RedisAutoRecommendationsBidValueManager | None = None,
        max_bid_age_sec: int = 60 * 5,
    ) -> None:
        """tz_name — часовой пояс для report_date (по умолчанию Москва)."""
        self._wb_manager_hub = wb_manager_hub
        self._tz = ZoneInfo(tz_name)
        self._sql_dir = Path(__file__).parent.joinpath("sql")
        self._auto_recommendations_bid_cache_manager = (
            auto_recommendations_bid_cache_manager
        )
        self._max_bid_age_sec = max(30, max_bid_age_sec)

    def _today_date(self) -> str:
        """Текущая дата отчёта YYYY-MM-DD в tz репозитория."""
        return datetime.now(self._tz).strftime("%Y-%m-%d")

    def _load_sql(self, filename: str) -> str:
        """Прочитать текст SQL-файла из каталога sql/."""
        return self._sql_dir.joinpath(filename).read_text(encoding="utf-8")

    async def fetch_total_auto_stat(self, auto_adv_id: int) -> AutoShelfRawStat | None:
        """Суммарная дневная статистика Auto-РК (fetch_total_auto_stat.sql)."""
        query = self._load_sql("fetch_total_auto_stat.sql")
        params = {"report_date": self._today_date(), "auto_adv_id": auto_adv_id}
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                result: QueryResult = await client.query(query, parameters=params)
        if not result.result_set:
            return None
        row: dict[str, Any] = cast(dict[str, Any], result.first_item)
        return AutoShelfRawStat(
            impressions=int(row["impressions"]),
            clicks=int(row["clicks"]),
            carts=int(row["carts"]),
            orders=int(row["orders"]),
            spend=float(row["spend"]),
        )

    async def fetch_keyword_stat(self, auto_adv_id: int, nmid: int) -> AutoShelfRawStat | None:
        """Сумма по кластерам/ключам (fetch_keyword_stat.sql); None если нет строк."""
        query = self._load_sql("fetch_keyword_stat.sql")
        params = {
            "report_date": self._today_date(),
            "auto_adv_id": auto_adv_id,
            "nmid": nmid,
        }
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                result: QueryResult = await client.query(query, parameters=params)
        if not result.result_set:
            return None
        row: dict[str, Any] = cast(dict[str, Any], result.first_item)
        return AutoShelfRawStat(
            impressions=int(row["impressions"]),
            clicks=int(row["clicks"]),
            carts=int(row["carts"]),
            orders=int(row["orders"]),
            spend=float(row["spend"]),
        )

    async def fetch_prev_auto_shelf_bid(self, nmid: int) -> AutoShelfBidSnapshot | None:
        """Последний prev из CH (get_prev_auto_shelf_bid.sql)."""
        query = self._load_sql("get_prev_auto_shelf_bid.sql")
        params = {"nmid": nmid}
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                result: QueryResult = await client.query(query, parameters=params)
        if not result.result_rows:
            return None
        column_names = cast(tuple[str, ...], result.column_names)
        row_values = tuple(result.result_rows[0])
        row: dict[str, Any] = dict(zip(column_names, row_values))
        # bucket_start not stored in prev table; use src_ts for compatibility.
        row["bucket_start"] = row["src_ts"]
        return AutoShelfBidSnapshot.from_clickhouse(row)

    async def fetch_current_auto_common_bid(
        self,
        complex_adv: ComplexAdv,
        nmid: int,
    ) -> int | None:
        """Ставка полок из Redis-кэша, заполненного минутным updater потоком."""
        cache_manager = self._auto_recommendations_bid_cache_manager
        auto_adv_id = complex_adv.auto_adv_id
        if cache_manager is None:
            logger.warning(
                "auto_recommendations_bid_cache_unconfigured auto_adv_id=%s nmid=%s",
                auto_adv_id,
                nmid,
            )
            return None
        cached = await cache_manager.get_bid(auto_adv_id, nmid)
        if cached is None:
            logger.warning(
                "auto_recommendations_bid_cache_miss auto_adv_id=%s nmid=%s",
                auto_adv_id,
                nmid,
            )
            return None
        cached_updated_at = cached.updated_at
        if cached_updated_at.tzinfo is None:
            cached_updated_at = cached_updated_at.replace(tzinfo=self._tz)
        age_sec = (datetime.now(self._tz) - cached_updated_at).total_seconds()
        if age_sec > self._max_bid_age_sec:
            logger.warning(
                "auto_recommendations_bid_cache_stale auto_adv_id=%s nmid=%s age_sec=%.3f max_age_sec=%s",
                auto_adv_id,
                nmid,
                age_sec,
                self._max_bid_age_sec,
            )
            return None
        logger.info(
            "auto_recommendations_bid_cache_hit auto_adv_id=%s nmid=%s age_sec=%.3f",
            auto_adv_id,
            nmid,
            age_sec,
        )
        return cached.bid_minor

    async def fetch_current_price_minor(self, nmid: int) -> int | None:
        """Цена в minor из WBCard.json; ошибки → None (не блокирует update)."""
        try:
            async with sm(read_only=True) as session:
                row = await session.execute(
                    select(WBCard.json).where(WBCard.nmid == nmid).limit(1)
                )
            card_json_raw = row.scalar_one_or_none()
            if not isinstance(card_json_raw, str):
                return None
            import json

            payload_obj = json.loads(card_json_raw)
            if not isinstance(payload_obj, dict):
                return None
            payload = cast(dict[str, Any], payload_obj)
            return self._extract_price_minor_from_card_json(payload)
        except Exception:
            logger.warning(
                "auto_shelf_bid_price_fetch_failed nmid=%s source=wbcard_json",
                nmid,
                exc_info=True,
            )
            return None

    def _extract_price_minor_from_card_json(self, payload: dict[str, Any]) -> int | None:
        """Парсинг priceU/salePriceU или рублёвых полей ×100 из JSON карточки."""
        direct_minor_keys = ("salePriceU", "priceU")
        for key in direct_minor_keys:
            value = payload.get(key)
            if isinstance(value, int) and value > 0:
                return value

        sizes = payload.get("sizes")
        if isinstance(sizes, list):
            for size in sizes:
                if not isinstance(size, dict):
                    continue
                price_obj = size.get("price")
                if isinstance(price_obj, dict):
                    for key in direct_minor_keys:
                        value = price_obj.get(key)
                        if isinstance(value, int) and value > 0:
                            return value
                for key in direct_minor_keys:
                    value = size.get(key)
                    if isinstance(value, int) and value > 0:
                        return value

        # Fallback to ruble-like numeric fields.
        direct_ruble_keys = ("price", "salePrice", "discountedPrice")
        for key in direct_ruble_keys:
            value = payload.get(key)
            if isinstance(value, (int, float)) and value > 0:
                return int(round(float(value) * 100))

        if isinstance(sizes, list):
            for size in sizes:
                if not isinstance(size, dict):
                    continue
                price_obj = size.get("price")
                if isinstance(price_obj, dict):
                    for key in direct_ruble_keys:
                        value = price_obj.get(key)
                        if isinstance(value, (int, float)) and value > 0:
                            return int(round(float(value) * 100))
        return None

    async def get_current_mode(self, nmid: int) -> str:
        """Режим размещения; v1 всегда main."""
        _ = nmid
        return "main"

