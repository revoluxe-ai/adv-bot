from sqlalchemy import select

from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.api import WBApi
from app.modules.common_slaves.wildberries.models import WBUserCabinet, AdvSetting, WBCabinet
from app.modules.wb_adv_updater.wb_manager import Manager
from app.utils.db.session_maker import get_async_session_maker as sm



shop_id = '89b37551-ff7f-4124-ac7e-cd7546af25cf'

adv_id = 18616947

async def get_wb_user_cabinet():
    async with sm() as session:
        stmt = select(WBUserCabinet).join(WBCabinet).where(WBCabinet.shop_id == shop_id)
        result = await session.execute(stmt)
        wb_user_cabinet = result.scalar()
    return wb_user_cabinet



async def get_keywords_stat_from_wb(semaphore):
    async with sm() as session:
        stmt = select(AdvSetting).where(AdvSetting.adv_id == adv_id)
        result = await session.execute(stmt)
        adv_setting = result.scalar()

    wb_user_cabinet = await get_wb_user_cabinet()
    access = await super_cabinet_manager.get_access_for_wb_user_cabinet(wb_user_cabinet)
    wb_api = WBApi(access)
    wb_manager = Manager()
    await wb_manager.keyword_stat_updater(adv_setting, wb_api, semaphore)





if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    keyword_stat = loop.run_until_complete(get_keywords_stat_from_wb(None))
    print(keyword_stat)











