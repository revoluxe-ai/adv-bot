from app.client_bot.user_interface.views import db_manager
from app.modules.common_slaves.wildberries.models import AdvSetting

adv_id = 17542809


async def get_adv_by_id(adv_id: int):
    async with db_manager._sm() as session:
        stmt = db_manager.select(AdvSetting).where(AdvSetting.adv_id == adv_id)
        result = await session.execute(stmt)
        adv = result.scalar_one_or_none()
        return adv

async def get_mean_ctr():
    adv = await get_adv_by_id(adv_id)
    mean_ctr = await db_manager.get_mean_ctr(adv)
    print(mean_ctr)


if __name__ == '__main__':
    import asyncio
    asyncio.run(get_mean_ctr())