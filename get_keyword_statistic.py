from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.wb_adv_updater.data_managers import get_keywords_statistic
from app.utils.db.session_maker import get_async_session_maker


async_session_maker = get_async_session_maker()

async def main():
    async with async_session_maker() as session:  # Use async context manager
        async with session.begin():  # Start a transaction
            # Asynchronous query execution
            result = await session.execute(
                select(AdvSetting).filter(AdvSetting.adv_id == 15010746)
            )
            adv_setting = result.scalar_one_or_none()  # Use scalar_one_or_none to avoid exceptions if no rows are found

    # Outside of the session context
    if adv_setting:
        pass_days = None
        keywords_stats = await get_keywords_statistic(adv_setting, pass_days)  # Assume this function is also async

        for keywords_stat in keywords_stats:
            print(keywords_stat.text, keywords_stat.ctr, keywords_stat.clicks, keywords_stat.views)

# Run the main coroutine
if __name__ == '__main__':
    import asyncio
    asyncio.run(main())