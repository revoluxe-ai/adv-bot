from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from app.modules.shop_runner.service_manager.old_modules.adv_common_parameters_manager.adv_parameter_manager import (
    AdvParameterManager,
)

adv_param_manager = AdvParameterManager()


@pytest.mark.asyncio
async def test_get_min_cpm_from_redis(adv_setting_mock):

    result_mock = MagicMock()
    result_mock.scalar_one.return_value = "Юбки"
    session_mock = MagicMock()
    session_mock.execute = AsyncMock(return_value=result_mock)
    session_maker_mock = MagicMock()
    session_maker_mock.__aenter__ = AsyncMock(return_value=session_mock)

    get_session_maker_mock = MagicMock(return_value=session_maker_mock)

    redis_manager_mock = MagicMock()
    redis_manager_mock.get_min_cpm_by_category_name = AsyncMock(return_value=150)

    with (
        patch(
            "app.modules.shop_runner.modules.adv_common_parameters_manager.adv_parameter_manager.sm",
            new=get_session_maker_mock,
        ),
        patch(
            "app.modules.shop_runner.modules.adv_common_parameters_manager.adv_parameter_manager.redis_manager",
            new=redis_manager_mock,
        ),
    ):
        cpm = await adv_param_manager.get_min_cpm(adv_setting_mock)
    print(cpm)
    assert isinstance(cpm, int)
