"""Legacy path: GET /adv/v3/fullstats via aiohttp for code that does not use WBManagerHub (e.g. scripts)."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date
from typing import Any

from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
    FullStatsItem,
)
from app.modules.full_stat_adv_updater.types.full_adv_stat import FullAdvStat

logger = logging.getLogger(__name__)

BASE_URL = "https://advert-api.wildberries.ru"
MAX_IDS_PER_REQUEST = 50
# v3 fullstats: 3 requests/minute, 20s between requests
FULLSTATS_V3_RATE_LIMIT_INTERVAL_SEC = 20
FULLSTATS_V3_MAX_CHUNK_RETRIES = 10


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
    from app.core.mp.wb.api.adapter.promotion_client.fullstats.adapter import (
        fetch_fullstats_with_windowing,
    )
    from app.core.mp.wb.api.adapter.promotion_client.fullstats.mapper import (
        full_stats_item_to_full_adv_stat,
    )

    async def single_range_fetcher(
        ids: list[int], b: date, e: date
    ) -> list[FullAdvStat]:
        return await _fetch_single_range(
            session, headers, ids, b, e, full_stats_item_to_full_adv_stat
        )

    return await fetch_fullstats_with_windowing(
        adv_ids, begin_date, end_date, single_range_fetcher
    )


def _parse_429_retry_seconds(response: Any) -> int:
    """Parse x-ratelimit-retry from response headers; default 20s."""
    try:
        headers = getattr(response, "headers", None)
        if not headers:
            return FULLSTATS_V3_RATE_LIMIT_INTERVAL_SEC
        for key, value in headers.items():
            if key.lower() == "x-ratelimit-retry":
                try:
                    return int(value)
                except ValueError:
                    return FULLSTATS_V3_RATE_LIMIT_INTERVAL_SEC
    except Exception:
        pass
    return FULLSTATS_V3_RATE_LIMIT_INTERVAL_SEC


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
        if i > 0:
            await asyncio.sleep(FULLSTATS_V3_RATE_LIMIT_INTERVAL_SEC)
        chunk = adv_ids[i : i + MAX_IDS_PER_REQUEST]
        ids_str = ",".join(str(aid) for aid in chunk)
        url = (
            f"{BASE_URL}/adv/v3/fullstats"
            f"?ids={ids_str}&beginDate={begin_date.isoformat()}&endDate={end_date.isoformat()}"
        )
        for attempt in range(FULLSTATS_V3_MAX_CHUNK_RETRIES):
            async with session.get(url, headers=headers) as response:
                if response.status == 429:
                    await response.read()  # consume body so connection can be reused
                    if attempt + 1 >= FULLSTATS_V3_MAX_CHUNK_RETRIES:
                        response.raise_for_status()
                    wait = _parse_429_retry_seconds(response)
                    logger.warning(
                        "fullstats v3 chunk 429, waiting %ss (attempt %s/%s)",
                        wait,
                        attempt + 1,
                        FULLSTATS_V3_MAX_CHUNK_RETRIES,
                    )
                    await asyncio.sleep(wait)
                    continue
                response.raise_for_status()
                text = await response.text()
            raw = json.loads(text) if text else []
            if not isinstance(raw, list):
                raw = []
            for d in raw:
                if not isinstance(d, dict):
                    continue
                try:
                    item = FullStatsItem.from_dict(d)
                    result.append(mapper(item, begin_date, end_date))
                except Exception as e:
                    logger.warning("Skip fullstats item: %s", e)
            break
    return result
