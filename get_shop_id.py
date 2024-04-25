from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet
from app.utils.db.models import User
from app.utils.db.session_maker import get_session_maker

sm = get_session_maker()

"""Здесь нужно найти найти пользователя и создать wbusercabinet для админа"""


client_link = 'https://t.me/inavsek'

client_name = client_link.replace('https://t.me/', '')

if __name__ == '__main__':

    with sm() as session:
       stmt = select(WBCabinet.shop_id)\
       .join(WBCabinet.wb_user_cabinets)\
       .join(WBUserCabinet.user)\
         .filter(User.username == client_name)

       shop_id = session.execute(stmt).scalar()
       print(shop_id)



