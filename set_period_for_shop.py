import datetime
from datetime import timedelta

from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import WBUserCabinet, WBCabinet
from app.utils.db.models import User
from app.utils.db.session_maker import get_session_maker

sm = get_session_maker()

"""Здесь нужно найти найти пользователя и создать wbusercabinet для админа"""


shop_id = '8a2acf65-1b2c-4061-9ae5-fed8ffb04371'.strip()


if __name__ == '__main__':

    with sm() as session:
         stmt = select(WBCabinet)\
         .where(WBCabinet.shop_id == shop_id)
         wb_cabinet: WBCabinet = session.execute(stmt).scalar()
         expiration_time = wb_cabinet.expiration_time
         if expiration_time < datetime.datetime.now():
              expiration_time = datetime.datetime.now()
         wb_cabinet.expiration_time = expiration_time + timedelta(days=30)
         wb_cabinet.demo = False
         wb_cabinet.active = True
         session.commit()



