"""ClickHouse manager for fetching bids per position from bid_decision_log."""

from __future__ import annotations

from collections import defaultdict

from app.core.clickhouse_manager.base_clickhouse_manager import BaseClickHouseManager
from app.modules.bids_for_positions_manager.dto import BidPositionRow
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.client import get_clickhouse_client


class BidsForPositionsClickHouseManager(BaseClickHouseManager):
    """Fetches raw bid positions (norm_query, position, bid, timestamp) per nmid."""

    async def get_bids_for_positions(
        self, nmid: int
    ) -> dict[str, list[BidPositionRow]]:
        query = self._get_query("get_bids_for_positions")
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                result = await client.query(query, parameters={"nmid": nmid})
                column_names = result.column_names
                results: dict[str, list[BidPositionRow]] = defaultdict(list)
                rows = list(result.result_rows)
                for row in rows:
                    row_dict = dict(zip(column_names, row))
                    keyword = row_dict["norm_query"]
                    position = row_dict["pos_bin"]
                    timestamp = row_dict["last_decision_time"]
                    bid = row_dict["bid_cpm"]
                    results[keyword].append(
                        BidPositionRow(
                            keyword=keyword,
                            position=position,
                            bid=bid,
                            timestamp=timestamp,
                        )
                    )
        return results
