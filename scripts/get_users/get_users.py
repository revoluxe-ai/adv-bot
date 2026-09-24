import asyncio
from typing import AsyncGenerator
from datetime import datetime

from sqlalchemy import exists, or_, select
from sqlalchemy.orm import load_only, selectinload

from app.modules.billing.pricer import Pricer
from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet, WBCabinet
from app.utils.db.session_maker import get_async_session_maker as sm

from app.utils.db.models import User
from scripts.users_csv_exporter.dto import UserDTO

_RESULT_SENTINEL = object()


pricer = Pricer()


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
    .load_only(AdvSetting.id, AdvSetting.bot_active, AdvSetting.nmids),
)

_NEGATIVE_DEFAULT_USER_TELEGRAM_IDS = [
    1121102685,
    707068503,
    261235974,
    373435337,
]


async def _fetch_user_batch(
    batch_size: int,
    last_id: int | None,
    telegram_ids_filter: list[int] | None,
    only_with_auto_campaign: bool = False,
    balance_more_than_0: bool = None,
     without_active_advs: bool =False,
) -> list[User]:
    stmt = (
        select(User)
        .options(
            load_only(User.id, User.user_telegram_id, User.username),
            *_USER_LOADING_OPTIONS,
        )
        .where(User.user_telegram_id.not_in(_NEGATIVE_DEFAULT_USER_TELEGRAM_IDS))
    )
    if telegram_ids_filter:
        stmt = stmt.where(User.user_telegram_id.in_(telegram_ids_filter))
    if last_id is not None:
        stmt = stmt.where(User.id > last_id)
    if only_with_auto_campaign:
        has_auto = exists(
            select(1)
            .select_from(AdvSetting)
            .join(WBCabinet, AdvSetting.wb_cabinet_id == WBCabinet.id)
            .join(WBUserCabinet, WBUserCabinet.wb_cabinet_id == WBCabinet.id)
            .where(
                WBUserCabinet.user_id == User.id,
                AdvSetting.bot_active.is_(True),
                or_(
                    AdvSetting.individual_keywords_target_place_mode.is_(True)
                ),
            )
        )
        stmt = stmt.where(has_auto)

    stmt = stmt.order_by(User.id).limit(batch_size)

    print(
        f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Opening session for get_users batch after id={last_id}"
    )
    async with sm(read_only=True) as session:
        result = await session.scalars(stmt)
        users = result.all()
    print(
        f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Session closed; fetched {len(users)} rows"
    )
    return users


async def get_users(
    batch_size: int,
    telegram_ids_filter: list[int] | None = None,
    only_with_auto_campaign: bool = False,
balance_more_than_0: bool = None,
without_active_advs: bool = True
) -> AsyncGenerator[UserDTO, None]:
    """
    Pull users in batches via short-lived sessions so no cursor stays open too long.
    """

    user_count = 0
    last_id: int | None = None

    while True:
        batch = await _fetch_user_batch(
            batch_size, last_id, telegram_ids_filter, only_with_auto_campaign, balance_more_than_0,
        without_active_advs)
        if not batch:
            break

        for user in batch:
            user_dto = await UserDTO.from_user(user, pricer, sm)
            user_count += 1
            last_id = user.id

            print(
                f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] [{user_count}] Cursor row: user id={user.id}, username={user.username}"
            )
            if balance_more_than_0:
                for cab  in user_dto.cabinets:
                    if cab.balance_plus_bonus > 0:
                        yield user_dto
                        break
            else:
                yield user_dto



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
