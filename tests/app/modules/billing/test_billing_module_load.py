import logging
from unittest.mock import AsyncMock, patch

import pytest

from app.core.di import AppContainer, DIManager
from app.modules.billing import process_payment_for_advs

logging.disable()

@pytest.mark.asyncio
async def test_billing_module_load():
    mock_process = AsyncMock(name="_process_single_cabinet")

    # Важно: путь должен совпадать с тем местом, откуда вызывается функция
    with (patch("app.modules.billing.billing._process_single_cabinet", new=mock_process)):
        async with (await DIManager.create(AppContainer)):
            await process_payment_for_advs()
    mock_process.assert_awaited()