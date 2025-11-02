import pytest

from app.modules.shop_runner.adv_common_parameters.adv_parameter_manager import AdvParameterManager
from app.modules.common_slaves.wildberries.models import AdvSetting


@pytest.fixture
def adv_parameter_manager():
    return AdvParameterManager()


@pytest.mark.asyncio
async def test_get_min_cpm_always_returns_10(adv_parameter_manager):
    adv_setting = AdvSetting()
    result = await adv_parameter_manager.get_min_cpm(adv_setting)
    assert result == 10
