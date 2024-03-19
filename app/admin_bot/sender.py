from .bot_manager import bot



admin_chat_id = 373435337

async def send_message(text: str):
    await bot.send_message(admin_chat_id, text)
