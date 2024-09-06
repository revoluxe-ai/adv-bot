from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import WBCabinet
from app.utils.db.session_maker import get_async_session_maker as sm

shop_id = '8a2acf65-1b2c-4061-9ae5-fed8ffb04371'
add_balance = 1000000
add_bonus = 100000

async def add_balance_and_bonus():
    async with sm() as session:
        stmt = select(WBCabinet).where(WBCabinet.shop_id == shop_id)
        result = await session.execute(stmt)
        wb_cabinet = result.scalar_one_or_none()
        if not (balance := wb_cabinet.balance):
            wb_cabinet.balance = 0
        if not (bonus := wb_cabinet.bonus):
            wb_cabinet.bonus = 0
        wb_cabinet.balance += add_balance
        wb_cabinet.bonus = + add_bonus
        await session.commit()



if __name__ == '__main__':
    import asyncio
    asyncio.run(add_balance_and_bonus())