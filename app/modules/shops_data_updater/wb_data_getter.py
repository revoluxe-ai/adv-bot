from datetime import datetime, timedelta
import typing

if typing.TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.api import WBApi


async def get_full_adv_stat_for_adv_ids(wb_api: 'WBApi', adv_ids: list[int], pass_days: int):
    dates  = []
    today = datetime.now().date()
    last_days = pass_days
    for i in range(last_days):
        dates.append(today - timedelta(days=i))
    stats = await wb_api.advert.get_adv_full_state(adv_ids, dates)
    return stats