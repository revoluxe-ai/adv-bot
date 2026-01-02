import asyncio
import logging
import os
from hashlib import sha256

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.admin_bot.sender import redis_manager
from scripts.send_message import single_messages
from app.modules.common_slaves.wildberries.models.models import (
    WBUserCabinet,
)
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm


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

async def send_message(user: User, bot: Bot, send_count: int, not_send_count: int) -> None:
    user_id = user.user_telegram_id
    message = single_messages.Single_message
    hash_ = sha256((str(message)).encode()).hexdigest()
    if await redis_manager.check_message_send(hash_, user_id, bot.id):
        return None
    if user_id == 1121102685:  # фильтруем Влада
        return None
    try:
        await message(bot, user_id)()
        await redis_manager.set_message_send(hash_, user_id, bot.id)
        send_count += 1
    except Exception as e:
        logger.error(e)
        not_send_count += 1
    print("Отправлено сообщений: ", send_count)
    print("Не отправлено сообщений: ", not_send_count)

async def send_message_to_users():
    send_count = 0
    not_send_count = 0
    users = get_users()
    # users = get_test_user()
    # chain = async_chain(admin_users, users)
    send_tasks = []
    bots = get_bots()
    async for user in users:
       for bot in bots:
           send_tasks.append(send_message(user, bot, send_count, not_send_count))

    await asyncio.gather(*send_tasks)
    try:
        _ = [await bot.session.close() for bot in bots]
    except Exception as e:
        logger.warning(f"Bot session close failed: {e}")

    try:
        await redis_manager.close()
    except Exception as e:
        logger.warning(f"Redis close failed: {e}")


if __name__ == "__main__":
    asyncio.run(send_message_to_users())
