from __future__ import annotations

from typing import AsyncGenerator, AsyncIterator

from sqlalchemy import select
from sqlalchemy.orm import load_only, selectinload

from app.modules.billing.pricer import Pricer
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    WBUserCabinet,
    WBCabinet,
)
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm
from scripts.get_users.get_users import get_users
from scripts.users_csv_exporter.dto import UserDTO

batch_size = 30

# Список Telegram ID пользователей для тестовой рассылки.
TEST_TELEGRAM_IDS: list[int] = [373435337]

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

_pricer = Pricer()


async def get_test_users_iterator() -> AsyncGenerator[UserDTO, None]:
    """
    Напрямую возвращает пользователей с Telegram ID из списка TEST_TELEGRAM_IDS.
    Без использования get_users, get_test_users и прочих обёрток.
    """
    if not TEST_TELEGRAM_IDS:
        return

    stmt = (
        select(User)
        .options(
            load_only(User.id, User.user_telegram_id, User.username),
            *_USER_LOADING_OPTIONS,
        )
        .where(User.user_telegram_id.in_(TEST_TELEGRAM_IDS))
        .order_by(User.id)
    )

    async with sm(read_only=True) as session:
        result = await session.scalars(stmt)
        users = result.unique().all()

    for user in users:
        yield await UserDTO.from_user(user, _pricer, sm)


async def get_users_iterator(
    only_with_auto_campaign: bool = True,
) -> AsyncIterator[UserDTO]:
    get_users_generator = get_users(
        batch_size=batch_size,
        telegram_ids_filter=None,
        only_with_auto_campaign=False,
        balance_more_than_0=False
    )
    return get_users_generator
