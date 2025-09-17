import asyncio

from sqlalchemy import update

from app.modules.common_slaves.wildberries.models import KeywordSetting
from app.utils.db.session_maker import get_async_session_maker as sm


async def set_relevant_if_white_list() -> None:
    stmt = update(KeywordSetting).where(KeywordSetting.hard_status == 2).values({"relevant": True})
    async with sm() as session:
        await session.execute(stmt)
        await session.commit()


if __name__ == "__main__":
    asyncio.run(set_relevant_if_white_list())
