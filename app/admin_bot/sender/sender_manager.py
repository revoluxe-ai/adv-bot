from app.admin_bot.bot_manager import bot
from . import messages
from app.client_bot.user_interface.message_templates.base import Base as MessageTemplate
from app.client_bot.client_bot import bot



admin_chat_id = 373435337


async def send_to_all_users(message: MessageTemplate):
    message = message()





async def send_message(text: str):
    await bot.send_message(admin_chat_id, text











async def send_message(text: str):
    await bot.send_message(admin_chat_id, text)

