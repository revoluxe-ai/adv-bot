import datetime
from datetime import timedelta

from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import WBUserCabinet, WBCabinet
from app.utils.db.models import User
from app.utils.db.session_maker import get_session_maker

sm = get_session_maker()

"""Здесь нужно найти найти пользователя и создать wbusercabinet для админа"""


shop_id = '69b113be-2867-4c44-80b3-3066f28a94df'.strip()


if __name__ == '__main__':

    with sm() as session:
         stmt = select(WBCabinet)\
         .where(WBCabinet.shop_id == shop_id)
         wb_cabinet: WBCabinet = session.execute(stmt).scalar()
         expiration_time = wb_cabinet.expiration_time
         if expiration_time < datetime.datetime.now():
              expiration_time = datetime.datetime.now()
         wb_cabinet.expiration_time = expiration_time + timedelta(days=33)
         wb_cabinet.demo = False
         wb_cabinet.active = True
         session.commit()



