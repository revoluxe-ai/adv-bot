from datetime import datetime
from zoneinfo import ZoneInfo

from .clickhouse_manager import ClickHouseManager
from .clickhouse_manager.dto import ConvCartToViewsOnPosition
from .clickhouse_manager.dto.bid_position import BidPosition


class PredictKeywordsTargetPlace:
    def __init__(self, clickhouse_manager: ClickHouseManager):
        self._clickhouse_manager = clickhouse_manager


    async def get_keywords_target_position(self,*, nmid: int, min_bid: int, positions_size: int) -> dict[str, int]:

        assert positions_size <= 300, 'Количество позиций не может быть больше 300'

        convs_carts_to_views: dict[str, list[ConvCartToViewsOnPosition]] = \
            await self._clickhouse_manager.get_conv_cart_to_views(nmid=nmid,
                                                                  positions_size=positions_size)
        bids_for_positions: dict[str, list[BidPosition]] = \
            await self._clickhouse_manager.get_bids_for_positions(nmid=nmid)
        return self._get_target_positions(convs_carts_to_views,
                                          bids_for_positions,
                                          min_bid,
                                          positions_size)

    def _get_target_positions(self,
                                    convs_carts_to_views: dict[str, list[ConvCartToViewsOnPosition]],
                                    bids_for_positions: dict[str, list[BidPosition]],
                                    min_bid: int,
                                    positions_size: int
                              ) -> dict[str, int]:
        bids_for_positions: dict[str, list[BidPosition]] = self._normalize_bids_for_positions(bids_for_positions,
                                                                convs_carts_to_views,
                                                                min_bid=min_bid,
                                                                positions_size=positions_size)
        result_target_positions: dict[str, int] = {}
        for keyword, positions in bids_for_positions.items():
            best_position: BidPosition = min(positions, key=lambda p: p.pay_for_cart)
            result_target_positions[keyword] = best_position.position
        return result_target_positions


    def _normalize_bids_for_positions(self,
                                      bids_for_positions: dict[str, list[BidPosition]],
                                      convs: dict[str, list[ConvCartToViewsOnPosition]],
                                      min_bid: int,
                                      positions_size: int
                                      ) -> dict[str, list[BidPosition]]:
        normalized_bids_for_positions = {}
        bids_for_positions = self._sort_bids_for_positions(bids_for_positions)
        for key, items in bids_for_positions.items():
            item_normalized = self._normalize_bids_for_keyword(items,
                                                               min_bid=min_bid,
                                                               positions_size=positions_size)
            convs_for_keyword = convs.get(key)
            if not convs_for_keyword:
                continue
            positions_filled = self._fill_positions_convs(item_normalized, convs_for_keyword)

            normalized_bids_for_positions[key] = positions_filled
        return normalized_bids_for_positions

    def _normalize_bids_for_keyword(self,
                                    items: list[BidPosition],
                                    min_bid: int,
                                    positions_size: int) -> list[BidPosition]:
        items = self._delete_bids_low_then_min_bid(items, min_bid)
        cleared_items = self._delete_bad_bids(items)
        positions_filled: list[BidPosition] = self._fill_positions(cleared_items, min_bid=min_bid, size=positions_size)
        positions_tail_trimmed_tail = self._trim_tail(positions_filled, min_bid)
        return positions_tail_trimmed_tail

    @staticmethod
    def _sort_bids_for_positions(bids_for_positions: dict[str, list[BidPosition]]) -> dict[str, list[BidPosition]]:
        def sort_func(item: BidPosition) -> int:
            return item.position

        sorted_results = {}
        for key, items in bids_for_positions.items():
            items.sort(key=sort_func)
            sorted_results[key] = items
        return sorted_results


    @staticmethod
    def _delete_bad_bids(items: list[BidPosition]) -> list[BidPosition]:
        items.sort(key=lambda item: item.position)
        bad_indexes: set[int] = set()
        for index, bid in enumerate(items):
            if index in bad_indexes:
                continue
            tail = items[index + 1:]
            for index_2, bid_2 in enumerate(tail):
                if bid.bid > bid_2.bid:
                    continue
                else:
                    if bid.timestamp > bid_2.timestamp:
                        bad_indexes.add(index_2 + 1 + index)
                    else:
                        bad_indexes.add(index)
        normalized_items = []
        for index, bid in enumerate(items):
            if index in bad_indexes:
                continue
            normalized_items.append(bid)
        return normalized_items

    @staticmethod
    def _fill_positions(items: list[BidPosition], min_bid: int, size: int) -> list[BidPosition]:
        if not items:
            return []
        assert len(set([item.keyword for item in items])) == 1, 'Позиции от разных ключей'
        keyword: str = items[0].keyword
        pos_to_position: dict[int, BidPosition] = {pos.position:pos for pos in items}
        items.sort(key=lambda x: x.position)
        time_stamp = datetime.now(ZoneInfo('Europe/Moscow'))
        dummy_positions = []
        for position in range(1, size + 1):
            pos = pos_to_position.get(position)
            if pos:
                continue
            else:
                tail = [pos for pos in items if pos.position > position]
                if tail:
                    next_position = tail[0]
                    bid = next_position.bid
                    dummy_bid_position = BidPosition(keyword=keyword,
                                                     position=position,
                                                     bid=bid,
                                                     timestamp=time_stamp,
                                                     )
                    dummy_positions.append(dummy_bid_position)
                else:
                    dummy_positions.append(BidPosition(keyword=keyword,
                                                       position=position,
                                                       bid=min_bid,
                                                       timestamp=time_stamp,))
        result = items + dummy_positions
        result.sort(key=lambda x: x.position)
        return result

    @staticmethod
    def _fill_positions_convs(positions: list[BidPosition],
                              convs: list[ConvCartToViewsOnPosition]) -> list[BidPosition]:
        assert len(set([pos.keyword for pos in positions] + [conv.keyword for conv in convs])) == 1
        positions_filled = []
        convs_dict = {conv.position:conv for conv in convs}
        for position in positions:
            conv = convs_dict.get(position.position)
            if conv:
                position.conv_carts_to_views = conv.conv_cart_to_views
                positions_filled.append(position)
        return positions_filled

    @staticmethod
    def _delete_bids_low_then_min_bid(items: list[BidPosition], min_bid: int) -> list[BidPosition]:
        cleared_items: list[BidPosition] = []
        for bid in items:
            if bid.bid < min_bid:
                continue
            cleared_items.append(bid)
        return cleared_items

    @staticmethod
    def _trim_tail(positions: list[BidPosition], min_bid: int) -> list[BidPosition]:
        positions.sort(key=lambda pos: pos.position)
        for index, pos in enumerate(positions):
            if pos.bid == min_bid:
                catch_index = index
                break
        else:
            return positions
        return positions[:catch_index + 1]
















