import aiogram
from aiogram.exceptions import TelegramForbiddenError
from .utils import utils
from app.client_bot.client_bot import bot
from . import messages
from app.client_bot.user_interface.message_templates.base import Base as MessageTemplate
from app.client_bot.utils import data_managers
import asyncio
from app.admin_bot.sender import redis_manager
from hashlib import sha256
import logging
from app.client_bot import const
from python_modules.logger import setup_logging
from . import messages


setup_logging()

logger = logging.getLogger(__name__)

admin_chat_id = 373435337

test_user_ids = [5378020690, 373435337]



message = messages.NewFeaturesInBot


async def send_to_users_out_channel():
    users = await data_managers.get_all_users()
    # users = [user for user in users if user.user_telegram_id in test_user_ids]
    hash = sha256(str(message).encode()).hexdigest()
    for user in users:
        if await redis_manager.check_message_send(hash, user.user_telegram_id):
            logger.info(f'Сообщение уже отправлено пользователю {user.username}')
            continue
        user_id = user.user_telegram_id
        try:
            check = await utils.check_user_in_support_channel(bot, user_id)
        except aiogram.exceptions.TelegramBadRequest as e:
            logger.error(f'Ошибка при проверке пользователя {user.username} в канале поддержки {e}')
            continue
        if not check:
            try:
                await messages.NewFeaturesInBot(bot, user_id)()
                await redis_manager.set_message_send(hash, user_id)
                await asyncio.sleep(1)

            except TelegramForbiddenError:
                logger.error(f'Пользователь {user.username} заблокировал бота')

            finally:
                http_session = bot.session
                if http_session:
                    await http_session.close()







async def send_to_all_users():
    users = await data_managers.get_all_users()
    # users = [user for user in users if user.user_telegram_id in test_user_ids]
    hash = sha256(str(message).encode()).hexdigest()
    for user in users:
       if await redis_manager.check_message_send(hash, user.user_telegram_id):
           continue
       else:
           try:
               all_shops = await data_managers.get_all_shops_for_user(user)
               await message(bot, user.user_telegram_id, all_shops)()
           except Exception as e:
               logger.error(f'Error while sending message to user {e}')

           await redis_manager.set_message_send(hash, user.user_telegram_id)
           await asyncio.sleep(5)


async def send_message(text: str):
    await bot.send_message(admin_chat_id, text)




