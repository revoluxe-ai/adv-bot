"""Mock-only regression checks for the manual-strategy PG child seam."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.client_bot.user_interface.handlers.strategy_setting import (
    set_manual_strategy_in_session,
)
from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy


@pytest.mark.unit
@pytest.mark.asyncio
async def test_manual_strategy_child_mutates_loaded_entity() -> None:
    """Child changes only the loaded ORM entity; parent owns commit."""
    adv_setting = SimpleNamespace(auto_update_strategy=False, strategy=None)
    session = SimpleNamespace(get=AsyncMock(return_value=adv_setting))

    selected = await set_manual_strategy_in_session(session, 7, Strategy.OPTIMUM.value)

    assert selected is Strategy.OPTIMUM
    assert adv_setting.strategy is Strategy.OPTIMUM
    session.get.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_manual_strategy_child_rejects_auto_mode() -> None:
    """Auto mode remains a protected boundary for manual writes."""
    adv_setting = SimpleNamespace(auto_update_strategy=True, strategy=None)
    session = SimpleNamespace(get=AsyncMock(return_value=adv_setting))

    with pytest.raises(RuntimeError, match="отключите авто"):
        await set_manual_strategy_in_session(session, 7, Strategy.OPTIMUM.value)

    assert adv_setting.strategy is None
