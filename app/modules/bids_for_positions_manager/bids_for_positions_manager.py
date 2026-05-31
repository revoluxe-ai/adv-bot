"""Manager: fetch and normalize bid positions from ClickHouse (no conv)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from .clickhouse_manager import BidsForPositionsClickHouseManager
from .dto import BidPositionRow


class BidsForPositionsManager:
    """Fetches bids for positions from CH and normalizes them (sort, filter, fill, trim). No conv."""

    def __init__(self, clickhouse_manager: BidsForPositionsClickHouseManager) -> None:
        self._clickhouse_manager = clickhouse_manager

    async def get_bid_positions_normalized(
        self,
        nmid: int,
        min_bid: int,
        positions_size: int,
    ) -> dict[str, list[BidPositionRow]]:
        """Return normalized bid positions per keyword (no conv_carts_to_views)."""
        raw: dict[str, list[BidPositionRow]] = (
            await self._clickhouse_manager.get_bids_for_positions(nmid=nmid)
        )
        sorted_bids = self._sort_bids_for_positions(raw)
        return self._normalize_bids_for_positions(
            sorted_bids, min_bid=min_bid, positions_size=positions_size
        )

    def _normalize_bids_for_positions(
        self,
        bids_for_positions: dict[str, list[BidPositionRow]],
        min_bid: int,
        positions_size: int,
    ) -> dict[str, list[BidPositionRow]]:
        normalized: dict[str, list[BidPositionRow]] = {}
        for key, items in bids_for_positions.items():
            item_normalized = self._normalize_bids_for_keyword(
                items, min_bid=min_bid, positions_size=positions_size
            )
            normalized[key] = item_normalized
        return normalized

    def _normalize_bids_for_keyword(
        self,
        items: list[BidPositionRow],
        min_bid: int,
        positions_size: int,
    ) -> list[BidPositionRow]:
        items = self._delete_bids_low_then_min_bid(items, min_bid)
        cleared_items = self._delete_bad_bids(items)
        positions_filled = self._fill_positions(
            cleared_items, min_bid=min_bid, size=positions_size
        )
        return self._trim_tail(positions_filled, min_bid)

    @staticmethod
    def _sort_bids_for_positions(
        bids_for_positions: dict[str, list[BidPositionRow]],
    ) -> dict[str, list[BidPositionRow]]:
        def sort_func(item: BidPositionRow) -> int:
            return item.position

        sorted_results: dict[str, list[BidPositionRow]] = {}
        for key, items in bids_for_positions.items():
            items = list(items)
            items.sort(key=sort_func)
            sorted_results[key] = items
        return sorted_results

    @staticmethod
    def _delete_bad_bids(items: list[BidPositionRow]) -> list[BidPositionRow]:
        items = list(items)
        items.sort(key=lambda item: item.position)
        bad_indexes: set[int] = set()
        for index, bid in enumerate(items):
            if index in bad_indexes:
                continue
            tail = items[index + 1 :]
            for index_2, bid_2 in enumerate(tail):
                if bid.bid > bid_2.bid:
                    continue
                if bid.timestamp > bid_2.timestamp:
                    bad_indexes.add(index_2 + 1 + index)
                else:
                    bad_indexes.add(index)
        return [bid for index, bid in enumerate(items) if index not in bad_indexes]

    @staticmethod
    def _fill_positions(
        items: list[BidPositionRow], min_bid: int, size: int
    ) -> list[BidPositionRow]:
        if not items:
            return []
        assert len(set(item.keyword for item in items)) == 1, "Позиции от разных ключей"
        keyword: str = items[0].keyword
        pos_to_position: dict[int, BidPositionRow] = {
            pos.position: pos for pos in items
        }
        items = list(items)
        items.sort(key=lambda x: x.position)
        time_stamp = datetime.now(ZoneInfo("Europe/Moscow"))
        dummy_positions: list[BidPositionRow] = []
        for position in range(1, size + 1):
            pos = pos_to_position.get(position)
            if pos is not None:
                continue
            tail = [p for p in items if p.position > position]
            if tail:
                next_position = tail[0]
                dummy_positions.append(
                    BidPositionRow(
                        keyword=keyword,
                        position=position,
                        bid=next_position.bid,
                        timestamp=time_stamp,
                        ch_observed=False,
                    )
                )
            else:
                dummy_positions.append(
                    BidPositionRow(
                        keyword=keyword,
                        position=position,
                        bid=min_bid,
                        timestamp=time_stamp,
                        ch_observed=False,
                    )
                )
        result = items + dummy_positions
        result.sort(key=lambda x: x.position)
        return result

    @staticmethod
    def _delete_bids_low_then_min_bid(
        items: list[BidPositionRow], min_bid: int
    ) -> list[BidPositionRow]:
        return [bid for bid in items if bid.bid >= min_bid]

    @staticmethod
    def _trim_tail(
        positions: list[BidPositionRow], min_bid: int
    ) -> list[BidPositionRow]:
        positions = list(positions)
        positions.sort(key=lambda pos: pos.position)
        for index, pos in enumerate(positions):
            if pos.bid == min_bid:
                return positions[: index + 1]
        return positions
