"""Чтение статистики из ClickHouse и контекста для auto_shelf инкрементов.

Обязанности v1:
    - total/keyword/prev статистика из ClickHouse (SQL в sql/);
    - текущая ставка полок (`bid_minor`) из Redis-кэша минутного updater.

Что намеренно НЕ входит в v1:
    - получение цены товара (`price_minor`) из Postgres/WBCard или WB API.
    - Цена в snapshot всегда `NULL`; задаётся в `AutoShelfBidIncrementManager.update()`.
    - Методы fetch price удалены намеренно — не dead code regression, а упрощение
      pipeline под контракт v1 (см. README, раздел «Для ревью»).
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, cast
from zoneinfo import ZoneInfo

from clickhouse_connect.driver.query import QueryResult

from app.domain.rec_system_bid_math.hour_observation_builder import (
    BidBucketObservation,
)
from app.core.di.wb_manager_hub import WBManagerHub
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.client import get_clickhouse_client

from .dto import AutoShelfBidSnapshot, AutoShelfRawStat
from .redis_auto_recommendations_bid_value_manager import (
    RedisAutoRecommendationsBidValueManager,
)
from ..auto_shelf_bid_control_manager.auto_shelf_bid_control_repository import (
    AutoShelfBidControlRepository,
)

logger = logging.getLogger(__name__)


def build_bid_bucket_observations_from_ch_rows(
    rows: list[dict[str, object]],
) -> list[BidBucketObservation]:
    """Собрать 15-минутные bucket-объекты из CH rows без бизнес-логики.

    Ожидаются минимум поля:
        - bid_minor / bid
        - bucket_start
        - delta_impressions / impressions
    """
    grouped: dict[datetime, list[dict[str, object]]] = {}
    for row in rows:
        bucket_start = row.get("bucket_start")
        if not isinstance(bucket_start, datetime):
            raise KeyError("row is missing bucket_start")
        grouped.setdefault(bucket_start, []).append(row)

    observations: list[BidBucketObservation] = []
    for bucket_start, bucket_rows in grouped.items():
        bid_values: set[int] = set()
        for row in bucket_rows:
            bid_value = row.get("bid_minor", row.get("bid"))
            if bid_value is not None:
                bid_values.add(int(cast(Any, bid_value)))
        if len(bid_values) != 1:
            continue

        price_values: set[int | None] = set()
        for row in bucket_rows:
            price_value = row.get("price_minor")
            price_values.add(None if price_value is None else int(cast(Any, price_value)))
        if len(price_values) != 1:
            continue

        impressions_sum = 0.0
        for row in bucket_rows:
            impressions_value = row.get("delta_impressions", row.get("impressions"))
            if impressions_value is None:
                raise KeyError("row is missing delta_impressions/impressions")
            impressions_sum += float(cast(Any, impressions_value))

        if impressions_sum < 0:
            continue

        observations.append(
            BidBucketObservation(
                bid=next(iter(bid_values)),
                bucket_start=bucket_start,
                impressions=impressions_sum,
                price_minor=next(iter(price_values)),
            )
        )

    return observations


class AutoShelfBidRepository:
    """Загрузка SQL из sql/ и маппинг результатов в DTO.

    Граница ответственности:
        - CH-запросы и маппинг в `AutoShelfRawStat` / `AutoShelfBidSnapshot`;
        - Redis-кэш recommendations bid (`fetch_current_auto_common_bid`).

    Не отвечает за:
        - расчёт delta и контрактные ветки (это `AutoShelfBidIncrementManager`);
        - цену товара в v1 (поле `price_minor` в snapshot заполняется в менеджере).
    """

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
        self._control_repository = AutoShelfBidControlRepository()

    def _today_date(self) -> str:
        """Текущая дата отчёта YYYY-MM-DD в tz репозитория."""
        return datetime.now(self._tz).strftime("%Y-%m-%d")

    def _load_sql(self, filename: str) -> str:
        """Прочитать текст SQL-файла из каталога sql/."""
        return self._sql_dir.joinpath(filename).read_text(encoding="utf-8")

    @staticmethod
    def _to_int(value: object) -> int:
        """Безопасно привести значение CH к int."""
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            return int(value)
        raise TypeError(f"Cannot cast to int: {type(value)!r}")

    @staticmethod
    def _to_float(value: object) -> float:
        """Безопасно привести значение CH к float."""
        if isinstance(value, bool):
            return float(int(value))
        if isinstance(value, int | float):
            return float(value)
        if isinstance(value, str):
            return float(value)
        raise TypeError(f"Cannot cast to float: {type(value)!r}")

    async def fetch_total_auto_stat(self, auto_adv_id: int) -> AutoShelfRawStat | None:
        """Суммарная дневная статистика Auto-РК (fetch_total_auto_stat.sql)."""
        query = self._load_sql("fetch_total_auto_stat.sql")
        params = {"report_date": self._today_date(), "auto_adv_id": auto_adv_id}
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                result: QueryResult = await client.query(query, parameters=params)
        if not result.result_rows:
            return None
        raw_column_names = cast(
            tuple[object, ...],
            result.column_names,  # pyright: ignore[reportUnknownMemberType]
        )
        column_names = [str(name) for name in raw_column_names]
        row_values = tuple(result.result_rows[0])
        row: dict[str, object] = dict(zip(column_names, row_values))
        return AutoShelfRawStat(
            impressions=self._to_int(row["impressions"]),
            clicks=self._to_int(row["clicks"]),
            carts=self._to_int(row["carts"]),
            orders=self._to_int(row["orders"]),
            spend=self._to_float(row["spend"]),
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
        if not result.result_rows:
            return None
        raw_column_names = cast(
            tuple[object, ...],
            result.column_names,  # pyright: ignore[reportUnknownMemberType]
        )
        column_names = [str(name) for name in raw_column_names]
        row_values = tuple(result.result_rows[0])
        row: dict[str, object] = dict(zip(column_names, row_values))
        return AutoShelfRawStat(
            impressions=self._to_int(row["impressions"]),
            clicks=self._to_int(row["clicks"]),
            carts=self._to_int(row["carts"]),
            orders=self._to_int(row["orders"]),
            spend=self._to_float(row["spend"]),
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
        raw_column_names = cast(
            tuple[object, ...],
            result.column_names,  # pyright: ignore[reportUnknownMemberType]
        )
        column_names = tuple(str(name) for name in raw_column_names)
        row_values = tuple(result.result_rows[0])
        row: dict[str, object] = dict(zip(column_names, row_values))
        # bucket_start not stored in prev table; use src_ts for compatibility.
        row["bucket_start"] = row["src_ts"]
        return AutoShelfBidSnapshot.from_clickhouse(row)

    async def fetch_rec_bid_bucket_observations_for_nmid(
        self,
        nmid: int,
        mode: str,
        date_from: datetime,
        date_to: datetime,
    ) -> list[BidBucketObservation]:
        """Read-only bucket fetch for rec_system bid ranking."""
        query = self._load_sql("fetch_auto_shelf_bid_bucket_rows.sql")
        params = {
            "nmid": nmid,
            "date_from": date_from,
            "date_to": date_to,
        }
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                result: QueryResult = await client.query(query, parameters=params)
        if not result.result_rows:
            return []
        raw_column_names = cast(
            tuple[object, ...],
            result.column_names,  # pyright: ignore[reportUnknownMemberType]
        )
        column_names = [str(name) for name in raw_column_names]
        rows = [dict(zip(column_names, tuple(row))) for row in result.result_rows]
        return build_bid_bucket_observations_from_ch_rows(rows)

    async def fetch_rec_bid_ctr_by_bid_for_nmid(
        self,
        nmid: int,
        mode: str,
        date_from: datetime,
        date_to: datetime,
    ) -> dict[int, float]:
        """Return real CTR by bid from read-only CH aggregation."""
        query = self._load_sql("fetch_rec_bid_ctr_by_bid.sql")
        params = {
            "nmid": nmid,
            "date_from": date_from,
            "date_to": date_to,
        }
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                result: QueryResult = await client.query(query, parameters=params)
        if not result.result_rows:
            return {}
        raw_column_names = cast(
            tuple[object, ...],
            result.column_names,  # pyright: ignore[reportUnknownMemberType]
        )
        column_names = [str(name) for name in raw_column_names]
        ctr_by_bid: dict[int, float] = {}
        for row in result.result_rows:
            row_dict = dict(zip(column_names, tuple(row)))
            bid = self._to_int(row_dict["bid"])
            impressions = self._to_float(row_dict["impressions"])
            clicks = self._to_float(row_dict["clicks"])
            ctr_by_bid[bid] = clicks / impressions if impressions > 0 else 0.0
        return ctr_by_bid

    async def fetch_current_auto_common_bid(
        self,
        complex_adv: ComplexAdv,
        nmid: int,
    ) -> int | None:
        """Ставка полок из Redis-кэша, заполненного минутным updater потоком.

        Цена товара здесь намеренно не читается — v1 unknown price задаётся
        в менеджере (`price_minor=None`). См. README «Для ревью» п.2.
        """
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

    async def get_current_mode(self, nmid: int) -> str:
        """Вернуть mode из control state при включенном флаге, иначе main."""
        return await self._control_repository.get_mode_for_nmid(nmid)
