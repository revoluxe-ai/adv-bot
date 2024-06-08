import datetime
from datetime import timedelta

from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import WBUserCabinet, WBCabinet
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

sm = get_async_session_maker

"""Здесь нужно найти найти пользователя и создать wbusercabinet для админа"""


shop_id = '45c8c933-d7b2-4ef2-bcd3-1a6a7f1155d1'.strip()



async def set_period_for_shop(shop_id: str, period: int):
     async with sm() as session:
          stmt = select(WBCabinet) \
               .where(WBCabinet.shop_id == shop_id)
          wb_cabinet: WBCabinet = session.execute(stmt).scalar()
          expiration_time = wb_cabinet.expiration_time
          if expiration_time < datetime.datetime.now():
               expiration_time = datetime.datetime.now()
          wb_cabinet.expiration_time = expiration_time + timedelta(days=period)
          wb_cabinet.demo = False
          wb_cabinet.active = True
          session.commit()


if __name__ == '__main__':
     import asyncio
     asyncio.run(set_period_for_shop(shop_id, 33))




