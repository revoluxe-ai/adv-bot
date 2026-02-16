from __future__ import annotations

from datetime import date, datetime
from typing import Sequence

import factory
from faker import Faker

from app.modules.shop_runner.service_manager.services.clusters_adv_stat_updater.row_stat_dto import (
    RowStatDTO,
)

fake = Faker("ru_RU")


class ClustersAdvStatsDTO(RowStatDTO):
    timestamp: datetime


class ClustersAdvStatsFactory(factory.Factory):
    """
    Factory for generating ClickHouse rows compatible with clusters_adv_stats table.
    """

    class Meta:
        model = ClustersAdvStatsDTO

    adv_id = factory.Sequence(lambda n: 10_000 + n)
    nmid = factory.Sequence(lambda n: 100_000 + n)
    wb_category = factory.LazyFunction(lambda: fake.word())
    norm_query = factory.LazyFunction(lambda: fake.unique.word())
    views = 120
    clicks = 30
    ctr = factory.LazyAttribute(lambda obj: round(obj.clicks / obj.views, 4))
    cpm = 90.0
    add_to_cart = 5
    orders = 3
    cpc = 12.0
    avr_pos = 2.0
    date = factory.LazyFunction(date.today)
    timestamp = factory.LazyFunction(datetime.utcnow)
    spend = factory.LazyFunction(lambda: 0.0)


CLUSTERS_ADV_STATS_COLUMNS = [
    "adv_id",
    "nmid",
    "wb_category",
    "norm_query",
    "views",
    "clicks",
    "ctr",
    "cpm",
    "add_to_cart",
    "orders",
    "cpc",
    "avr_pos",
    "date",
    "spend",
    "timestamp",
]


def build_clusters_adv_stats_rows(
    records: Sequence[ClustersAdvStatsDTO],
) -> list[list[object]]:
    """
    Converts DTO instances into a ClickHouse insert payload.
    """

    rows: list[list[object]] = []
    for record in records:
        rows.append(
            [
                record.adv_id,
                record.nmid,
                record.wb_category,
                record.norm_query,
                record.views,
                record.clicks,
                record.ctr,
                record.cpm,
                record.add_to_cart,
                record.orders,
                record.cpc,
                record.avr_pos,
                record.date,
                record.spend,
                record.timestamp,
            ]
        )
    return rows


__all__ = [
    "ClustersAdvStatsDTO",
    "ClustersAdvStatsFactory",
    "CLUSTERS_ADV_STATS_COLUMNS",
    "build_clusters_adv_stats_rows",
]
