from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet, WBUserCabinet
from app.utils.db.models import User
from app.utils.db.session_maker import get_session_maker

sm = get_session_maker()

"""Здесь нужно найти найти пользователя и создать wbusercabinet для админа"""


client_link = 'https://t.me/inavsek'

client_name = client_link.replace('https://t.me/', '')

if __name__ == '__main__':

    with sm() as session:
       stmt = select(User)\
       .join(User.wb_tokens)\
       .filter(User.username == client_name)

       user = session.execute(stmt).scalar()

       for token in  user.wb_tokens:
            print(token.api_key)

