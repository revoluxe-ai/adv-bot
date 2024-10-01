import asyncio
import logging
from hashlib import sha256
from typing import Optional
# from app.client_bot.user_interface.
import aiogram
from aiogram.exceptions import TelegramForbiddenError
from .utils import utils
from app.client_bot.bot import bot
from app.client_bot.utils import data_manager
from python_modules.logger import setup_logging

from python_modules.logger import setup_logging
from ...modules.common_slaves.wildberries.models import WBUserCabinet, WBItemPosition
from ...utils import redis_manager
from ...utils.db.models import User
from app.client_bot.user_interface.views import messages


setup_logging()

logger = logging.getLogger(__name__)

admin_chat_id = 373435337

test_user_ids = [5378020690, 373435337]



# async def send_to_users_out_channel():
#     users = await data_manager.get_all_users()
#     # users = [user for user in users if user.user_telegram_id in test_user_ids]
#     hash = sha256(str(message).encode()).hexdigest()
#     for user in users:
#         if await redis_manager.check_message_send(hash, user.user_telegram_id):
#             logger.info(f'Сообщение уже отправлено пользователю {user.username}')
#             continue
#         user_id = user.user_telegram_id
#         try:
#             check = await utils.check_user_in_support_channel(bot, user_id)
#         except aiogram.exceptions.TelegramBadRequest as e:
#             logger.error(f'Ошибка при проверке пользователя {user.username} в канале поддержки {e}')
#             continue
#         if not check:
#             try:
#                 await message(bot, user_id)()
#                 await redis_manager.set_message_send(hash, user_id)
#                 await asyncio.sleep(1)
#
#             except TelegramForbiddenError:
#                 logger.error(f'Пользователь {user.username} заблокировал бота')
#
#             finally:
#                 http_session = bot.session
#                 if http_session:
#                     await http_session.close()


async def send_message_to_admin(text: str, off = False):
    if off:
        return
    try:
        await bot.send_message(admin_chat_id, text)
    except Exception as exc:
        logger.error(f'Ошибка при отправке сообщения админу {exc}')

async def send_message_to_user(wb_user_cabinet: WBUserCabinet, message):
    user: User = wb_user_cabinet.user
    await message(bot, user.user_telegram_id, wb_user_cabinet.name)()


async def get_users_from_nmid(nmid: int):
    users = await data_manager.get_users_from_nmid(nmid)
    return users


async def check_last_position(last_position: Optional[WBItemPosition],
                              new_position: WBItemPosition):
    try:
        nmid = new_position.nmid
        if not last_position:
            last_position = new_position
        text = new_position.keyword_text
        cluster_name, _ = await redis_manager.get_cluster_and_preset(text)
        if not cluster_name:
            return
        if last_position.base_position > 0 and new_position.base_position == 0:

            keyword_send_status: str = await redis_manager.get_keyword_send_status(cluster_name, new_position.nmid)
            if keyword_send_status == 'ItemIsOutOfIndex':
                return
            users = await get_users_from_nmid(nmid)
            for user in users:
                try:
                    await messages.ItemIsOutOfIndex(bot,
                                                user.user_telegram_id,
                                                last_position,
                                                    new_position)()
                except Exception as exc:
                    logger.error(f'Ошибка при отправке сообщения пользователю {user.username}: {exc}')
            await redis_manager.set_keyword_send_status(cluster_name, nmid,  'ItemIsOutOfIndex')
        elif last_position.base_position == 0 and new_position.base_position > 0:
            keyword_send_status: str = await redis_manager.get_keyword_send_status(cluster_name, nmid)
            if keyword_send_status == 'ItemIsInIndex':
                return
            users = await get_users_from_nmid(nmid)
            for user in users:
                try:
                    await messages.ItemIsInIndex(bot,
                                             user.user_telegram_id,
                                             last_position,
                                             new_position)()

                except Exception as exc:
                    logger.error(f'Ошибка при отправке сообщения пользователю {user.username}: {exc}')
            await redis_manager.set_keyword_send_status(cluster_name, nmid,  'ItemIsInIndex')
    except Exception as exc:
        logger.error(f'Ошибка при проверке позиции {exc}', exc_info=True)
        pass


# async def send_about_new_adv(adv, wb_cabinet_id):
#     async with sm() as session:
#         stmt = select(WBCabinet).where(WBCabinet.id == wb_cabinet_id)
#         wb_cabinet: WBCabinet = (await session.execute(stmt)).scalar()
#         users = await data_manager.get_users_from_wb_cabinet(wb_cabinet)
