import pytest

from .common_stat_data_manager import CommonStatDataManager

manager = CommonStatDataManager()


@pytest.mark.asyncio
async def test_get_days_stat_text(adv_setting_mock) -> None:
    last_days = 2
    text = await manager.get_days_static_text(adv_setting_mock, last_days)
    assert isinstance(text, str)
    assert len(text) > 0
    print("\n", text)
