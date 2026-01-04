import pytest
from unittest.mock import AsyncMock, MagicMock

from aiohttp import ClientSession

from app.modules.wb_adv_updater.wb_manager import update_wb_config_data


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_wb_config_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure update_wb_config_data runs with a provided client session.

    The function under test requires an aiohttp ClientSession.
    In unit tests we stub external dependencies and only verify call flow.
    """

    # Stub dependencies inside wb_manager to avoid real network/redis calls.
    from app.modules.wb_adv_updater import wb_manager

    monkeypatch.setattr(
        wb_manager,
        "super_cabinet_manager",
        MagicMock(
            get_common_access=AsyncMock(return_value=MagicMock()),
        ),
    )

    fake_api = MagicMock(get_min_cpm_adv_data=AsyncMock(return_value=MagicMock()))
    monkeypatch.setattr(wb_manager, "WBAdvAPI", MagicMock(return_value=fake_api))

    monkeypatch.setattr(
        wb_manager,
        "redis_manager",
        MagicMock(set_min_cpm_data=AsyncMock(return_value=None)),
    )

    async with ClientSession() as client_session:
        await update_wb_config_data(client_session)

