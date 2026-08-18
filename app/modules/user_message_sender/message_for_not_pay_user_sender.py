"""Helpers for sending informational messages to inactive or zero-balance users."""

import asyncio
import logging
import time
from typing import Any

import dotenv

from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet

dotenv.load_dotenv()
from app.client_bot.bot import aclose_telegram_http_session, get_bot
from app.modules.user_message_sender import messages
from app.utils import redis_manager

from sqlalchemy import or_, select
from sqlalchemy.sql.functions import func

from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)

delay = 60 * 60 * 24  # 1 day


async def send_message_to_user(bot: Any, user_telegram_id: int) -> None:
    """Отправить уведомление одному пользователю через Telegram-бота."""
    message = messages.NotAnyUsesAndNotMoneyOnBalance(bot, user_telegram_id)
    logger.debug(f"Отправляю сообщение для {user_telegram_id}")
    await message()


async def send_messages_to_users() -> None:
    all_user_telegram_ids = await get_all_user_telegram_ids_with_not_balance()
    all_user_telegram_ids = list(set(all_user_telegram_ids))
    user_telegram_ids = await get_user_telegram_ids_for_condition(all_user_telegram_ids)
    bot = get_bot()

    try:
        # Цикл для последовательной отправки сообщений
        for user_telegram_id in user_telegram_ids:
            try:
                await send_message_to_user(bot, user_telegram_id)
                logger.debug(
                    f"Отправил сообщение и сбрасываю использование для {user_telegram_id}"
                )
                await redis_manager.reset_last_user_use_time(user_telegram_id)
            except Exception as e:
                logger.error(
                    f"Error sending message to {user_telegram_id}: {e}", exc_info=True
                )
                await redis_manager.reset_last_user_use_time(user_telegram_id)
            await asyncio.sleep(1)  # Если нужно добавить задержку между отправками
    except Exception as e:
        logger.error(f"Error in the process: {e}")
    try:
        await aclose_telegram_http_session()
    except Exception as e:
        logger.error(f"Error closing bot session: {e}")


async def get_user_telegram_ids_for_condition(
    user_telegram_ids: list[int],
) -> list[int]:
    """Оставить пользователей, давно не использовавших бота."""
    last_users_used = await redis_manager.get_last_users_use_time(user_telegram_ids)
    condition_users_ids: list[int] = []
    now = time.time()
    for user_id, last_use_time in zip(user_telegram_ids, last_users_used, strict=False):
        if last_use_time:
            pass_seconds = now - last_use_time
            if pass_seconds > delay:
                condition_users_ids.append(user_id)
    return condition_users_ids


async def get_all_user_telegram_ids_with_not_balance() -> list[int]:
    """Получить Telegram ID пользователей без кабинета или положительного баланса."""
    stmt = (
        select(User.user_telegram_id)
        .outerjoin(User.wb_user_cabinets)
        .outerjoin(WBUserCabinet.wb_cabinet)
        .group_by(User.id)
        .having(
            or_(
                func.count(WBUserCabinet.id) == 0,  # Нет кабинетов
                func.coalesce(func.sum(WBCabinet.balance + WBCabinet.bonus), 0)
                == 0,  # Баланс всех магазинов = 0
            )
        )
    )

    async with sm(read_only=True) as session:
        result = await session.execute(stmt)
        result = result.scalars().all()
        return [user_id for user_id in result if user_id is not None]
