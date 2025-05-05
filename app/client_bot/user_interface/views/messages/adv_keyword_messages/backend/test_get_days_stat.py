import pytest
from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm
from .common_stat_data_manager import CommonStatDataManager

manager = CommonStatDataManager()


@pytest.mark.asyncio
async def test_get_days_stat_text() -> None:
    last_days = 2
    test_adv_setting_id = 24916807

    async with sm() as session:
        stmt = select(AdvSetting).where(AdvSetting.adv_id == test_adv_setting_id)
        result = await session.execute(stmt)
        adv_setting = result.scalar_one_or_none()
    assert (
        adv_setting is not None
    ), f"AdvSetting with id {test_adv_setting_id} not found"
    text = await manager.get_days_static_text(adv_setting, last_days)
    assert isinstance(text, str)
    assert len(text) > 0
    print("\n", text)
