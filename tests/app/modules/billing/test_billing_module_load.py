"""Smoke test for billing module wiring without leaking global logging state."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.di import DIManager

from app.modules.billing import process_payment_for_advs


@pytest.fixture(autouse=True)
def _suppress_billing_logs() -> None:
    """Temporarily silence logs for this module and restore the previous global threshold."""
    previous_disable_level = logging.root.manager.disable
    logging.disable()
    try:
        yield
    finally:
        logging.disable(previous_disable_level)


@pytest.mark.asyncio
async def test_billing_module_load(monkeypatch):
    """Unit-тест: не использует реальную БД (async_session тянет Docker)."""
    from app.core.di.app_container import AppContainer
    monkeypatch.setattr(
        "app.core.di.databases.redis.RedisLifecycle.init",
        AsyncMock(return_value=None),
    )
    mock_process = AsyncMock(name="_process_single_cabinet")
    mock_fetch_active_cabinet_ids = AsyncMock(return_value=[1, 2, 3])

    # Мок для redis_lock - без него acquire_lock() вернёт False и _process_single_cabinet не вызовется
    mock_redis_lock = AsyncMock()
    mock_redis_lock.acquire_lock = AsyncMock(return_value=True)
    mock_redis_lock.release_lock = AsyncMock()

    mock_session = MagicMock(spec_set=["execute", "commit", "close"])
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.close = AsyncMock()

    # Важно: путь должен совпадать с тем местом, откуда вызывается функция
    with (
        patch("app.modules.billing.billing._process_single_cabinet", new=mock_process),
        patch("app.modules.billing.billing._fetch_active_cabinet_ids", new=mock_fetch_active_cabinet_ids),
        patch("app.utils.db.session_maker.get_async_session_maker") as mock_sm_factory,
    ):
        mock_sm_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sm_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        async with await DIManager.create(AppContainer) as container:
            container.module_resources.billing.redis_lock.override(mock_redis_lock)
            await process_payment_for_advs()
    mock_process.assert_awaited()
