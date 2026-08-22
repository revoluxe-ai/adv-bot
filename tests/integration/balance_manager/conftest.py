import uuid
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.destructive_local
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, async_sessionmaker

from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet


@pytest.fixture(autouse=True)
async def test_session_factory(async_engine: AsyncEngine):
    """Фабрика сессий для интеграционных тестов.

    Патчит `sm` (который является `get_async_session_maker`) в модуле `balance_service`,
    чтобы он использовал тестовый engine.
    """

    async_session_maker = async_sessionmaker(
        async_engine,
        expire_on_commit=False,
    )

    @asynccontextmanager
    async def get_test_session() -> AsyncGenerator[AsyncSession, None]:
        async with async_session_maker() as session:
            yield session

    with patch(
        "app.modules.balance_manager.balance_service.sm",
        get_test_session,
    ), patch(
        "app.modules.balance_manager.handlers.sm",
        get_test_session,
    ), patch(
        "app.modules.balance_manager.user_balance_service.sm",
        get_test_session,
    ):
        yield get_test_session


@pytest.fixture
async def cabinet(async_session: AsyncSession) -> WBCabinet:
    """Изолированный кабинет для integration-тестов."""
    cab = WBCabinet(
        shop_id="test_%s" % uuid.uuid4().hex,
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
    )
    async_session.add(cab)
    await async_session.flush()
    await async_session.refresh(cab)
    return cab



