from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.client import get_clickhouse_client

__all__ = ["get_sum_spend_for_complex_adv"]


query = """
WITH max_versions AS (
    SELECT
        spend,
        date,  -- добавляем сюда
        ROW_NUMBER() OVER (PARTITION BY adv_id, date ORDER BY version DESC) AS row_num
    FROM default_db.full_adv_wb_stat
    WHERE adv_id IN %(adv_ids)s
)
SELECT
    SUM(spend) AS spend
FROM max_versions
WHERE row_num = 1
GROUP BY date
ORDER BY date

"""


async def get_sum_spend_for_complex_adv(auto_adv_id: int, auction_adv_id: int) -> float:
    async with anti_ch_crash_semaphore:
        async with get_clickhouse_client() as client:
            result = await client.query(
                query, parameters={"adv_ids": [auto_adv_id, auction_adv_id]}
            )

        sum_spend: float = result.first_item["spend"]
        return sum_spend
