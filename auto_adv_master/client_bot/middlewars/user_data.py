from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from auto_adv_master.modules.common_slaves.wildberries.models import WBUserCabinet
from auto_adv_master.utils.db.models import User
from auto_adv_master.utils.db.session_maker import get_async_session_maker

from .. import redis_manager as __redis_manager

_redis_manager = __redis_manager.RedisManager()



_sm = get_async_session_maker()


class UserDataMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]], event: Message, data: Dict[str, Any]) -> Any:
        async with _sm() as session:
            user_telegram_id = event.from_user.id
            stmt = select(User).options(joinedload(User.wb_user_cabinets).joinedload(
                WBUserCabinet.wb_cabinet)) \
                .where(User.user_telegram_id == user_telegram_id)
            result = await session.execute(stmt)
            user = result.scalar()
            if not user:
                user = User(user_telegram_id=user_telegram_id,
                            username=event.from_user.username,
                            wb_tokens=[])
                session.add(user)
                await session.commit()
                await session.refresh(user)
            data['user']: User = user
        return await handler(event, data)
