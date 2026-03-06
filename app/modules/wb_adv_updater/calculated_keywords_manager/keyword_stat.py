"""Сырые метрики кластера из запроса (get_clusters_stats.sql).

CPM приходит из того же запроса (last_cpm из mv_clusters_last_state) и передаётся
в каскад как шаг «stats»: set_bid → bid_log → stats. Без него рейтинг ключей
и orders_per_1000_rub не считаются (каскад даёт 0), ломаются whitelist и тесты.
orders_per_1000_rub считается выше по стеку в PreCalculatedKeyword/CalculatedKeyword.
"""
from datetime import datetime

from pydantic import BaseModel, Field

# Фиксированная дата для нулевой статистики (ключи без данных в CH)
_ZERO_STAT_TIMESTAMP = datetime.min


class KeywordStat(BaseModel):
    """Статистика по ключу из ClickHouse: показы, клики, spend, conv_views_to_orders, cpm.

    cpm — последний CPM по ключу из CH; используется как третий шаг каскада CPM
    (шаг «stats») для расчёта рейтинга и orders_per_1000_rub.
    """

    text: str = Field(alias="norm_query")
    position: float = Field(alias="position")
    timestamp: datetime = Field(alias="timestamp")
    views: int = Field(alias="views")
    clicks: int = Field(alias="clicks")
    add_to_cart: int = Field(alias="add_to_cart")
    orders: int = Field(alias="orders")
    spend: float = Field(alias="spend")
    cpm: float = Field(alias="cpm")
    base_cart_to_order_conv: float = Field(alias="base_cart_to_order_conv")
    expected_orders_from_cart: float = Field(alias="expected_orders_from_cart")
    expected_orders: float = Field(alias="expected_orders")
    conv_views_to_orders: float = Field(alias="conversion_without_cpm")
    total_views: int = Field(alias="views_all_time")
    total_orders: int = Field(alias="orders_all_time")

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }

    @property
    def ctr(self) -> float:
        if self.views > 0:
            return self.clicks / self.views
        else:
            return 0.0


def make_zero_keyword_stat(text: str) -> KeywordStat:
    """Фабрика нулевой статистики для ключа без данных в ClickHouse (новые фразы в БС/релевантные)."""
    return KeywordStat.model_construct(
        text=text,
        position=0.0,
        timestamp=_ZERO_STAT_TIMESTAMP,
        views=0,
        clicks=0,
        add_to_cart=0,
        orders=0,
        spend=0.0,
        cpm=0.0,
        base_cart_to_order_conv=0.0,
        expected_orders_from_cart=0.0,
        expected_orders=0.0,
        conv_views_to_orders=0.0,
        total_views=0,
        total_orders=0,
    )
