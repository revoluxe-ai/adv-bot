from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import WBCabinet
from app.utils.db.session_maker import get_async_session_maker as sm

shop_id = 'ab71abdd-0295-46e0-800f-beab07958883'
add_balance = 500
add_bonus =  add_balance*2

async def add_balance_and_bonus():
    async with sm() as session:
        stmt = select(WBCabinet).where(WBCabinet.shop_id == shop_id)
        result = await session.execute(stmt)
        wb_cabinet = result.scalar_one_or_none()
        if not (balance := wb_cabinet.balance):
            balance = 0
        if not (bonus := wb_cabinet.bonus):
            bonus = 0
        wb_cabinet.balance = balance + add_balance
        wb_cabinet.bonus = bonus + add_bonus
        await session.commit()



if __name__ == '__main__':
    import asyncio
    asyncio.run(add_balance_and_bonus())