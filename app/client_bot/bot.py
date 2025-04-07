from aiogram import Bot
from app.settings import settings
from dotenv import load_dotenv
load_dotenv()


token = settings.TELEGRAM_BOT_TOKEN

bot = Bot(token=token)




def get_bot():
    bot = Bot(token=token)
    return bot


