import pytest
from app.client_bot.user_interface.handlers.adv_setting import _update_and_get_adv_setting
from app.modules.common_slaves.wildberries.models import AdvSetting
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import AdvSettingFactory


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_and_get_adv_setting_success(async_session: AsyncSession):
    # Arrange
    adv_setting = AdvSettingFactory.build(id=1,
                                          auto_update_minus_phrases=False)
    async_session.add(adv_setting)
    await async_session.commit()

    # Act
    updated_adv_setting = await _update_and_get_adv_setting(async_session, new_status=True, adv_setting_original_id=1)

    # Assert
    assert updated_adv_setting.auto_update_minus_phrases is True


@pytest.mark.asyncio
async def test_update_and_get_adv_setting_not_found(async_session: AsyncSession):
    # Act & Assert
    with pytest.raises(RuntimeError, match="AdvSetting not found for original_id=999"):
        await _update_and_get_adv_setting(async_session, new_status=True, adv_setting_original_id=999)


@pytest.mark.asyncio
async def test_update_and_get_adv_setting_commit_failure(async_session: AsyncSession, mocker):
    # Arrange
    adv_setting = AdvSetting(id=2, auto_update_minus_phrases=False)
    async_session.add(adv_setting)
    await async_session.commit()

    mocker.patch.object(async_session, "commit",
                        side_effect=IntegrityError("Mocked Commit Error", params=None, orig=None))

    # Act & Assert
    with pytest.raises(IntegrityError):
        await _update_and_get_adv_setting(async_session, new_status=True, adv_setting_original_id=2)
