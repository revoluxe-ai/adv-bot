from datetime import timedelta

from app.modules.shop_runner.modules.wb_api import WBApi
from app.utils.timezone import today_moscow


async def get_full_adv_stat_for_adv_ids(
    wb_api: "WBApi", adv_ids: set[int], threshold_dates: int
):
    dates = []
    today = today_moscow()
    last_days = threshold_dates
    for i in range(last_days):
        dates.append(today - timedelta(days=i))
    stats = await wb_api.get_adv_full_state(list(adv_ids), dates)
    return stats
