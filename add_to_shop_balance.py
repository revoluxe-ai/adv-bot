from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import WBCabinet
from app.utils.db.session_maker import get_async_session_maker as sm

shop_id = 'b1f6b9d2-7722-59ba-a37a-6d5fbcc6b165'
add_balance = 1000
add_bonus = +50000
async def add_balance_and_bonus():
    async with sm(read_only=False) as session:
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