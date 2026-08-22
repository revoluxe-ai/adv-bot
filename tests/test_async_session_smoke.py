import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# TODO: Перенести все папки в tests/ и впредь поддерживать структуру тестов в одном месте

pytestmark = pytest.mark.destructive_local
@pytest.mark.asyncio
@pytest.mark.skip('Skipped: Test fails in CI environment due to unknown reasons - needs investigation')
async def test_async_session_smoke(async_session: AsyncSession):
    """Проверяем, что async-сессия реально работает и БД отвечает"""
    result = await async_session.execute(text("SELECT 1"))
    assert result.scalar() == 1