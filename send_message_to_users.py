
from app.admin_bot.sender import sender_manager
import asyncio


async def send_message_to_users():
    await sender_manager.send_to_users_out_channel()



if __name__ == '__main__':

    asyncio.run(send_message_to_users())







