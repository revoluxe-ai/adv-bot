from app.utils.click_house.client import get_clickhouse_client


async def get_clicks_to_orders_ration_on_phrases(
    adv_ids: list[int], days: int
) -> float:
    """Получает соотношение кликов к заказам по фразам из ClickHouse"""
    query = """
            SELECT 
               IF(
                    SUM(toFloat64(orders)) = 0, 
                     SUM(toFloat64(clicks)), 
                       SUM(toFloat64(clicks)) / SUM(toFloat64(orders))
                ) AS ratio
            FROM (
                SELECT 
                    adv_id,
                    date,
                    argMax(clicks, version) AS clicks,
                    argMax(orders, version) AS orders
                FROM default_db.full_adv_wb_stat
                WHERE adv_id IN {adv_ids:Array(UInt32)}
                  AND date >= today() - INTERVAL {days:UInt32} DAY
                GROUP BY adv_id, date
                )
    """

    async with get_clickhouse_client() as client:
        result = await client.query(query, {"adv_ids": adv_ids, "days": days})
    return float(list(result.named_results())[0]["ratio"])
