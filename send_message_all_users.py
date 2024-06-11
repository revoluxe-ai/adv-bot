import datetime
from hashlib import sha256
from sqlalchemy import select, or_
from app.client_bot.user_interface.views import messages
from app.modules.common_slaves.wildberries.models import WBUserCabinet, WBCabinet
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker
from app.client_bot.bot import bot
import asyncio
from app.admin_bot.sender import redis_manager
sm = get_async_session_maker()
import logging

logger = logging.getLogger(__name__)


async def send_message_to_users():
    send_count = 0
    not_send_count = 0
    async with sm() as session:
        stmt = select(User).distinct(User.id).outerjoin(User.wb_user_cabinets) \
            .outerjoin(WBUserCabinet.wb_cabinet) \
            # .filter(or_(WBCabinet.expiration_time < datetime.datetime.now(),
            #             User.wb_user_cabinets == None
            #             ))
        result = await session.execute(stmt)
        users = result.scalars().all()
        print('Всего пользователей для отправки сообщений: ', len(users))
        for user in users:
            user_id =  user.user_telegram_id
            message = messages.Single_message14
            hash = sha256((str(message)) \
                          .encode()).hexdigest()
            if await redis_manager.check_message_send(hash, user_id):
                send_count += 1
                continue

            try:
                # if user.user_telegram_id not in [373435337, 1058013578, 352225040]:
                #     continue
                await message(bot, user_id)()
                await redis_manager.set_message_send(hash, user_id)
                send_count += 1
            except Exception as e:
                logger.error(f'{e}')
                not_send_count += 1
        print('Отправлено сообщений: ', send_count)
        print('Не отправлено сообщений: ', not_send_count)


if __name__ == '__main__':

    asyncio.run(send_message_to_users())