from datetime import datetime, timedelta

import aiofiles
from aiohttp import ClientSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from app.modules.common_slaves.wildberries.wb_api import WBApi
from app.modules.full_stat_adv_updater.types import FullAdvStat
from app.modules.full_stat_adv_updater.types.full_adv_stat import DayStats
from app.utils.db.session_maker import get_async_session_maker as sm


async def upload_full_adv_stat(wb_cabinet_id: int, client_session):
    access = await super_cabinet_manager.get_access_for_wb_cabinet(wb_cabinet_id)
    wb_api = WBApi(access, client_session)

    stmt = select(AdvSetting.adv_id).where(
        AdvSetting.wb_cabinet_id == wb_cabinet_id, AdvSetting.bidder_active == True
    )
    async with sm() as session:
        result = await session.execute(stmt)
        adv_ids = result.scalars().all()
    dates = []
    today = datetime.now().date()
    last_days = 7
    for i in range(last_days):
        dates.append(today - timedelta(days=i))
    stats = await wb_api.advert.def_get_adv_full_state(adv_ids, dates)
    return stats


async def get_adv_setting(adv_id: int):
    stmt = (
        select(AdvSetting)
        .options(joinedload(AdvSetting.wb_cabinet))
        .where(AdvSetting.adv_id == adv_id)
    )
    async with sm() as session:
        result = await session.execute(stmt)
        adv_setting = result.scalar()
    return adv_setting


async def get_csv_stat(shop_ids: list[str], client_session):
    header = None
    rows = []
    for shop_id in shop_ids:
        stmt = select(AdvSetting).join(AdvSetting.wb_cabinet).where(WBCabinet.shop_id == shop_id)
        async with sm() as session:
            result = await session.execute(stmt)
            adv_setting = result.scalar()
        wb_cabinet_id = adv_setting.wb_cabinet_id
        wb_cabinet = adv_setting.wb_cabinet
        if not (balance := wb_cabinet.balance):
            balance = 0
        if not (bonus := wb_cabinet.bonus):
            bonus = 0
        total = balance + bonus
        stats: list[FullAdvStat] = asyncio.run(
            upload_full_adv_stat(wb_cabinet_id, client_session),
        )
        max_stat_days = max([len(stat.days) for stat in stats])
        if header is None:
            header = "shop_id; adv_id; name; " + ";".join([str(i) for i in range(max_stat_days)])
            header += "; Баланс"
        for stat in stats:
            adv: AdvSetting = await get_adv_setting(stat.advertId)
            name = adv.name
            adv_id = adv.adv_id
            stat_days: list[DayStats] = sorted(stat.days, key=lambda x: x.date, reverse=True)
            shop_id = adv.wb_cabinet.shop_id
            row = f"""{shop_id}; {adv_id}; {name}; {";".join([str(day.orders) for day in stat_days])}"""
            row += f"; {total}"
            rows.append(row)

    csv = "\n".join([header] + rows)
    async with aiofiles.open("full_stats.csv", "w", encoding="utf8") as f:
        await f.write(csv)


shop_ids = [
    "e1b05fca-4c41-471d-be8c-0cba27c96b0a",
    "2a26710b-f385-4ac6-977e-2a105f34ccd6",
    "f84f665d-b426-4b6d-a36a-dd978c4a2547",
    "ac1d2b97-0b95-4e5f-89e4-6ebb4a2f2660",
]

if __name__ == "__main__":
    import asyncio

    async def main() -> None:
        async with ClientSession() as session:
            await get_csv_stat(shop_ids, session)

    asyncio.run(main())
