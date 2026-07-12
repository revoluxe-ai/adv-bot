"""Gate: minus phrases не обновляются при bot_active=False."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.bot_active_gates.helpers import unwrap_coroutine

pytestmark = [pytest.mark.unit, pytest.mark.bot_active_gates, pytest.mark.asyncio]


async def test_minus_phrases_skipped_when_bot_inactive(
    coroutines_manager_gate: MagicMock,
    inactive_complex_adv: MagicMock,
) -> None:
    manager = coroutines_manager_gate
    manager._wb_shop_data_manager.get_complex_advs = AsyncMock(
        return_value=[inactive_complex_adv]
    )
    minus_mock = AsyncMock()
    container = MagicMock()
    container.minus_phrase_manager = MagicMock(return_value=MagicMock(update_minus_phrases=minus_mock))

    with patch(
        "app.modules.shop_runner.service_manager.services.minus_phrase_manager.MinusPhraseManagerContainer",
        return_value=container,
    ):
        await unwrap_coroutine(manager.update_minus_phrases_in_advs)(manager)

    minus_mock.assert_not_called()
