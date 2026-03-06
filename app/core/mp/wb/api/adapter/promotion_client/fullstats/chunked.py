"""Shared chunking, rate-limit sleep, and 429-retry orchestration for fullstats v3.

Used by both the generated-client adapter and the legacy aiohttp path so behavior
and constants stay in one place.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import date
from typing import TypeVar

from app.core.mp.wb.api.excs import TooManyRequests

logger = logging.getLogger(__name__)

T = TypeVar("T")

MAX_IDS_PER_REQUEST = 50
# v3 fullstats: 3 requests/minute, 20s between requests
FULLSTATS_V3_RATE_LIMIT_INTERVAL_SEC = 20
FULLSTATS_V3_MAX_CHUNK_RETRIES = 10


async def run_chunked_single_range(
    adv_ids: list[int],
    begin_date: date,
    end_date: date,
    fetcher: Callable[[list[int], date, date], Awaitable[list[T]]],
    *,
    rate_limit_interval_sec: float = FULLSTATS_V3_RATE_LIMIT_INTERVAL_SEC,
    max_retries: int = FULLSTATS_V3_MAX_CHUNK_RETRIES,
) -> list[T]:
    """
    Run fullstats for one date range with chunking by 50 ids, inter-chunk sleep,
    and per-chunk 429 retry with backoff.

    fetcher(chunk_ids, begin_date, end_date) must return the list of results for
    that chunk, or raise TooManyRequests(next_pause) on 429.
    """
    result: list[T] = []
    for i in range(0, len(adv_ids), MAX_IDS_PER_REQUEST):
        if i > 0:
            await asyncio.sleep(rate_limit_interval_sec)
        chunk = adv_ids[i : i + MAX_IDS_PER_REQUEST]
        for attempt in range(max_retries):
            try:
                items = await fetcher(chunk, begin_date, end_date)
                result.extend(items)
                break
            except TooManyRequests as e:
                wait = e.next_pause if e.next_pause is not None else rate_limit_interval_sec
                if attempt + 1 >= max_retries:
                    raise
                logger.warning(
                    "fullstats v3 chunk 429, waiting %ss (attempt %s/%s)",
                    wait,
                    attempt + 1,
                    max_retries,
                )
                await asyncio.sleep(wait)
    return result
