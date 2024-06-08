import datetime
from datetime import timedelta

from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import WBUserCabinet, WBCabinet
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

sm = get_async_session_maker


"""Здесь нужно найти найти пользователя и создать wbusercabinet для админа"""


shop_id = 'e4c7631a-fc60-4020-b06a-44dc0f3eef84'.strip()

period = 33


async def set_period_for_shop(shop_id: str, period: int):
     async with sm() as session:
          stmt = select(WBCabinet) \
               .where(WBCabinet.shop_id == shop_id)
          result = await session.execute(stmt)
          wb_cabinet = result.scalar_one_or_none()
          expiration_time = wb_cabinet.expiration_time
          if expiration_time < datetime.datetime.now():
               expiration_time = datetime.datetime.now()
          wb_cabinet.expiration_time = expiration_time + timedelta(days=period)
          wb_cabinet.demo = False
          wb_cabinet.active = True
          await session.commit()


if __name__ == '__main__':
     import asyncio
     asyncio.run(set_period_for_shop(shop_id, period))




