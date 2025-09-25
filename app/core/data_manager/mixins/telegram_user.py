from sqlalchemy import select
from sqlalchemy.orm import load_only

from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm


class TelegramUserMixin:
    @staticmethod
    async def get_telegram_user_model(user_telegram_id: int, load_only_options: list[str] | None = None) -> User:
        stmt = select(User).filter(User.user_telegram_id == user_telegram_id)

        # Если load_only передан, добавляем его в запрос
        if load_only_options:
            loaded_columns = [getattr(User, option) for option in load_only_options]
            stmt = stmt.options(load_only(*loaded_columns))

        async with sm() as session:  # sm() - асинхронный менеджер сессий
            result = await session.execute(stmt)
            user: User = result.scalar_one()

        return user

    @staticmethod
    async def save_phone(user_telegram_id: int, phone_number: str) -> User:
        async with sm(read_only=False) as session:
            stmt = select(User).filter(User.user_telegram_id == user_telegram_id)
            result = await session.execute(stmt)
            user: User = result.scalar_one()
            user.phone = phone_number
            await session.commit()
        return user
