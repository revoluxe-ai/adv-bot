import aiogram
from sqlalchemy import select, and_

from app.utils.db.session_maker import get_async_session_maker
from app.admin_bot.sender.utils.db.models import TelegramFile


_sm = get_async_session_maker()


async def add_file(telegram_file_id: str, dhash: str, bot_id: int):
    async with _sm() as session:
        file = TelegramFile(file_telegram_id=telegram_file_id, dhash=dhash, bot_id=bot_id)
        session.add(file)
        await session.commit()
    return

async def get_telegram_file(dhash, bot: aiogram.Bot):
    bot_id = bot.id
    async with _sm() as session:
        result = await session.execute(
            select(TelegramFile.file_telegram_id).filter(and_(TelegramFile.dhash == dhash,
                                                              TelegramFile.bot_id == bot_id)
        ))
        result = result.scalar_one_or_none()
    return result