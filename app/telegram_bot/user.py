from session_maker import get_async_session_maker
from sqlalchemy import select
from .drivers.wb import adverd_manager
from aiogram.types import Message
from .models import User, Token

_sm = get_async_session_maker()



async def get(message: Message):
    class User:
        def __init__(self, tokens: list[Token]):
            self._tokens = tokens



        def





        @property
        cabinets(self):
            return self.__db_user.cabinets











    telegram_user_id = message.from_user.id
    async with _sm() as session:
        stmt = select(User).where(User.user_telegram_id == telegram_user_id)
        result = await session.execute(stmt)
        user = result.scalar()
        if not user:
            user = User(user_telegram_id=telegram_user_id,
                        username=message.from_user.username,
                        tokens=[])
            session.add(user)
            session.commit()
        return User(user)




