import asyncio
from typing import AsyncGenerator
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import load_only, selectinload

from app.modules.balance_manager.balance_service import get_cabinet_balance
from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet, WBCabinet
from app.utils.db.session_maker import get_async_session_maker as sm


from app.utils.db.models import User


_RESULT_SENTINEL = object()

_USER_LOADING_OPTIONS = (
    selectinload(User.wb_user_cabinets)
    .load_only(WBUserCabinet.id, WBUserCabinet.name, WBUserCabinet.wb_cabinet_id)
    .selectinload(WBUserCabinet.wb_cabinet)
    .load_only(WBCabinet.id, WBCabinet.shop_id, WBCabinet.balance, WBCabinet.bonus)
    .selectinload(WBCabinet.balance_payments),
    selectinload(User.wb_user_cabinets)
    .load_only(WBUserCabinet.id, WBUserCabinet.name, WBUserCabinet.wb_cabinet_id)
    .selectinload(WBUserCabinet.wb_cabinet)
    .load_only(WBCabinet.id, WBCabinet.shop_id, WBCabinet.balance, WBCabinet.bonus)
    .selectinload(WBCabinet.bonus_payments),
    selectinload(User.wb_user_cabinets)
    .load_only(WBUserCabinet.id, WBUserCabinet.name, WBUserCabinet.wb_cabinet_id)
    .selectinload(WBUserCabinet.wb_cabinet)
    .load_only(WBCabinet.id, WBCabinet.shop_id, WBCabinet.balance, WBCabinet.bonus)
    .selectinload(WBCabinet.adv_settings)
    .load_only(AdvSetting.id, AdvSetting.bot_active),
)

async def get_users(batch_size) -> AsyncGenerator[User, None]:
    """
    Stream users through a single server-side cursor to avoid repeated plans.

    ``stream_results=True`` keeps the cursor open for the duration of the
    generator, and ``yield_per`` batches the rows so the database can control
    flow without replaying ``LIMIT`` + ``OFFSET``.
    """

    stmt = (
        select(User)
        .options(
            load_only(User.id, User.user_telegram_id, User.username),
            *_USER_LOADING_OPTIONS,
        )
        .where(User.id != 43, User.user_telegram_id != 1121102685,
               User.user_telegram_id != 707068503)
        .order_by(User.id)
        .execution_options(stream_results=True)
    )

    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Opening cursor for get_users")
    async with sm(read_only=True) as session:
        stream = await session.stream(stmt)
        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Cursor opened; fetching with batch_size={batch_size}")
        try:
            user_count = 0
            cursor_iter = stream.scalars().yield_per(batch_size)
            async for user in cursor_iter:
                user_count += 1
                print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] [{user_count}] Cursor row: user id={user.id}, username={user.username}")
                yield user
        finally:
            await stream.close()
            print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Cursor closed for get_users")


async def _user_has_target_balance(user: User, max_balance: int) -> bool:
    """
    Fetch all cabinet balances in parallel to avoid serial waits.
    """
    cabinets = [
        wb_user_cabinet.wb_cabinet
        for wb_user_cabinet in user.wb_user_cabinets
        if wb_user_cabinet.wb_cabinet is not None
    ]
    if not cabinets:
        return False

    results = await asyncio.gather(
        *(get_cabinet_balance(cabinet.id) for cabinet in cabinets)
    )

    total_balance = 0
    for balance, bonus in results:
        cabinet_total = balance + bonus
        if cabinet_total >= max_balance:
            return False
        total_balance += cabinet_total

    return total_balance != 0


async def filter_users_for_table(
    users: AsyncGenerator[User, None],
    max_balance: int = 200,
    max_workers: int = 30,
    queue_size: int | None = None,
) -> AsyncGenerator[User, None]:
    """
    Intermediate generator that filters users concurrently via a worker pool.

    Each worker reads users from the shared queue and, if the balance filter
    passes, pushes them into ``result_queue`` so downstream code receives users
    as soon as they finish, while ``batch_size`` still controls the cursor.
    """
    user_queue: asyncio.Queue[User | None] = asyncio.Queue(queue_size or max_workers * 2)
    result_queue: asyncio.Queue[User | object] = asyncio.Queue()

    async def _producer() -> None:
        async for user in users:
            await user_queue.put(user)
        for _ in range(max_workers):
            await user_queue.put(None)

    async def _worker() -> None:
        while True:
            user = await user_queue.get()
            user_queue.task_done()
            if user is None:
                break

            if await _user_has_target_balance(user, max_balance):
                await result_queue.put(user)

    async def _finalize() -> None:
        await producer_task
        await user_queue.join()
        await asyncio.gather(*worker_tasks)
        await result_queue.put(_RESULT_SENTINEL)

    producer_task = asyncio.create_task(_producer())
    worker_tasks = [asyncio.create_task(_worker()) for _ in range(max_workers)]
    finalize_task = asyncio.create_task(_finalize())

    try:
        while True:
            user = await result_queue.get()
            if user is _RESULT_SENTINEL:
                break
            yield user
    finally:
        await finalize_task
