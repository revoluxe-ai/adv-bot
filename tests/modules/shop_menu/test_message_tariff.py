import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timedelta
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.settings.settings_master import Settings

from app.modules.shop_menu.message import ShopMenu
from app.utils.db.models import User
from app.modules.billing.pricer.pricer import Pricer


class TestTariffCalculation:
    @pytest.fixture
    def mock_bot(self):
        return AsyncMock()

    @pytest.fixture
    def mock_state(self):
        state = AsyncMock()
        state.update_data = AsyncMock()
        return state

    @pytest.fixture
    def sample_user(self):
        user = MagicMock(spec=User)
        user.user_telegram_id = 123456789
        return user

    @pytest.fixture
    def sample_wb_cabinet(self, sample_user):
        wb_cabinet = MagicMock()
        wb_cabinet.id = 1
        wb_cabinet.shop_id = "test_shop_123"
        wb_cabinet.user = sample_user # Add user to wb_cabinet mock
        
        # Mock adv_settings as an empty list by default
        wb_cabinet.adv_settings = []
        
        # Add other necessary attributes for _load_all_data
        wb_cabinet.calculated_balance = 1000.0
        wb_cabinet.calculated_bonus = 100.0
        wb_cabinet.expiration_time = datetime.now() + timedelta(days=30)

        return wb_cabinet

    @pytest.fixture
    def sample_wb_user_cabinet(self, sample_user, sample_wb_cabinet):
        wb_user_cabinet = MagicMock()
        wb_user_cabinet.id = 1
        wb_user_cabinet.name = "Test Shop"
        wb_user_cabinet.user = sample_user
        wb_user_cabinet.wb_cabinet = sample_wb_cabinet # Ensure wb_cabinet is nested correctly
        return wb_user_cabinet

    @pytest.fixture
    def mock_pricer(self):
        pricer = AsyncMock()
        pricer.get_month_tariff_for_count_advs.return_value = 1500
        pricer.get_price_for_day_for_shop.return_value = 50
        return pricer

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def sample_shop_menu(self, mock_bot, mock_state, sample_wb_user_cabinet, mock_pricer, sample_wb_cabinet):
        shop_menu = ShopMenu(
            bot=mock_bot,
            chat_id=sample_wb_user_cabinet.user.user_telegram_id,
            state=mock_state,
            wb_user_cabinet_original_id=sample_wb_user_cabinet.id
        )
        # _wb_user_cabinet and _wb_cabinet are loaded inside _load_all_data
        # We should NOT set them directly here, but ensure they are mocked correctly when fetched from DB
        shop_menu._pricer = mock_pricer
        # Mocking get_shop_token_status to prevent actual token loading during tariff tests
        shop_menu.get_shop_token_status = AsyncMock()
        return shop_menu

    @pytest.mark.asyncio
    async def test_get_tariff_info_active_advs(self, sample_shop_menu, mock_pricer, sample_wb_user_cabinet, sample_wb_cabinet):
        """Test tariff calculation when is_active_adv is True."""
        # Create a mock for AdvSetting objects and add to wb_cabinet
        mock_adv_setting = MagicMock()
        mock_adv_setting.id = 1
        mock_adv_setting.bot_active = True
        sample_wb_cabinet.adv_settings = [mock_adv_setting]

        with patch('app.modules.shop_menu.message.sm') as mock_sm:
            mock_session = AsyncMock()
            mock_sm.return_value.__aenter__.return_value = mock_session

            # Mock the DB query for WBUserCabinet and WBCabinet
            mock_result = MagicMock()
            mock_result.scalar_one.return_value = sample_wb_user_cabinet # Use scalar_one()
            mock_session.execute.return_value = mock_result

            result = await sample_shop_menu._load_all_data()

            assert result is True
            assert sample_shop_menu.is_active_adv is True
            assert sample_shop_menu.price_for_month_for_shop == 1500
            assert sample_shop_menu.total_amount_for_day == 50
            mock_pricer.get_month_tariff_for_count_advs.assert_called_once_with(mock_session, "test_shop_123")
            mock_pricer.get_price_for_day_for_shop.assert_called_once_with(mock_session, "test_shop_123")

    @pytest.mark.asyncio
    async def test_get_tariff_info_inactive_advs(self, sample_shop_menu, mock_pricer, sample_wb_user_cabinet, sample_wb_cabinet):
        """Test tariff calculation when is_active_adv is False."""
        # Ensure no active adv_settings
        sample_wb_cabinet.adv_settings = []

        with patch('app.modules.shop_menu.message.sm') as mock_sm:
            mock_session = AsyncMock()
            mock_sm.return_value.__aenter__.return_value = mock_session

            # Mock the DB query for WBUserCabinet and WBCabinet
            mock_result = MagicMock()
            mock_result.scalar_one.return_value = sample_wb_user_cabinet # Use scalar_one()
            mock_session.execute.return_value = mock_result

            result = await sample_shop_menu._load_all_data()

            assert result is True
            assert sample_shop_menu.is_active_adv is False
            assert sample_shop_menu.price_for_month_for_shop == 0
            assert sample_shop_menu.total_amount_for_day == 0
            mock_pricer.get_month_tariff_for_count_advs.assert_not_called()
            mock_pricer.get_price_for_day_for_shop.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_tariff_info_pricer_exception(self, sample_shop_menu, mock_pricer, sample_wb_user_cabinet, sample_wb_cabinet):
        """Test tariff calculation when _pricer methods raise an exception."""
        # Create a mock for AdvSetting objects and add to wb_cabinet to make is_active_adv True
        mock_adv_setting = MagicMock()
        mock_adv_setting.id = 1
        mock_adv_setting.bot_active = True
        sample_wb_cabinet.adv_settings = [mock_adv_setting]

        mock_pricer.get_month_tariff_for_count_advs.side_effect = Exception("Test exception")

        with patch('app.modules.shop_menu.message.sm') as mock_sm:
            mock_session = AsyncMock()
            mock_sm.return_value.__aenter__.return_value = mock_session

            # Mock the DB query for WBUserCabinet and WBCabinet
            mock_result = MagicMock()
            mock_result.scalar_one.return_value = sample_wb_user_cabinet # Use scalar_one()
            mock_session.execute.return_value = mock_result

            with pytest.raises(Exception, match="Test exception"):
                await sample_shop_menu._load_all_data()

            mock_pricer.get_month_tariff_for_count_advs.assert_called_once()
            # If the first call raises, the second should not be called
            mock_pricer.get_price_for_day_for_shop.assert_not_called()

    @pytest.fixture
    def mock_settings(self):
        with patch('app.settings.settings_master.Settings') as MockSettings:
            instance = MockSettings.return_value
            instance.WHITE_LIST_AUTO_UPDATER_MONTH_TARIFF = 2500
            instance.AUTO_UPDATE_TARGET_PLACE_MONTH_TARIFF = 2500
            yield instance

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "num_active_advs, num_white_list_auto_updater, num_autoupdate_target_place, expected_month_tariff, expected_day_tariff",
        [
            (5, 4, 4, 26495, 883.17),
            (1, 0, 0, 1699, 56.63),
        ]
    )
    async def test_pricer_calculations(
        self,
        mock_session,
        mock_settings,
        num_active_advs,
        num_white_list_auto_updater,
        num_autoupdate_target_place,
        expected_month_tariff,
        expected_day_tariff
    ):
        """Test Pricer's tariff calculations with various campaign configurations."""
        # Mock methods that return counts
        with patch.object(Pricer, 'get_advs_count', new_callable=AsyncMock) as mock_get_advs_count, \
             patch.object(Pricer, '_get_month_tariff_for_white_list_updater', new_callable=AsyncMock) as mock_get_white_list_tariff, \
             patch.object(Pricer, '_get_month_tariff_for_autoupdate_target_place', new_callable=AsyncMock) as mock_get_target_place_tariff:

            mock_get_advs_count.return_value = num_active_advs
            mock_get_white_list_tariff.return_value = num_white_list_auto_updater * mock_settings.WHITE_LIST_AUTO_UPDATER_MONTH_TARIFF
            mock_get_target_place_tariff.return_value = num_autoupdate_target_place * mock_settings.AUTO_UPDATE_TARGET_PLACE_MONTH_TARIFF

            pricer = Pricer()
            shop_id = "test_shop_123"

            month_tariff = await pricer.get_month_tariff_for_count_advs(mock_session, shop_id)
            day_tariff = await pricer.get_price_for_day_for_shop(mock_session, shop_id)

            assert month_tariff == expected_month_tariff
            assert day_tariff == expected_day_tariff

            mock_get_advs_count.assert_has_calls([call(mock_session, shop_id), call(mock_session, shop_id)])
            mock_get_white_list_tariff.assert_has_calls([call(mock_session, shop_id), call(mock_session, shop_id)])
            mock_get_target_place_tariff.assert_has_calls([call(mock_session, shop_id), call(mock_session, shop_id)])
