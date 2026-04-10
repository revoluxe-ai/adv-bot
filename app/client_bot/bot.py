from aiogram import Bot
from dotenv import load_dotenv

from app.settings import settings
from aiogram.client.session.aiohttp import AiohttpSession

load_dotenv()


session = AiohttpSession(
    proxy="http://xray-client.default.svc.cluster.local:8080",
)


token = settings.TELEGRAM_BOT_TOKEN

bot = Bot(token=token, session=session)


def get_bot() -> Bot:
    return bot
