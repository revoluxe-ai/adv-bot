"""Module for reading keyword bids from bid_decision_log (ClickHouse)."""

from __future__ import annotations

from datetime import datetime

from app.modules.keyword_bid_from_log.clickhouse_manager import (
    KeywordBidFromLogClickHouseManager,
)

__all__ = [
    "KeywordBidFromLogClickHouseManager",
    "get_latest_keyword_bids",
]

_manager: KeywordBidFromLogClickHouseManager | None = None


async def get_latest_keyword_bids(
    adv_id: int,
    nmids: list[int],
    norm_queries: list[str],
) -> dict[str, tuple[float, datetime]]:
    """
    Return latest (cpm_curr, decision_time) per norm_query from bid_decision_log.

    Uses default_db.bid_decision_log, one row per norm_query (max version).
    Empty norm_queries → empty dict.
    """
    global _manager
    if _manager is None:
        _manager = KeywordBidFromLogClickHouseManager()
    return await _manager.get_latest_keyword_bids(adv_id, nmids, norm_queries)
