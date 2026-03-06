"""Legacy path: GET /adv/v3/fullstats via aiohttp for code that does not use WBManagerHub (e.g. scripts)."""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import Any

from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
    FullStatsItem,
)
from app.modules.full_stat_adv_updater.types.full_adv_stat import FullAdvStat

logger = logging.getLogger(__name__)

BASE_URL = "https://advert-api.wildberries.ru"
MAX_IDS_PER_REQUEST = 50
MAX_DAYS_PER_REQUEST = 31


async def fetch_fullstats_v3(
    session: Any,
    headers: dict[str, str],
    adv_ids: list[int],
    begin_date: date,
    end_date: date,
) -> list[FullAdvStat]:
    """
    Fetch fullstats via GET /adv/v3/fullstats (chunks of 50 ids, 31-day windows).
    Uses aiohttp session; for hub-based code use hub.wb_data_manager.get_full_adv_stat instead.
    """
    from app.core.mp.wb.api.adapter.promotion_client.fullstats.mapper import (
        full_stats_item_to_full_adv_stat,
    )
    from app.core.mp.wb.api.adapter.promotion_client.fullstats.adapter import (
        _merge_full_adv_stat,
    )

    if not adv_ids:
        return []

    total_days = (end_date - begin_date).days + 1
    if total_days <= MAX_DAYS_PER_REQUEST:
        return await _fetch_single_range(
            session, headers, adv_ids, begin_date, end_date,
            full_stats_item_to_full_adv_stat,
        )

    windows: list[tuple[date, date]] = []
    w_begin = begin_date
    while w_begin <= end_date:
        w_end = min(w_begin + timedelta(days=MAX_DAYS_PER_REQUEST - 1), end_date)
        windows.append((w_begin, w_end))
        w_begin = w_end + timedelta(days=1)

    merged_by_id: dict[int, FullAdvStat] = {}
    for w_begin, w_end in windows:
        chunk_stats = await _fetch_single_range(
            session, headers, adv_ids, w_begin, w_end,
            full_stats_item_to_full_adv_stat,
        )
        for stat in chunk_stats:
            aid = stat.advertId
            if aid not in merged_by_id:
                merged_by_id[aid] = stat
            else:
                merged_by_id[aid] = _merge_full_adv_stat(merged_by_id[aid], stat)

    return list(merged_by_id.values())


async def _fetch_single_range(
    session: Any,
    headers: dict[str, str],
    adv_ids: list[int],
    begin_date: date,
    end_date: date,
    mapper: Any,
) -> list[FullAdvStat]:
    result: list[FullAdvStat] = []
    for i in range(0, len(adv_ids), MAX_IDS_PER_REQUEST):
        chunk = adv_ids[i : i + MAX_IDS_PER_REQUEST]
        ids_str = ",".join(str(aid) for aid in chunk)
        url = (
            f"{BASE_URL}/adv/v3/fullstats"
            f"?ids={ids_str}&beginDate={begin_date.isoformat()}&endDate={end_date.isoformat()}"
        )
        async with session.get(url, headers=headers) as response:
            response.raise_for_status()
            text = await response.text()
        raw = json.loads(text) if text else []
        if not isinstance(raw, list):
            continue
        for d in raw:
            if not isinstance(d, dict):
                continue
            try:
                item = FullStatsItem.from_dict(d)
                result.append(mapper(item, begin_date, end_date))
            except Exception as e:
                logger.warning("Skip fullstats item: %s", e)
    return result
