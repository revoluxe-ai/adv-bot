from sqlalchemy import select

from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.api import WBApi
from app.modules.common_slaves.wildberries.models import WBUserCabinet, AdvSetting, WBCabinet
from app.modules.wb_adv_updater.wb_manager import Manager
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm



async def get_advs_for_user():
    async with sm() as session:
        stmt = select(AdvSetting).join(WBCabinet).join(WBUserCabinet).join(User).where(User.username == 'MARIYA_Zommer')
        result = await session.execute(stmt)
        advs: list[AdvSetting] = result.scalars().all()
        for adv in advs:
            print(adv.bot_active)
            adv.bot_active = False
        await session.commit()



if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(get_advs_for_user())