import pytest
from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.modules.adv_common_parameters_manager.adv_parameter_manager import (
    AdvParameterManager,
)
from app.utils.db.session_maker import get_async_session_maker as sm

adv_param_manager = AdvParameterManager()


@pytest.mark.asyncio(loop_scope="session")
async def test_get_min_cpm_from_redis():
    stmt = select(AdvSetting).where(AdvSetting.adv_id == 25040169)
    async with sm() as session:
        result = await session.execute(stmt)
        adv_setting = result.scalar_one()

    cpm = await adv_param_manager.get_min_cpm(adv_setting)
    print(cpm)
    assert isinstance(cpm, int)
