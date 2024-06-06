import asyncio

from sqlalchemy import select

from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.models import WBUserCabinet, WBCabinet
from app.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater
from app.utils.db.session_maker import get_async_session_maker
import logging

logger = logging.getLogger(__name__)


sm = get_async_session_maker

test_shop_id = '93d70b23-32b4-4f1c-a431-985386197cfd'

async def update_data():
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
    asyncio.run(update_data())
