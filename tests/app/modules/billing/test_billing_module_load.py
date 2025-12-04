import logging
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.di import DIManager
from app.core.di.app_container import AppContainer
from app.modules.billing import process_payment_for_advs

logging.disable()


@pytest.mark.asyncio
async def test_billing_module_load(async_session: AsyncSession):
    mock_process = AsyncMock(name="_process_single_cabinet")
    mock_fetch_active_cabinet_ids = AsyncMock(return_value=[1, 2, 3])

    # Мок для redis_lock - без него acquire_lock() вернёт False и _process_single_cabinet не вызовется
    mock_redis_lock = AsyncMock()
    mock_redis_lock.acquire_lock = AsyncMock(return_value=True)
    mock_redis_lock.release_lock = AsyncMock()

    # Важно: путь должен совпадать с тем местом, откуда вызывается функция
    with (
        patch("app.modules.billing.billing._process_single_cabinet", new=mock_process),
        patch("app.modules.billing.billing._fetch_active_cabinet_ids", new=mock_fetch_active_cabinet_ids),
        patch("app.utils.db.session_maker.get_async_session_maker") as mock_sm_factory,
    ):
        mock_sm_factory.return_value.__aenter__.return_value = async_session
        mock_sm_factory.return_value.__aexit__.return_value = None
        async with await DIManager.create(AppContainer) as container:
            container.module_resources.billing.redis_lock.override(mock_redis_lock)
            await process_payment_for_advs()
    mock_process.assert_awaited()
