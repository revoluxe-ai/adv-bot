import logging
from pathlib import Path

from app.utils.click_house.client import get_clickhouse_client

logger = logging.getLogger(__name__)


class TotalOrdersManager:
    @staticmethod
    async def get_total_orders(
        nmid: int,
        keywords_texts: list[str],
    ) -> dict[str, int]:
        """Deprecated: используйте get_total_stats вместо этого"""
        stats = await TotalOrdersManager.get_total_stats(nmid)
        return {text: stats.get(text, (0, 0))[0] for text in keywords_texts}

    @staticmethod
    async def get_total_stats(
        nmid: int,
    ) -> dict[str, tuple[int, int]]:
        """
        Получить суммарные заказы и показы по ключевым словам.
        
        Returns:
            dict[str, tuple[int, int]]: {keyword_text: (total_orders, total_views)}
        """

        query = (Path(__file__).parent / "sql" / "get_total_orders.sql").read_text()


        async with get_clickhouse_client() as client:
            result = await client.query(
                query,
                parameters={
                    "nmid": nmid,

                },
            )

        rows = result.result_rows or []
        # row[0] = text, row[1] = total_orders, row[2] = total_views
        stats_map: dict[str, tuple[int, int]] = {}
        for row in rows:
            if row and len(row) >= 3:
                text = str(row[0])
                orders = int(row[1]) if row[1] is not None else 0
                views = int(row[2]) if row[2] is not None else 0
                stats_map[text] = (orders, views)
        return stats_map


