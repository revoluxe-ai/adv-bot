"""Conftest for onboarding integration tests: patch sm and get_shop_ids_with_complete_token_status."""

from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.destructive_local
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet


class MockSessionMaker:
    """Mock session maker for handlers to use test session."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def __call__(self, read_only: bool = False) -> "MockSessionMaker":
        return self

    async def __aenter__(self) -> AsyncSession:
        return self.session

    async def __aexit__(self, *args: object) -> None:
        pass


@pytest.fixture(autouse=True)
def patch_start_and_token_services(async_session: AsyncSession):
    """Patch sm in start module and get_shop_ids_with_complete_token_status."""
    mock_sm = MockSessionMaker(async_session)
    with patch(
        "app.client_bot.user_interface.handlers.start.start.sm",
        mock_sm,
    ), patch(
        "app.client_bot.user_interface.handlers.start.start.get_shop_ids_with_complete_token_status",
        new=AsyncMock(return_value=set()),
    ):
        yield


@pytest.fixture
async def cabinet(async_session: AsyncSession) -> WBCabinet:
    """Create a test WBCabinet."""
    import uuid

    cab = WBCabinet(
        shop_id=f"test_{uuid.uuid4().hex}",
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
    )
    async_session.add(cab)
    await async_session.flush()
    await async_session.refresh(cab)
    return cab
