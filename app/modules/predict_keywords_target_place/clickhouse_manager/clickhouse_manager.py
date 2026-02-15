from collections import defaultdict

from app.core.clickhouse_manager.base_clickhouse_manager import BaseClickHouseManager
from .dto import BidPosition, ConvCartToViewsOnPosition
from app.utils.click_house.client import get_clickhouse_client as get_client


class ClickHouseManager(BaseClickHouseManager):

    async def get_conv_cart_to_views(self, nmid: int,
                                     positions_size: int) -> dict[str, list[ConvCartToViewsOnPosition]]:
        query = self._get_query('get_conv_carts_to_views')
        async with get_client() as client:
            result = await client.query(query,
                                        parameters={'nmid': nmid,
                                                'positions_size': positions_size},
                                        )
            column_names = result.column_names
            results: dict[str, list[ConvCartToViewsOnPosition]] = defaultdict(list)
            # Consume all rows INSIDE the async context before the connection closes
            rows = list(result.result_rows)
            for row in rows:
                row_dict = dict(zip(column_names, row))
                keyword = row_dict['text']
                conv = row_dict['p_key_pos']
                position = row_dict['pos.pos_bin']
                conv_cart_to_views_in_position = ConvCartToViewsOnPosition(
                    keyword=keyword,
                    position=position,
                    conv_cart_to_views=conv,
                )
                results[keyword].append(conv_cart_to_views_in_position)
            return results

    async def get_bids_for_positions(self, nmid: int)-> dict[str, list[BidPosition]]:
        query = self._get_query('get_bids_for_positions')
        async with get_client() as client:
            result = await client.query(query, parameters={'nmid':nmid})
            column_names = result.column_names
            results = defaultdict(list[BidPosition])
            rows = list(result.result_rows)
            for row in rows:
                row_dict = dict(zip(column_names, row))
                keyword = row_dict['norm_query']
                position = row_dict['pos_bin']
                timestamp = row_dict['last_decision_source']
                bid = row_dict['bid_cpm']
                pos = BidPosition(keyword=keyword,
                                  position=position,
                                  bid=bid,
                                  timestamp=timestamp)
                results[keyword].append(pos)
        return results









