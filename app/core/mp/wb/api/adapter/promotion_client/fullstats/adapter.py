"""Adapter for GET /adv/v3/fullstats (campaign statistics)."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import date, timedelta
from typing import Any, cast

from app.core.mp.wb.api.adapter.promotion_client.base_section_adapter import (
    BaseSectionAdapter,
)
from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.api.statistics.get_adv_v3_fullstats import (
    asyncio_detailed as get_adv_v3_fullstats_async,
)
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
    FullStatsItem,
)
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.types import (
    Response,
)
from app.modules.full_stat_adv_updater.types.full_adv_stat import (
    DayStats,
    FullAdvStat,
    compute_aggregate_ctr_cpc_cr,
)

from .chunked import run_chunked_single_range
from .mapper import full_stats_item_to_full_adv_stat

logger = logging.getLogger(__name__)

MAX_DAYS_PER_REQUEST = 31

SingleRangeFetcher = Callable[
    [list[int], date, date], Awaitable[list[FullAdvStat]]
]


async def fetch_fullstats_with_windowing(
    adv_ids: list[int],
    begin_date: date,
    end_date: date,
    single_range_fetcher: SingleRangeFetcher,
) -> list[FullAdvStat]:
    """
    Fetch fullstats with 31-day windowing and merge-by-advertId.
    single_range_fetcher(adv_ids, begin_date, end_date) must return stats for one
    date range (caller is responsible for 50-id chunking inside the fetcher).
    """
    if not adv_ids:
        return []

    total_days = (end_date - begin_date).days + 1
    if total_days <= MAX_DAYS_PER_REQUEST:
        return await single_range_fetcher(adv_ids, begin_date, end_date)

    windows: list[tuple[date, date]] = []
    w_begin = begin_date
    while w_begin <= end_date:
        w_end = min(w_begin + timedelta(days=MAX_DAYS_PER_REQUEST - 1), end_date)
        windows.append((w_begin, w_end))
        w_begin = w_end + timedelta(days=1)

    merged_by_id: dict[int, FullAdvStat] = {}
    for w_begin, w_end in windows:
        chunk_stats = await single_range_fetcher(adv_ids, w_begin, w_end)
        for stat in chunk_stats:
            aid = stat.advertId
            if aid not in merged_by_id:
                merged_by_id[aid] = stat
            else:
                merged_by_id[aid] = _merge_full_adv_stat(merged_by_id[aid], stat)

    return list(merged_by_id.values())


class FullstatsAdapter(BaseSectionAdapter):
    """Adapter for campaign full statistics (v3 API)."""

    async def get_full_adv_stat(
        self,
        adv_ids: list[int],
        begin_date: date,
        end_date: date,
    ) -> list[FullAdvStat]:
        """Fetch full stats for campaigns; chunks by 50 ids and 31-day windows."""
        return await fetch_fullstats_with_windowing(
            adv_ids, begin_date, end_date, self._get_full_adv_stat_single_range
        )

    async def _get_full_adv_stat_single_range(
        self,
        adv_ids: list[int],
        begin_date: date,
        end_date: date,
    ) -> list[FullAdvStat]:
        """One date range (<= 31 days); chunk adv_ids by 50. Rate-limited and per-chunk retry on 429."""

        async def fetcher(
            chunk: list[int], b: date, e: date
        ) -> list[FullAdvStat]:
            items = await self._request_chunk(chunk, b, e)
            from app.modules.attribution_facts.ingest.seam import (
                maybe_ingest_fullstats_chunk,
            )

            await maybe_ingest_fullstats_chunk(list(items))
            return [
                full_stats_item_to_full_adv_stat(item, b, e) for item in items
            ]

        return await run_chunked_single_range(
            adv_ids, begin_date, end_date, fetcher
        )

    async def _request_chunk(
        self,
        adv_ids: list[int],
        begin_date: date,
        end_date: date,
    ) -> list[FullStatsItem]:
        """Single API call: one chunk of ids, one date range."""
        client = await self.auth_client_handler.get_proxy_client(self)
        ids_str = ",".join(str(aid) for aid in adv_ids)
        response: Response[
            Any
        ] = await with_raise_errors(
            get_adv_v3_fullstats_async,
            client,
            ids=ids_str,
            begin_date=begin_date,
            end_date=end_date,
        )
        parsed = response.parsed
        if parsed is None or not isinstance(parsed, list):
            return []
        parsed_list: list[Any] = cast(list[Any], parsed)
        return [x for x in parsed_list if isinstance(x, FullStatsItem)]


def _merge_full_adv_stat(a: FullAdvStat, b: FullAdvStat) -> FullAdvStat:
    """Merge two FullAdvStat for the same advertId (e.g. from two 31-day windows)."""
    assert a.advertId == b.advertId
    dates = list(dict.fromkeys(a.dates + b.dates))
    dates.sort()
    days: list[DayStats] = list(a.days) + list(b.days)
    days.sort(key=lambda d: d.date)

    views = a.views + b.views
    clicks = a.clicks + b.clicks
    sum_ = a.sum + b.sum
    atbs = a.atbs + b.atbs
    orders = a.orders + b.orders
    shks = a.shks + b.shks
    sum_price = a.sum_price + b.sum_price

    ctr, cpc, cr = compute_aggregate_ctr_cpc_cr(views, clicks, sum_, orders)

    booster_stats = (a.boosterStats or []) + (b.boosterStats or [])
    booster_stats = booster_stats if booster_stats else None

    return FullAdvStat(
        dates=dates,
        views=views,
        clicks=clicks,
        ctr=ctr,
        cpc=cpc,
        sum=sum_,
        atbs=atbs,
        orders=orders,
        cr=cr,
        shks=shks,
        sum_price=sum_price,
        days=days,
        boosterStats=booster_stats,
        advertId=a.advertId,
    )
