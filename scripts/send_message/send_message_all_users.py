import asyncio
import logging
import os
from hashlib import sha256

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.admin_bot.sender import redis_manager
from app.modules.common_slaves.wildberries.models.models import (
    WBUserCabinet,
)
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm
from scripts.send_message.utils.get_user_with_token_without_balance import \
    iter_users_with_zero_or_negative_balance_without_active_advs
from scripts.send_message.utils.messages import message_1

logger = logging.getLogger(__name__)


USER_TYPE = "user_with_active_company"

test_users_ids = [373435337]

def get_bots() -> list[Bot]:
    tokens_str = os.environ.get("SEND_BOTS_TOKENS")
    # tokens = os.environ.get("SEND_BOTS_TOKENS")
    tokens = tokens_str.split(",")
    bots = [Bot(token=t) for t in tokens]
    return bots


def get_test_bots() -> list[Bot]:
    tokens_str = os.environ.get("TEST_SEND_BOTS_TOKENS")
    # tokens = os.environ.get("SEND_BOTS_TOKENS")
    tokens = tokens_str.split(",")
    bots = [Bot(token=t) for t in tokens]
    return bots




async def get_test_user():
    async with sm() as session:
        stmt = (
            select(User)
            .options(
                selectinload(User.wb_user_cabinets).selectinload(
                    WBUserCabinet.wb_cabinet
                )
            )
            .where(User.user_telegram_id.in_(test_users_ids))
        )
        user = await session.execute(stmt)
        user = user.scalars().all()
    for user in user:
        yield user


async def async_chain(*async_generators):
    for gen in async_generators:
        async for item in gen:
            yield item

redis_semaphore = asyncio.Semaphore(1)


async def send_message(user: User, bot: Bot) -> bool:
    user_id = user.user_telegram_id
    message = message_1.Single_message
    hash_ = sha256(str(message).encode()).hexdigest()

    # фильтр Влада
    if user_id == 1121102685:
        return False

    # проверка в Redis
    if await redis_manager.check_message_send(hash_, user_id, bot.id):
        return False

    try:
        await message(bot, user_id)()
        await redis_manager.set_message_send(hash_, user_id, bot.id)
        return True
    except Exception as e:
        logger.error(e)
        return False

async def send_message_to_users():
    send_count = 0
    not_send_count = 0

    users = iter_users_with_zero_or_negative_balance_without_active_advs()
    bots = get_bots()

    async for user in users:
        for bot in bots:
            ok = await send_message(user, bot)
            if ok:
                send_count += 1
            else:
                not_send_count += 1

            print("Отправлено сообщений:", send_count)
            print("Не отправлено сообщений:", not_send_count)

    # закрываем ботов
    for bot in bots:
        try:
            await bot.session.close()
        except Exception as e:
            logger.error(e)

    # закрываем Redis (пул + сокеты)
    try:
        await redis_manager.close()
    except Exception as e:
        logger.warning(f"Redis close failed: {e}")


if __name__ == "__main__":
    asyncio.run(send_message_to_users())
