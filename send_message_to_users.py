from app.client_bot.utils import data_managers
from app.admin_bot.bot_manager import bot
from app.admin_bot.sender import messages
from app.admin_bot.sender import sender_manager
import asyncio


async def send_message_to_users():
    message = messages.AddImageOnApi
    await sender_manager.send_to_all_users(message)



if __name__ == '__main__':

    asyncio.run(send_message_to_users())







