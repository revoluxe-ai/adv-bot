"""User iterators for message sending and export scripts."""

from __future__ import annotations

from collections.abc import AsyncGenerator, AsyncIterator

from sqlalchemy import select
from sqlalchemy.orm import load_only

from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm
from scripts.get_users.get_users import get_users
from scripts.users_communicate_module.test_user_cabinets import build_test_user_dto
from scripts.users_csv_exporter.dto import UserDTO

DEFAULT_USER_BATCH_SIZE = 30

# Список Telegram ID пользователей для тестовой рассылки.
TEST_TELEGRAM_IDS: list[int] = [373435337]


async def get_test_users_iterator() -> AsyncGenerator[UserDTO, None]:
    """Yield test users with lightweight mock cabinets.

    Test mode loads only base user fields from the database and then attaches a
    small deterministic set of transient cabinet/campaign models. This avoids
    loading all real shops for heavy accounts and skips expensive tariff and
    ClickHouse calculations.
    """
    if not TEST_TELEGRAM_IDS:
        return

    stmt = (
        select(User)
        .options(load_only(User.id, User.user_telegram_id, User.username))
        .where(User.user_telegram_id.in_(TEST_TELEGRAM_IDS))
        .order_by(User.id)
    )

    async with sm(read_only=True) as session:
        result = await session.scalars(stmt)
        users = result.unique().all()

    for user in users:
        yield build_test_user_dto(user)


async def get_users_iterator(
    *,
    only_with_auto_campaign: bool,
    balance_more_than_0: bool,
    batch_size: int | None = None,
) -> AsyncIterator[UserDTO]:
    """Iterate users from DB in batches (``batch_size`` rows per query; default 30)."""
    effective_batch = (
        batch_size if batch_size is not None else DEFAULT_USER_BATCH_SIZE
    )
    if effective_batch < 1:
        raise ValueError("batch_size must be >= 1")
    get_users_generator = get_users(
        batch_size=effective_batch,
        telegram_ids_filter=None,
        only_with_auto_campaign=only_with_auto_campaign,
        balance_more_than_0=balance_more_than_0,
    )
    return get_users_generator
