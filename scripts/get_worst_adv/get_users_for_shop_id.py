import asyncio

from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm

async def get_users(shop_id: str) -> list[User]:
    stmt = select(User).join(User.wb_user_cabinets) \
            .join(WBUserCabinet.wb_cabinet)\
    .where(WBCabinet.shop_id == shop_id)

    async with sm(read_only=False) as session:
        users = await session.execute(stmt)
    return users.scalars().all()




if __name__ == '__main__':
    shop_id = ''
    users = asyncio.run(get_users(shop_id))
    for user in users:
        print(user.username)

