from app.modules.common_slaves.wildberries.models import AdvSetting
from app.core.clikhouse_client_manager import get_client
from app.utils.ch_semaphore import anti_ch_crash_semaphore


async def get_cart_to_order_ratio_from_common_items_stat(
    adv: "AdvSetting", pass_days: int
) -> float | None:
    nmids = adv.nmids
    query = """
          SELECT
          if(SUM(orders) = 0, 0.0, SUM(add_to_cart) / SUM(orders)) AS cart_to_order_ratio
          FROM (
              SELECT
                  nmid,
                  date,
                  argMax(add_to_cart, version) AS add_to_cart,
                  argMax(orders, version) AS orders
              FROM default_db.wb_common_stat
              WHERE nmid IN {nmids:Array(UInt64)}
                AND date >= today() - INTERVAL {pass_days:UInt64} DAY
              GROUP BY nmid, date)"""

    async with anti_ch_crash_semaphore:
        async with get_client() as client:
            result = await client.query(
                query,
                parameters={
                    "nmids": nmids,
                    "pass_days": pass_days,
                },
            )
    if not result or result.first_row[0] is None:
        return None
    ratio = result.first_row[0]
    return ratio
