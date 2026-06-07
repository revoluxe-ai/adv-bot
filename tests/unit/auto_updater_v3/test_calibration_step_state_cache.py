"""Unit: Redis cache for adaptive V3 calibration steps."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_resolver import (
    CalibrationDirect,
    CalibrationStepState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_state_cache import (
    V3CalibrationStepState,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_zero_step_state_is_stored_and_read_as_empty_previous_state() -> None:
    """Zero persisted steps reset calibration history for the next tick."""
    adv = MagicMock()
    adv.adv_id = 42
    cache = V3CalibrationStepState(adv)
    client = AsyncMock()
    client.set = AsyncMock()
    client.get = AsyncMock(return_value="0|loosen")

    with patch.object(type(cache), "_client", new_callable=PropertyMock) as client_prop:
        client_prop.return_value = client
        await cache.set_state(
            CalibrationStepState(
                effective_steps=0,
                direct=CalibrationDirect.LOOSEN,
            )
        )
        state = await cache.get_state()

    client.set.assert_awaited_once_with(cache._key, "0|loosen")
    assert state is None
