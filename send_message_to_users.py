from app.client_bot.utils import data_managers



async def send_message_to_users():
    users = await data_managers.get_all_users()
    for user in users:






