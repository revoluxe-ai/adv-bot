"""RECORD gate (xfail): keyword stamp должен работать при inactive после loader refactor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.bot_active_gates.helpers import unwrap_coroutine

pytestmark = [pytest.mark.unit, pytest.mark.bot_active_gates, pytest.mark.asyncio]


@pytest.mark.xfail(reason="loader refactor pending: _get_active_advs filters bot_active")
async def test_inactive_adv_included_in_get_complex_advs_for_recording(
    coroutines_manager_gate: MagicMock,
    inactive_complex_adv: MagicMock,
) -> None:
    """Целевой контракт loader: inactive РК попадают в get_complex_advs."""
    manager = coroutines_manager_gate
    real_dm = manager._wb_shop_data_manager
    real_get = real_dm.get_complex_advs
    result = await real_get(load_extras=False)
    assert any(not adv.bot_active for adv in result)


async def test_keyword_stamp_coroutine_does_not_filter_bot_active_when_advs_provided(
    coroutines_manager_gate: MagicMock,
    inactive_complex_adv: MagicMock,
) -> None:
    """Корутина update_keywords_stamp не фильтрует bot_active (RECORD path)."""
    manager = coroutines_manager_gate
    manager._wb_shop_data_manager.get_complex_advs = AsyncMock(
        return_value=[inactive_complex_adv]
    )
    stamp_update = AsyncMock(return_value=None)
    container = MagicMock()
    container.keyword_stamp_manager = MagicMock(
        return_value=MagicMock(update_keywords_position_stamp=stamp_update)
    )

    async def _run_handlers(
        handlers: list[object],
        **_: object,
    ) -> list[None]:
        for handler in handlers:
            await handler()  # type: ignore[misc]
        return [None] * len(handlers)

    with patch(
        "app.modules.shop_runner.service_manager.services.keyword_stamp_manager.KeywordStampManagerContainer",
        return_value=container,
    ), patch(
        "app.modules.shop_runner.service_manager.manager.run_tasks",
        new=AsyncMock(side_effect=_run_handlers),
    ):
        await unwrap_coroutine(manager.update_keywords_stamp)(manager)

    stamp_update.assert_awaited_once()
