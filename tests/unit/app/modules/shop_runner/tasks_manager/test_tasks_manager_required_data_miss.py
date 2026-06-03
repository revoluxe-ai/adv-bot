"""Логирование RequiredDataMissError в TasksManager."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.modules.shop_runner.required_data_miss import (
    ShopRunnerKeywordsCacheMissError,
)
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager, run_tasks

MODULE = "app.modules.shop_runner.tasks_manager.tasks_manager"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_worker_logs_required_data_miss_as_warning() -> None:
    async def miss_handler() -> None:
        raise ShopRunnerKeywordsCacheMissError(
            "cache miss shop_id=s adv_id=1",
            shop_id="s",
            adv_id=1,
        )

    manager = TasksManager(max_workers=1)
    manager.start()

    with patch(f"{MODULE}.logger") as mock_logger:
        results = await run_tasks([miss_handler], max_workers=1, tasks_manager=manager)

    await manager.stop()
    assert len(results) == 1
    assert isinstance(results[0], ShopRunnerKeywordsCacheMissError)
    mock_logger.warning.assert_called_once()
    mock_logger.exception.assert_not_called()
