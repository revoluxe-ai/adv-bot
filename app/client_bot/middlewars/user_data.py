from collections.abc import Awaitable, Callable
from typing import Any, cast

from aiogram import BaseMiddleware
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

from .. import redis_manager as __redis_manager


_redis_manager = __redis_manager.RedisManager()


_sm = get_async_session_maker


class UserDataMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,  # type: ignore
        data: dict[str, Any],
    ) -> Any:
        async with _sm(read_only=False) as session:
            assert event.from_user is not None
            user_telegram_id = event.from_user.id
            stmt = (
                select(User)
                .options(joinedload(User.wb_user_cabinets).joinedload(WBUserCabinet.wb_cabinet))
                .where(User.user_telegram_id == user_telegram_id)
            )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if not user:
                user = User()
                user.user_telegram_id = user_telegram_id
                user.username = event.from_user.username
                session.add(user)
                await session.commit()
                await session.refresh(user)
            data["user"] = user
        return await handler(event, data)
