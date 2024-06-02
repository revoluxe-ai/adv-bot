import asyncio

from sqlalchemy import select

from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

test_users_telegram_ids= [352225040 , 5378020690]


sm = get_async_session_maker()

async def delete_test_users():
    async with sm() as session:
        stmt = select(User).where(User.user_telegram_id.in_(test_users_telegram_ids))
        result = await session.execute(stmt)
        users = result.scalars().all()
        for user in users:
            await session.delete(user)
        await session.commit()

if __name__ == '__main__':
    asyncio.run(delete_test_users())
