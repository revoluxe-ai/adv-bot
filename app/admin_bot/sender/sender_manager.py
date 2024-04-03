import aiogram
from aiogram.exceptions import TelegramForbiddenError

from app.client_bot.client_bot import bot
from . import messages
from app.client_bot.user_interface.message_templates.base import Base as MessageTemplate
from app.client_bot.utils import data_managers
import asyncio
from app.admin_bot.sender import redis_manager
from hashlib import sha256
import logging

from python_modules.logger import setup_logging



setup_logging()

logger = logging.getLogger(__name__)

admin_chat_id = 373435337

test_user_ids = [352225040, 5378020690]



async def send_to_all_users(message):
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




