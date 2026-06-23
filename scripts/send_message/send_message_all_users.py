from __future__ import annotations

import asyncio
import logging
import os
from hashlib import sha256

from collections.abc import AsyncGenerator, AsyncIterable, AsyncIterator
from typing import Any

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.admin_bot.sender import redis_manager
from app.client_bot.bot import aclose_telegram_http_session, get_bots_for_tokens

from scripts.send_message.utils.messages import message_11
from scripts.users_communicate_module.main_user_generator import get_users_iterator, get_test_users_iterator
from scripts.users_csv_exporter.dto import UserDTO

logger = logging.getLogger(__name__)


USER_TYPE = "user_with_active_company"

test_users_ids = [373435337, 707068503]

def get_bots():
    tokens_str = os.environ.get("SEND_BOTS_TOKENS")
    if not tokens_str:
        raise RuntimeError("SEND_BOTS_TOKENS is required")
    tokens = [t for t in tokens_str.split(",") if t]
    return get_bots_for_tokens(tokens)


def get_test_bots():
    tokens_str = os.environ.get("TEST_SEND_BOTS_TOKENS")
    if not tokens_str:
        raise RuntimeError("TEST_SEND_BOTS_TOKENS is required")
    tokens = [t for t in tokens_str.split(",") if t]
    return get_bots_for_tokens(tokens)




async def async_chain(
    *async_generators: AsyncIterable[Any],
) -> AsyncGenerator[Any, None]:
    for gen in async_generators:
        async for item in gen:
            yield item

redis_semaphore = asyncio.Semaphore(1)

TEST_MODE = True
DRY_RUN_MODE = False




async def send_message(user: UserDTO, bot: Bot) -> bool:
    user_id = user.telegram_id
    message = message_11.Message
    hash_ = sha256(str(message).encode()).hexdigest()

    # фильтр Влада
    if user_id == 1121102685:
        return False
    if not TEST_MODE or DRY_RUN_MODE:
        if await redis_manager.check_message_send(hash_, user_id, bot.id):
            return False

    try:
        if not DRY_RUN_MODE:
            await message(bot, user)()
        else:
            print('Имитация отправки: ', user.telegram_id)
        if not TEST_MODE or DRY_RUN_MODE:
            await redis_manager.set_message_send(hash_, user_id, bot.id)
        return True
    except Exception as e:
        logger.error(e)
        raise e





async def send_message_to_users():
    send_count = 0
    not_send_count = 0
    if not TEST_MODE:
        users: AsyncIterator[UserDTO] = await get_users_iterator(
            only_with_auto_campaign=False,
            balance_more_than_0=False
        )
        bots = get_bots()
    #
    else:
        bots =  get_test_bots()
        users = get_test_users_iterator()

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
        try:
            await aclose_telegram_http_session()
        except Exception as e:
            logger.error(e)

        # закрываем Redis (пул + сокеты)
        try:
            await redis_manager.close()
        except Exception as e:
            logger.warning(f"Redis close failed: {e}")


if __name__ == "__main__":
    asyncio.run(send_message_to_users())
