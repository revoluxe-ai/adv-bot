"""ClickHouse manager for fetching latest keyword bids from bid_decision_log."""

from __future__ import annotations

from datetime import datetime

from app.core.clickhouse_manager.base_clickhouse_manager import BaseClickHouseManager
from app.utils.click_house.client import get_clickhouse_client
from app.utils.ch_semaphore import anti_ch_crash_semaphore


class KeywordBidFromLogClickHouseManager(BaseClickHouseManager):
    """Fetches latest cpm_curr and decision_time per norm_query from bid_decision_log."""

    async def get_latest_keyword_bids(
        self,
        adv_id: int,
        nmids: list[int],
        norm_queries: list[str],
    ) -> dict[str, tuple[float, datetime]]:
        """
        Return one row per norm_query: (cpm_curr, decision_time) by latest version.

        Empty norm_queries → empty dict. Keys are norm_query strings.
        """
        if not norm_queries:
            return {}
        query = self._get_query("get_latest_keyword_bids")
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                response = await client.query(
                    query,
                    parameters={
                        "adv_id": adv_id,
                        "nmids": nmids,
                        "norm_queries": norm_queries,
                    },
                )
        result: dict[str, tuple[float, datetime]] = {}
        for row in response.named_results():
            norm_query = row["norm_query"]
            cpm_curr = row.get("cpm_curr")
            decision_time = row.get("decision_time")
            if cpm_curr is not None and decision_time is not None:
                result[norm_query] = (float(cpm_curr), decision_time)
        return result
