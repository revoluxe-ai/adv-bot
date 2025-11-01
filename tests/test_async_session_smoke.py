import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_async_session_smoke(async_session: AsyncSession):
    """Проверяем, что async-сессия реально работает и БД отвечает"""
    result = await async_session.execute(text("SELECT 1"))
    assert result.scalar() == 1