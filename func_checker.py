import asyncio

from sqlalchemy import select

from auto_adv_master.modules.common_slaves.wildberries import super_cabinet_manager
from auto_adv_master.modules.common_slaves.wildberries.models import WBUserCabinet, WBCabinet
from auto_adv_master.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater
from auto_adv_master.utils.db.session_maker import get_async_session_maker
import logging

logger = logging.getLogger(__name__)


sm = get_async_session_maker()

test_shop_id = '4a843047-429f-5a00-b659-156f6c81b70f'

async def getting_cards():
    wb_access = await get_access()
    shop_data_updater = ShopDataUpdater(wb_access)
    await shop_data_updater.update_all_data()


async def get_wb_user_cabinet():
    async with sm() as session:
        query = select(WBUserCabinet).join(WBUserCabinet.wb_cabinet)\
        .filter(WBCabinet.shop_id == test_shop_id)
        wb_user_cabinet = await session.execute(query)
        wb_user_cabinet = wb_user_cabinet.scalars().first()
        return wb_user_cabinet

async def get_access():
    wb_user_cabinet = await get_wb_user_cabinet()
    access = await super_cabinet_manager.get_access_for_wb_user_cabinet(wb_user_cabinet)
    return access

if __name__ == '__main__':
    asyncio.run(getting_cards())
