"""Unit tests for filtering minus-phrase background sync by dedicated flag."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.manager import CoroutinesManager


pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def test_update_minus_phrases_uses_dedicated_flag_not_white_list() -> None:
    manager = CoroutinesManager.__new__(CoroutinesManager)
    manager._wb_manager_hub = SimpleNamespace()
    manager._tasks_manager = MagicMock()
    manager._wb_shop_data_manager = SimpleNamespace(
        get_complex_advs=AsyncMock(
            return_value=[
                SimpleNamespace(
                    adv_id=1,
                    shop_id="shop-1",
                    bot_active=True,
                    auto_update_minus_phrases=False,
                    auto_update_white_list=True,
                    card_ab_hold_mode=None,
                ),
                SimpleNamespace(
                    adv_id=2,
                    shop_id="shop-1",
                    bot_active=True,
                    auto_update_minus_phrases=True,
                    auto_update_white_list=False,
                    card_ab_hold_mode=None,
                ),
            ]
        )
    )
    manager._max_workers_for = MagicMock(return_value=1)

    minus_phrase_manager = SimpleNamespace(
        update_minus_phrases=AsyncMock(return_value=None)
    )

    async def _run_tasks(
        handlers,
        max_workers,
        tasks_manager,
    ):
        return [await handler() for handler in handlers]

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.minus_phrase_manager.MinusPhraseManagerContainer",
            MagicMock(return_value=SimpleNamespace(minus_phrase_manager=lambda: minus_phrase_manager)),
        ),
        patch(
            "app.modules.shop_runner.service_manager.manager.run_tasks",
            new=AsyncMock(side_effect=_run_tasks),
        ),
    ):
        await manager.update_minus_phrases_in_advs.__wrapped__(  # type: ignore[attr-defined]
            manager,
            only_bot_active=False,
        )

    manager._wb_shop_data_manager.get_complex_advs.assert_awaited_once_with(
        load_extras=False,
        only_bot_active=False,
    )
    minus_phrase_manager.update_minus_phrases.assert_awaited_once()
    handled_adv = minus_phrase_manager.update_minus_phrases.await_args.args[0]
    assert handled_adv.adv_id == 2
