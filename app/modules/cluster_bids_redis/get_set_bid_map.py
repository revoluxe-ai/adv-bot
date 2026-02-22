"""Async function to fetch set bid map from Redis for cluster bids."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from app.modules.cluster_bids_redis.redis_cluster_bids_timestamp_manager import (
    AdvProtocol,
)

if TYPE_CHECKING:
    from app.core.redis_manager_v2.redis_client import RedisClient


async def get_set_bid_map(
    search_adv_id: int | None,
    nmids: list[int],
    texts: list[str],
    adv_for_timestamp: AdvProtocol,
    redis_client: RedisClient,
) -> dict[str, tuple[float, datetime | None]]:
    """
    Fetch set bid (cpm, date) per text from Redis cluster bids storage.

    Returns empty dict if texts/nmids empty or search_adv_id is None.
    """
    if search_adv_id is None or not nmids or not texts:
        return {}

    from app.modules.cluster_bids_redis import (
        ClusterBidKey,
        RedisClusterBidsManager,
        RedisClusterBidsTimestampManager,
    )

    keys = [
        ClusterBidKey(adv_id=search_adv_id, nmid=nmid, cluster=text)
        for nmid in nmids
        for text in texts
    ]
    manager = RedisClusterBidsManager(redis_client=redis_client)
    bids = await manager.get_bids(keys)
    ts_manager = RedisClusterBidsTimestampManager(redis_client=redis_client)
    set_bid_date = await ts_manager.get(adv_for_timestamp)

    set_bid_map: dict[str, tuple[float, datetime | None]] = {}
    for text in texts:
        for nmid in nmids:
            k = ClusterBidKey(adv_id=search_adv_id, nmid=nmid, cluster=text)
            if k in bids:
                set_bid_map[text] = (float(bids[k]), set_bid_date)
                break

    return set_bid_map
