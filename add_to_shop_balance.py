from sqlalchemy import select
import dotenv
dotenv.load_dotenv()
from app.modules.common_slaves.wildberries.models import WBCabinet
from app.utils.db.session_maker import get_async_session_maker as sm


shop_id = ''
add_balance =
add_bonus =


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
        print(f'Баланс кабинета {shop_id} увеличен на {add_balance} и {add_bonus} рублей')



if __name__ == '__main__':
    import asyncio
    asyncio.run(add_balance_and_bonus())