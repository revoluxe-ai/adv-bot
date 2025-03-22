import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.modules.bidder_auto_mode.handlers import on_bidder_for_auto, off_bidder_for_auto
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.client_bot.user_interface.views.callbacks import CPMSettingMenu
from app.client_bot.user_interface.views.messages import CPMSetting
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture
def callback_query():
    mock = AsyncMock()
    mock.message = AsyncMock()
    mock.bot = AsyncMock()
    mock.message.chat.id = 123456789
    return mock

@pytest.fixture
def adv_setting():
    mock = MagicMock(spec=AdvSetting)
    mock.id = 1
    mock.bidder_for_auto = False
    mock.bidder_active = False
    mock.max_place = 1
    mock.max_cpm = 100
    return mock

@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)

@pytest.mark.asyncio
async def test_on_bidder_for_auto(callback_query, adv_setting, mock_session):
    # Arrange
    callback_data = CPMSettingMenu(action="on_bidder_for_auto", adv_original_id=1)

    with patch('app.modules.bidder_auto_mode.handlers.get_async_session_maker') as mock_session_maker, \
         patch('app.modules.bidder_auto_mode.handlers.CPMSetting') as mock_cpm_setting:
        # Setup session mock
        mock_session_maker.return_value.__aenter__.return_value = mock_session
        
        # Setup execute result
        execute_result = MagicMock()
        mock_session.execute.return_value = execute_result

        # Setup CPMSetting mock
        mock_cpm_setting_instance = AsyncMock()
        mock_cpm_setting.return_value = mock_cpm_setting_instance

        # Act
        await on_bidder_for_auto(callback_query, callback_data)

        # Assert
        assert adv_setting.bidder_for_auto is True
        mock_session.commit.assert_awaited_once()
        callback_query.answer.assert_awaited_once_with("Автоматический биддер включен")
        mock_cpm_setting.assert_called_once_with(callback_query.bot, callback_query.message.chat.id)
        mock_cpm_setting_instance.assert_awaited_once_with(callback_data.adv_original_id)

@pytest.mark.asyncio
async def test_off_bidder_for_auto(callback_query, adv_setting, mock_session):
    # Arrange
    callback_data = CPMSettingMenu(action="off_bidder_for_auto", adv_original_id=1)
    adv_setting.bidder_for_auto = True

    with patch('app.modules.bidder_auto_mode.handlers.get_async_session_maker') as mock_session_maker, \
         patch('app.modules.bidder_auto_mode.handlers.CPMSetting') as mock_cpm_setting:
        # Setup session mock
        mock_session_maker.return_value.__aenter__.return_value = mock_session
        
        # Setup execute result
        execute_result = MagicMock()
        mock_session.execute.return_value = execute_result

        # Setup CPMSetting mock
        mock_cpm_setting_instance = AsyncMock()
        mock_cpm_setting.return_value = mock_cpm_setting_instance

        # Act
        await off_bidder_for_auto(callback_query, callback_data)

        # Assert
        assert adv_setting.bidder_for_auto is False
        mock_session.commit.assert_awaited_once()
        callback_query.answer.assert_awaited_once_with("Автоматический биддер выключен")
        mock_cpm_setting.assert_called_once_with(callback_query.bot, callback_query.message.chat.id)
        mock_cpm_setting_instance.assert_awaited_once_with(callback_data.adv_original_id)

@pytest.mark.asyncio
async def test_bidder_not_found(callback_query, mock_session):
    # Arrange
    callback_data = CPMSettingMenu(action="on_bidder_for_auto", adv_original_id=999)

    with patch('app.modules.bidder_auto_mode.handlers.get_async_session_maker') as mock_session_maker:
        # Setup session mock
        mock_session_maker.return_value.__aenter__.return_value = mock_session
        
        # Setup execute result to return None
        execute_result = MagicMock()
        mock_session.execute.return_value = execute_result

        # Act
        await on_bidder_for_auto(callback_query, callback_data)

        # Assert
        mock_session.commit.assert_not_awaited()
        callback_query.answer.assert_awaited_once_with("Рекламная кампания не найдена") 