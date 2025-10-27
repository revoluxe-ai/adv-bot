"""
Менеджер инкрементальной статистики.

Вместо хранения дневных агрегатов, сохраняет изменения (дельты) 
статистики с точным timestamp, что позволяет:
- Отслеживать продажи за любой период (час, 2 часа, день)
- Видеть реальные тренды в течение дня
- Быстро реагировать на изменения
- Детектировать всплески и аномалии

Обновляется каждые 5 минут вместе с основной статистикой.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core.wb_api.mixins.statistic_mixin.wb_statistic_obj import CommonStat
from app.modules.full_stat_adv_updater.types.full_adv_stat import FullAdvStat, DayStats
from app.utils.click_house.client import get_clickhouse_client

logger = logging.getLogger(__name__)


class BaseIncrementalManager(ABC):
    """
    Базовый менеджер для инкрементальной статистики (DRY).
    
    Общая логика для IncrementalCommonStatManager и IncrementalAdvStatManager.
    """

    table_name: str  # Переопределяется в наследниках
    key_field: str  # nmid или adv_id

    async def get_total_for_period(
        self, key_value: int | list[int], hours: int, metric: str
    ) -> float:
        """
        Универсальный метод получения суммы за период.

        Args:
            key_value: Значение ключа (nmid или adv_id) или список значений
            hours: Период в часах
            metric: Название метрики ('orders', 'spend', и т.д.)

        Returns:
            Сумма метрики за период
        """
        start_time = datetime.now() - timedelta(hours=hours)

        # Используем материализованное представление для быстроты
        hourly_table = self.table_name.replace("_incremental", "_hourly")

        # Поддержка списка ключей
        if isinstance(key_value, list):
            key_value = [k for k in key_value if k is not None]
            if not key_value:
                return 0.0
            key_condition = f"{self.key_field} IN %(key_value)s"
        else:
            key_condition = f"{self.key_field} = %(key_value)s"

        query = f"""
            SELECT sumMerge({metric}_sum) as total
            FROM {hourly_table}
            WHERE {key_condition}
              AND hour_start >= %(start_time)s
        """

        try:
            async with get_clickhouse_client() as client:
                res = await client.query(
                    query,
                    parameters={"key_value": key_value, "start_time": start_time},
                )
                return float(res.first_item["total"] or 0) if res.first_item else 0.0
        except Exception as exc:
            logger.error(
                f"Ошибка получения {metric} за период из {hourly_table}: {exc}",
                exc_info=True,
            )
            return 0.0

    @abstractmethod
    async def _get_previous_totals(self, keys: list, dates: list) -> dict:
        """Получает предыдущие значения из старой таблицы"""
        pass

    @abstractmethod
    async def _insert_incremental(self, incremental_stats: list) -> None:
        """Вставляет инкрементальные записи батчем (оптимизация для ClickHouse)"""
        pass


@dataclass
class IncrementalCommonStat:
    """Инкрементальная статистика карточки - изменения с прошлой проверки"""

    nmid: int
    timestamp: datetime
    date: datetime
    orders_delta: int
    orders_sum_delta: float
    open_card_delta: int
    add_to_cart_delta: int
    buy_outs_delta: int
    total_orders: int
    total_orders_sum: float
    total_open_card: int
    total_add_to_cart: int
    total_buy_outs: int
    version: int
    update_source: str = "wb_api"


class IncrementalCommonStatManager(BaseIncrementalManager):
    """Управление инкрементальной статистикой карточек товаров"""

    table_name = "default_db.wb_common_stat_incremental"
    key_field = "nmid"

    async def save_incremental_stats(
        self, statistics: list[CommonStat]
    ) -> list[IncrementalCommonStat]:
        """
        Сохраняет инкрементальные изменения в ClickHouse.

        Алгоритм:
        1. Группирует статистику по (nmid, date)
        2. Для каждой пары получает предыдущее значение из wb_common_stat
        3. Вычисляет дельту (current - previous)
        4. Контролирует отрицательные дельты (WB откатывает)
        5. Сохраняет батчем только если есть изменения

        Args:
            statistics: Список статистики от WB API (кумулятивные значения за день)

        Returns:
            Список сохраненных инкрементальных записей
        """
        if not statistics:
            return []

        incremental_stats = []
        current_timestamp = datetime.now()
        version = int(time.time() * 1000)  # Миллисекунды для уникальности

        # Группируем по (nmid, date)
        stats_by_key: dict[tuple[int, datetime], CommonStat] = {}
        for stat in statistics:
            key = (stat.nmid, stat.date)
            stats_by_key[key] = stat

        # Получаем предыдущие значения одним запросом
        previous_stats = await self._get_previous_totals(
            [stat.nmid for stat in statistics],
            [stat.date for stat in statistics],
        )

        # Вычисляем дельты
        for (nmid, date), current_stat in stats_by_key.items():
            previous = previous_stats.get((nmid, date))

            # Первая запись для карточки
            if previous is None:
                logger.info(f"Первая запись для nmid={nmid}, инициализируем baseline")

            # Вычисляем изменения с защитой от отрицательных значений
            # WB иногда корректирует статистику (отмены заказов, пересчёты)
            orders_delta = max(
                0, current_stat.orders - (previous.orders if previous else 0)
            )
            orders_sum_delta = max(
                0, current_stat.orders_sum - (previous.orders_sum if previous else 0)
            )
            open_card_delta = max(
                0, current_stat.open_card - (previous.open_card if previous else 0)
            )
            add_to_cart_delta = max(
                0,
                current_stat.add_to_cart - (previous.add_to_cart if previous else 0),
            )
            buy_outs_delta = max(
                0, current_stat.buy_outs - (previous.buy_outs if previous else 0)
            )

            # Проверяем были ли отрицательные дельты (для мониторинга)
            if previous:
                raw_orders_delta = current_stat.orders - previous.orders
                raw_sum_delta = current_stat.orders_sum - previous.orders_sum
                if raw_orders_delta < 0 or raw_sum_delta < 0:
                    logger.warning(
                        f"⚠️ WB откатил статистику для nmid={nmid} date={date}: "
                        f"orders: {previous.orders} → {current_stat.orders} (delta={raw_orders_delta}), "
                        f"sum: {previous.orders_sum:.2f} → {current_stat.orders_sum:.2f} (delta={raw_sum_delta:.2f})"
                    )

            # Сохраняем только если есть изменения
            if any(
                [
                    orders_delta != 0,
                    orders_sum_delta != 0,
                    open_card_delta != 0,
                    add_to_cart_delta != 0,
                    buy_outs_delta != 0,
                ]
            ):
                incremental = IncrementalCommonStat(
                    nmid=nmid,
                    timestamp=current_timestamp,  # Момент фиксации данных WB (WB не отдаёт время события)
                    date=date if isinstance(date, datetime) else datetime.combine(date, datetime.min.time()),
                    orders_delta=orders_delta,
                    orders_sum_delta=orders_sum_delta,
                    open_card_delta=open_card_delta,
                    add_to_cart_delta=add_to_cart_delta,
                    buy_outs_delta=buy_outs_delta,
                    total_orders=current_stat.orders,
                    total_orders_sum=current_stat.orders_sum,
                    total_open_card=current_stat.open_card,
                    total_add_to_cart=current_stat.add_to_cart,
                    total_buy_outs=current_stat.buy_outs,
                    version=version,
                )
                incremental_stats.append(incremental)

        # Батчевая вставка в ClickHouse (оптимизация производительности)
        if incremental_stats:
            await self._insert_incremental(incremental_stats)
            logger.info(
                f"Сохранено {len(incremental_stats)} инкрементальных записей (общая статистика)"
            )

        return incremental_stats

    async def _get_previous_totals(
        self, nmids: list[int], dates: list[datetime]
    ) -> dict[tuple[int, datetime], CommonStat]:
        """
        Получает предыдущие значения из основной таблицы wb_common_stat.

        Используем argMax(value, version) для получения последней версии.
        Защита от AttributeError при первой загрузке карточки.
        """
        if not nmids or not dates:
            return {}

        # Уникальные nmids и dates
        unique_nmids = list(set(nmids))
        unique_dates = list(
            set(d.date() if isinstance(d, datetime) else d for d in dates)
        )

        query = """
        SELECT 
            nmid,
            date,
            argMax(orders, version) as orders,
            argMax(orders_sum, version) as orders_sum,
            argMax(open_card, version) as open_card,
            argMax(add_to_cart, version) as add_to_cart,
            argMax(buy_outs, version) as buy_outs
        FROM default_db.wb_common_stat
        WHERE nmid IN %(nmids)s
          AND date IN %(dates)s
        GROUP BY nmid, date
        """

        try:
            async with get_clickhouse_client() as client:
                result = await client.query(
                    query,
                    parameters={
                        "nmids": unique_nmids,
                        "dates": [d.strftime("%Y-%m-%d") for d in unique_dates],
                    },
                )

                previous_stats = {}
                for row in result.result_rows:
                    nmid = row[0]
                    date = row[1]
                    stat = CommonStat(
                        nmid=nmid,
                        date=date,
                        open_card=row[4],
                        add_to_cart=row[5],
                        orders=row[2],
                        orders_sum=row[3],
                        buy_outs=row[6],
                    )
                    previous_stats[(nmid, date)] = stat

                return previous_stats
        except Exception as exc:
            logger.error(
                f"Ошибка получения предыдущих значений из wb_common_stat: {exc}",
                exc_info=True,
            )
            return {}

    async def _insert_incremental(
        self, incremental_stats: list[IncrementalCommonStat]
    ) -> None:
        """
        Батчевая вставка в ClickHouse.
        
        При массовой записи (100+ записей) это ускоряет запись в 5-10 раз
        и снимает нагрузку с ClickHouse при частых апдейтах.
        """
        if not incremental_stats:
            return

        # Подготавливаем данные для батчевой вставки
        data = []
        for stat in incremental_stats:
            data.append(
                {
                    "nmid": stat.nmid,
                    "timestamp": stat.timestamp,
                    "date": stat.date,
                    "orders_delta": stat.orders_delta,
                    "orders_sum_delta": stat.orders_sum_delta,
                    "open_card_delta": stat.open_card_delta,
                    "add_to_cart_delta": stat.add_to_cart_delta,
                    "buy_outs_delta": stat.buy_outs_delta,
                    "total_orders": stat.total_orders,
                    "total_orders_sum": stat.total_orders_sum,
                    "total_open_card": stat.total_open_card,
                    "total_add_to_cart": stat.total_add_to_cart,
                    "total_buy_outs": stat.total_buy_outs,
                    "version": stat.version,
                    "update_source": stat.update_source,
                }
            )

        # Батчевая вставка (ClickHouse оптимизирован для этого)
        async with get_clickhouse_client() as client:
            await client.insert(
                "default_db.wb_common_stat_incremental",
                data,
                column_names=[
                    "nmid",
                    "timestamp",
                    "date",
                    "orders_delta",
                    "orders_sum_delta",
                    "open_card_delta",
                    "add_to_cart_delta",
                    "buy_outs_delta",
                    "total_orders",
                    "total_orders_sum",
                    "total_open_card",
                    "total_add_to_cart",
                    "total_buy_outs",
                    "version",
                    "update_source",
                ],
            )


@dataclass
class IncrementalAdvStat:
    """Инкрементальная статистика рекламы - изменения с прошлой проверки"""

    adv_id: int
    timestamp: datetime
    date: datetime
    orders_delta: int
    spend_delta: float
    sum_price_delta: float
    views_delta: int
    clicks_delta: int
    added_to_cart_delta: int
    total_orders: int
    total_spend: float
    total_sum_price: float
    total_views: int
    total_clicks: int
    total_added_to_cart: int
    version: float


class IncrementalAdvStatManager(BaseIncrementalManager):
    """Управление инкрементальной статистикой рекламных кампаний"""

    table_name = "default_db.full_adv_wb_stat_incremental"
    key_field = "adv_id"

    async def save_incremental_stats(
        self, full_stats: list[FullAdvStat]
    ) -> list[IncrementalAdvStat]:
        """
        Сохраняет инкрементальные изменения рекламной статистики.

        Args:
            full_stats: Список полной статистики рекламы от WB API

        Returns:
            Список сохраненных инкрементальных записей
        """
        if not full_stats:
            return []

        incremental_stats = []
        current_timestamp = datetime.now()
        version = time.time()

        for full_stat in full_stats:
            adv_id = full_stat.advertId

            # Обрабатываем каждый день из статистики
            for day_stat in full_stat.days:
                date = (
                    day_stat.date.date()
                    if hasattr(day_stat.date, "date")
                    else day_stat.date
                )

                # Получаем предыдущие значения
                previous = await self._get_previous_total(adv_id, date)

                # Первая запись
                if previous is None:
                    logger.info(f"Первая запись для adv_id={adv_id}, date={date}")

                # Вычисляем дельты с защитой от отрицательных значений
                orders_delta = max(
                    0, day_stat.orders - (previous["orders"] if previous else 0)
                )
                spend_delta = max(
                    0, day_stat.sum - (previous["spend"] if previous else 0)
                )
                sum_price_delta = max(
                    0, day_stat.sum_price - (previous["sum_price"] if previous else 0)
                )
                views_delta = max(
                    0, day_stat.views - (previous["views"] if previous else 0)
                )
                clicks_delta = max(
                    0, day_stat.clicks - (previous["clicks"] if previous else 0)
                )
                added_to_cart_delta = max(
                    0, day_stat.atbs - (previous["added_to_cart"] if previous else 0)
                )

                # Проверяем отрицательные дельты для мониторинга
                if previous:
                    raw_orders_delta = day_stat.orders - previous["orders"]
                    raw_spend_delta = day_stat.sum - previous["spend"]
                    if raw_orders_delta < 0 or raw_spend_delta < 0:
                        logger.warning(
                            f"⚠️ WB откатил статистику рекламы adv_id={adv_id} date={date}: "
                            f"orders delta={raw_orders_delta}, spend delta={raw_spend_delta:.2f}"
                        )

                # Сохраняем только если есть изменения
                if any(
                    [
                        orders_delta != 0,
                        spend_delta != 0,
                        sum_price_delta != 0,
                        views_delta != 0,
                        clicks_delta != 0,
                        added_to_cart_delta != 0,
                    ]
                ):
                    incremental = IncrementalAdvStat(
                        adv_id=adv_id,
                        timestamp=current_timestamp,  # Момент фиксации данных WB
                        date=date if isinstance(date, datetime) else datetime.combine(date, datetime.min.time()),
                        orders_delta=orders_delta,
                        spend_delta=spend_delta,
                        sum_price_delta=sum_price_delta,
                        views_delta=views_delta,
                        clicks_delta=clicks_delta,
                        added_to_cart_delta=added_to_cart_delta,
                        total_orders=day_stat.orders,
                        total_spend=day_stat.sum,
                        total_sum_price=day_stat.sum_price,
                        total_views=day_stat.views,
                        total_clicks=day_stat.clicks,
                        total_added_to_cart=day_stat.atbs,
                        version=version,
                    )
                    incremental_stats.append(incremental)

        # Батчевая вставка
        if incremental_stats:
            await self._insert_incremental(incremental_stats)
            logger.info(
                f"Сохранено {len(incremental_stats)} инкрементальных записей (реклама)"
            )

        return incremental_stats

    async def _get_previous_total(
        self, adv_id: int, date: datetime
    ) -> dict[str, float] | None:
        """
        Получает предыдущие значения из full_adv_wb_stat.
        Возвращает None при первой загрузке.
        """
        query = """
        SELECT 
            argMax(orders, version) as orders,
            argMax(spend, version) as spend,
            argMax(sum_price_orders, version) as sum_price,
            argMax(views, version) as views,
            argMax(clicks, version) as clicks,
            argMax(added_to_cart, version) as added_to_cart
        FROM default_db.full_adv_wb_stat
        WHERE adv_id = %(adv_id)s
          AND date = %(date)s
        GROUP BY adv_id, date
        """

        try:
            async with get_clickhouse_client() as client:
                result = await client.query(
                    query,
                    parameters={"adv_id": adv_id, "date": date.strftime("%Y-%m-%d")},
                )
                if result.first_item:
                    return {
                        "orders": result.first_item["orders"] or 0,
                        "spend": result.first_item["spend"] or 0,
                        "sum_price": result.first_item["sum_price"] or 0,
                        "views": result.first_item["views"] or 0,
                        "clicks": result.first_item["clicks"] or 0,
                        "added_to_cart": result.first_item["added_to_cart"] or 0,
                    }
                return None
        except Exception as exc:
            logger.error(f"Ошибка получения предыдущих значений рекламы: {exc}")
            return None

    async def _get_previous_totals(
        self, keys: list, dates: list
    ) -> dict:
        """Заглушка для соответствия ABC"""
        return {}

    async def _insert_incremental(
        self, incremental_stats: list[IncrementalAdvStat]
    ) -> None:
        """Батчевая вставка инкрементальных записей рекламы"""
        if not incremental_stats:
            return

        data = []
        for stat in incremental_stats:
            data.append(
                {
                    "adv_id": stat.adv_id,
                    "timestamp": stat.timestamp,
                    "date": stat.date,
                    "orders_delta": stat.orders_delta,
                    "spend_delta": stat.spend_delta,
                    "sum_price_delta": stat.sum_price_delta,
                    "views_delta": stat.views_delta,
                    "clicks_delta": stat.clicks_delta,
                    "added_to_cart_delta": stat.added_to_cart_delta,
                    "total_orders": stat.total_orders,
                    "total_spend": stat.total_spend,
                    "total_sum_price": stat.total_sum_price,
                    "total_views": stat.total_views,
                    "total_clicks": stat.total_clicks,
                    "total_added_to_cart": stat.total_added_to_cart,
                    "version": stat.version,
                }
            )

        async with get_clickhouse_client() as client:
            await client.insert(
                "default_db.full_adv_wb_stat_incremental",
                data,
                column_names=[
                    "adv_id",
                    "timestamp",
                    "date",
                    "orders_delta",
                    "spend_delta",
                    "sum_price_delta",
                    "views_delta",
                    "clicks_delta",
                    "added_to_cart_delta",
                    "total_orders",
                    "total_spend",
                    "total_sum_price",
                    "total_views",
                    "total_clicks",
                    "total_added_to_cart",
                    "version",
                ],
            )


