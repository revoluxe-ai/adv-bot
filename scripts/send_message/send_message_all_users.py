from __future__ import annotations

import asyncio
import logging
import os
from hashlib import sha256

from collections.abc import AsyncGenerator, AsyncIterable
from typing import Any, AsyncIterator

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.admin_bot.sender import redis_manager
from app.modules.common_slaves.wildberries.models.models import (
    WBUserCabinet,
)
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm
from scripts.get_users.filters.filters import get_users_by_telegram_id, get_test_users
from scripts.send_message.utils.get_users_with_low_balance_and_near_last_payment import \
    get_users_with_low_balance_and_near_last_payment
from scripts.send_message.utils.messages import message_7
from scripts.users_communicate_module.main_user_generator import get_users_iterator, get_test_users_iterator
from scripts.users_csv_exporter.dto import UserDTO

logger = logging.getLogger(__name__)


USER_TYPE = "user_with_active_company"

test_users_ids = [373435337, 707068503]

def get_bots() -> list[Bot]:
    tokens_str = os.environ.get("SEND_BOTS_TOKENS")
    if not tokens_str:
        raise RuntimeError("SEND_BOTS_TOKENS is required")
    tokens = [t for t in tokens_str.split(",") if t]
    return [Bot(token=t) for t in tokens]


def get_test_bots() -> list[Bot]:
    tokens_str = os.environ.get("TEST_SEND_BOTS_TOKENS")
    if not tokens_str:
        raise RuntimeError("TEST_SEND_BOTS_TOKENS is required")
    tokens = [t for t in tokens_str.split(",") if t]
    return [Bot(token=t) for t in tokens]




async def async_chain(
    *async_generators: AsyncIterable[Any],
) -> AsyncGenerator[Any, None]:
    for gen in async_generators:
        async for item in gen:
            yield item

redis_semaphore = asyncio.Semaphore(1)


async def send_message(user: UserDTO, bot: Bot) -> bool:
    user_id = user.telegram_id
    message = message_7.Message
    hash_ = sha256(str(message).encode()).hexdigest()

    # фильтр Влада
    if user_id == 1121102685:
        return False

    # проверка в Redis
    if await redis_manager.check_message_send(hash_, user_id, bot.id):
        return False

    try:
        await message(bot, user)()
        await redis_manager.set_message_send(hash_, user_id, bot.id)
        return True
    except Exception as e:
        logger.error(e)
        raise e





async def send_message_to_users():
    send_count = 0
    not_send_count = 0

    users: AsyncIterator[UserDTO] = await get_users_iterator(
        only_with_auto_campaign=True
    )
    bots = get_bots()
    #
    # bots =  get_test_bots()
    # users = get_test_users_iterator()

    try:
        async for user in users:
            send_flag = False
            for bot in bots:
                try:
                    await send_message(user, bot)
                    send_flag = True
                except Exception as e:
                    logger.error(e)

            if send_flag:
                send_count += 1
            else:
                not_send_count += 1

                print("Отправлено сообщений:", send_count)
                print("Не отправлено сообщений:", not_send_count)
        print(f'Всего отправлено: {send_count}')
        print(f'Общая база рассылки: {not_send_count + send_count}')
    finally:
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
