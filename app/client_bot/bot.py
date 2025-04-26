from aiogram import Bot
from dotenv import load_dotenv

from app.settings import settings

load_dotenv()


token = settings.TELEGRAM_BOT_TOKEN

bot = Bot(token=token)


def get_bot() -> Bot:
    return bot
