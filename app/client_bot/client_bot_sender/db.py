from app.utils.db.session_maker import get_async_session_maker
from .models import TelegramFile


_sm = get_async_session_maker()


async def add_file(telegram_file_id: int, dhash: str):
    async with _sm() as session:
        file = TelegramFile(file_telegram_id=telegram_file_id, dhash=dhash)
        session.add(file)
        await session.commit()


async def get_telegram_file(dhash):
    async with _sm() as session:
        result = await session.execute(
            _sm().query(TelegramFile).filter(TelegramFile.dhash == dhash)
        )
        return result.scalar_one_or_none()