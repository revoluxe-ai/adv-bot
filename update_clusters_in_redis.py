

import asyncio

from sqlalchemy import select

from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.api import WBApi
from app.modules.common_slaves.wildberries.models import WBUserCabinet, WBCabinet, AdvSetting
from app.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater
from app.modules.wb_adv_updater.wb_manager import keyword_stat_updater
from app.utils import redis_manager
from app.utils.click_house.client import get_clickhouse_client
from app.utils.db.session_maker import get_async_session_maker
import logging

logger = logging.getLogger(__name__)


sm = get_async_session_maker

test_shop_id = '8a2acf65-1b2c-4061-9ae5-fed8ffb04371'

async def update_crusters_for_shop():
    wb_access = await get_access()
    wb_api = WBApi(wb_access)
    async with sm() as session:
        query = select(AdvSetting)\
            .join(AdvSetting.wb_cabinet)\
            .filter(WBCabinet.shop_id == test_shop_id)
        adv_settings = await session.execute(query)
        adv_settings = adv_settings.scalars().all()
    async with get_clickhouse_client() as client:
        for adv in adv_settings:
           try:
               await  keyword_stat_updater(client, adv.id,wb_api)
           except Exception as e:
               logger.error(f'Error getting clusters for adv {adv.id}: {e}',
                            exc_info=True)
               continue


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
    asyncio.run(update_crusters_for_shop())

