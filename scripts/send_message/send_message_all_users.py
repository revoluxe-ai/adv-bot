"""Queue-based Telegram broadcast sender for all selected users.

The script streams users from an async iterator into an ``asyncio.Queue`` and
flushes queued users in batches. Each batch is sent concurrently for up to 50
users via ``asyncio.gather`` while preserving per-user bot fallback behavior.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from hashlib import sha256

from aiogram import Bot

from app.admin_bot.sender import redis_manager
from app.client_bot.bot import aclose_telegram_http_session, get_bots_for_tokens
from scripts.send_message.utils.messages import message_11
from scripts.users_communicate_module.main_user_generator import (
    get_test_users_iterator,
    get_users_iterator,
)
from scripts.users_csv_exporter.dto import UserDTO

logger = logging.getLogger(__name__)

SEND_BATCH_SIZE = 1
QUEUE_MAX_SIZE = 1000
QUEUE_SENTINEL = object()

TEST_MODE = False
DRY_RUN_MODE =  False


def get_bots() -> list[Bot]:
    """Build sender bots from production token list."""
    tokens_str = os.environ.get("SEND_BOTS_TOKENS")
    if not tokens_str:
        raise RuntimeError("SEND_BOTS_TOKENS is required")
    tokens = [t for t in tokens_str.split(",") if t]
    return get_bots_for_tokens(tokens)


def get_test_bots() -> list[Bot]:
    """Build sender bots from test token list."""
    tokens_str = os.environ.get("TEST_SEND_BOTS_TOKENS")
    if not tokens_str:
        raise RuntimeError("TEST_SEND_BOTS_TOKENS is required")
    tokens = [t for t in tokens_str.split(",") if t]
    return get_bots_for_tokens(tokens)


async def send_message(user: UserDTO, bot: Bot) -> bool:
    """Send the configured broadcast to one user through one bot."""
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
    except Exception as exc:
        logger.error(exc)
        raise


async def send_message_with_fallback(user: UserDTO, bots: list[Bot]) -> bool:
    """Try all configured bots for one user until one send succeeds."""
    for bot in bots:
        try:
            is_sent = await send_message(user, bot)
        except Exception as exc:
            logger.error(exc)
            continue
        if is_sent:
            return True
    return False


async def produce_users(
    users: AsyncIterator[UserDTO],
    queue: asyncio.Queue[UserDTO | object],
) -> None:
    """Push users from the source iterator into the queue and finish with a sentinel."""
    try:
        async for user in users:
            await queue.put(user)
    finally:
        await queue.put(QUEUE_SENTINEL)


async def process_user_batch(batch: list[UserDTO], bots: list[Bot]) -> tuple[int, int]:
    """Send one queued batch concurrently and return sent/not-sent counters."""
    results = await asyncio.gather(
        *(send_message_with_fallback(user, bots) for user in batch),
        return_exceptions=True,
    )
    sent_count = 0
    not_sent_count = 0
    for result in results:
        if isinstance(result, Exception):
            logger.error(result)
            not_sent_count += 1
            continue
        if result:
            sent_count += 1
        else:
            not_sent_count += 1
    return sent_count, not_sent_count


async def consume_user_queue(
    queue: asyncio.Queue[UserDTO | object],
    bots: list[Bot],
) -> tuple[int, int]:
    """Read queued users, flush them in batches of 50, and aggregate counters."""
    send_count = 0
    not_send_count = 0
    batch: list[UserDTO] = []

    while True:
        item = await queue.get()
        try:
            if item is QUEUE_SENTINEL:
                if batch:
                    sent, not_sent = await process_user_batch(batch, bots)
                    send_count += sent
                    not_send_count += not_sent
                return send_count, not_send_count

            batch.append(item)
            if len(batch) >= SEND_BATCH_SIZE:
                sent, not_sent = await process_user_batch(batch, bots)
                send_count += sent
                not_send_count += not_sent
                batch = []
        finally:
            queue.task_done()


async def send_message_to_users() -> None:
    """Run the full queue-based broadcast workflow."""
    if not TEST_MODE:
        users: AsyncIterator[UserDTO] = await get_users_iterator(
            only_with_auto_campaign=False,
            balance_more_than_0=False,
        )
        bots = get_bots()
    else:
        bots = get_test_bots()
        users = get_test_users_iterator()

    queue: asyncio.Queue[UserDTO | object] = asyncio.Queue(maxsize=QUEUE_MAX_SIZE)

    try:
        producer_task = asyncio.create_task(produce_users(users, queue))
        consumer_task = asyncio.create_task(consume_user_queue(queue, bots))

        try:
            await producer_task
            await queue.join()
            send_count, not_send_count = await consumer_task
        except Exception:
            producer_task.cancel()
            consumer_task.cancel()
            await asyncio.gather(producer_task, consumer_task)
            raise

        print(f'Всего отправлено: {send_count}')
        print(f'Общая база рассылки: {not_send_count + send_count}')
    finally:
        try:
            await aclose_telegram_http_session()
        except Exception as exc:
            logger.error(exc)

        # закрываем Redis (пул + сокеты)
        try:
            await redis_manager.close()
        except Exception as exc:
            logger.warning("Redis close failed: %s", exc)


if __name__ == "__main__":
    asyncio.run(send_message_to_users())
