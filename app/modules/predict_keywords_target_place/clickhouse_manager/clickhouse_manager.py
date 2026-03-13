from collections import defaultdict

from app.core.clickhouse_manager.base_clickhouse_manager import BaseClickHouseManager
from app.utils.click_house.client import get_clickhouse_client as get_client

from .dto import ConvCartToViewsOnPosition


class ClickHouseManager(BaseClickHouseManager):
    """ClickHouse manager for predict_keywords_target_place: conv_cart_to_views only."""

    async def get_conv_cart_to_views(
        self, nmid: int, positions_size: int
    ) -> dict[str, list[ConvCartToViewsOnPosition]]:
        query = self._get_query("get_conv_carts_to_views")
        async with get_client() as client:
            result = await client.query(
                query,
                parameters={"nmid": nmid, "positions_size": positions_size},
            )
            column_names = result.column_names
            results: dict[str, list[ConvCartToViewsOnPosition]] = defaultdict(list)
            rows = list(result.result_rows)
            for row in rows:
                row_dict = dict(zip(column_names, row))
                keyword = row_dict["text"]
                conv = row_dict["p_key_pos"]
                position = row_dict["pos.pos_bin"]
                results[keyword].append(
                    ConvCartToViewsOnPosition(
                        keyword=keyword,
                        position=position,
                        conv_cart_to_views=conv,
                    )
                )
        return results
