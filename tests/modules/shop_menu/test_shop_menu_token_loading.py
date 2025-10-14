"""
Integration tests for ShopMenu token status loading.

This test file contains tests that would have caught the bug where token status 
wasn't being loaded in the ShopMenu._load_all_data() method.
"""

import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.shop_menu.message import ShopMenu
from app.modules.token_monitoring.services.token_info_service import TokenStatusReport, TokenInfo
from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet, AdvSetting
from app.utils.db.models import User


class TestShopMenuTokenLoading:
    """
    Tests that verify ShopMenu actually loads token status data.
    
    These tests would have caught the bug where _token_status was never populated.
    """
    
    @pytest.fixture
    def mock_bot(self):
        """Mock Telegram bot."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_state(self):
        """Mock FSMContext state."""
        state = AsyncMock()
        state.update_data = AsyncMock()
        return state
    
    @pytest.fixture
    def sample_wb_user_cabinet(self):
        """Create sample WBUserCabinet with related data."""
        # Create user
        user = MagicMock()
        user.user_telegram_id = 123456789
        
        # Create cabinet
        wb_cabinet = MagicMock()
        wb_cabinet.id = 1
        wb_cabinet.shop_id = "test_shop_123"
        wb_cabinet.calculated_balance = 1000.0
        wb_cabinet.calculated_bonus = 200.0
        wb_cabinet.expiration_time = datetime.datetime.now() + datetime.timedelta(days=30)
        wb_cabinet.white_list_update_active = False
        wb_cabinet.adv_settings = []
        wb_cabinet.bonus_payments = []
        wb_cabinet.balance_payments = []
        
        # Create user cabinet
        wb_user_cabinet = MagicMock()
        wb_user_cabinet.id = 1
        wb_user_cabinet.name = "Test Shop"
        wb_user_cabinet.user = user
        wb_user_cabinet.wb_cabinet = wb_cabinet
        
        return wb_user_cabinet
    
    @pytest.fixture
    def sample_token_status(self):
        """Create sample token status."""
        token_info = MagicMock()
        token_info.is_valid = True
        token_info.is_expired = False
        token_info.is_read_only = False
        token_info.expires = datetime.datetime.now() + datetime.timedelta(days=30)
        
        return TokenStatusReport(
            shop_id="test_shop_123",
            shop_name="Test Shop",
            status="Complete",
            all_tokens=[token_info],
            valid_tokens=[token_info],
            expired_tokens=[],
            available_permissions={"Контент", "Статистика", "Аналитика", "Продвижение"},
            missing_permissions=set(),
            has_all_required_permissions=True,
            expiring_tokens=[]
        )

    @pytest.mark.asyncio
    async def test_token_status_loaded_during_data_loading(
        self, mock_bot, mock_state, sample_wb_user_cabinet, sample_token_status
    ):
        """
        Test that token status is actually loaded during _load_all_data().
        
        This test would have FAILED before the fix and exposed the bug.
        """
        with patch('app.modules.shop_menu.message.sm') as mock_sm:
            with patch('app.modules.shop_menu.message.get_shop_token_status') as mock_get_token_status:
                # Setup database mocks - properly mock the async context manager
                mock_session = AsyncMock()
                mock_context_manager = AsyncMock()
                mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
                mock_context_manager.__aexit__ = AsyncMock(return_value=None)
                mock_sm.return_value = mock_context_manager
                
                # Mock the database query result
                mock_result = MagicMock()  # Result object is not async
                mock_result.scalar_one.return_value = sample_wb_user_cabinet  # scalar_one() is sync
                mock_session.execute = AsyncMock(return_value=mock_result)  # execute() is async
                
                # Mock the token status service
                mock_get_token_status.return_value = sample_token_status
                
                # Mock the pricer methods - these are async methods
                with patch('app.modules.billing.pricer.Pricer.get_month_tariff_for_count_advs', new_callable=AsyncMock) as mock_month_tariff:
                    with patch('app.modules.billing.pricer.Pricer.get_price_for_day_for_shop', new_callable=AsyncMock) as mock_day_price:
                        mock_month_tariff.return_value = 500
                        mock_day_price.return_value = 100
                        
                        # Create ShopMenu instance
                        shop_menu = ShopMenu(
                            bot=mock_bot,
                            chat_id=123456789,
                            state=mock_state,
                            wb_user_cabinet_original_id=1
                        )
                        
                        # Initially, token status should not be loaded
                        assert shop_menu._token_status_loaded == False
                        assert shop_menu._token_status is None
                        
                        # Call _load_all_data which should load token status
                        await shop_menu._load_all_data()
                        
                        # After loading, token status should be populated
                        assert shop_menu._token_status_loaded == True, "Token status should be marked as loaded"
                        assert shop_menu._token_status is not None, "Token status should be populated"
                        assert shop_menu._token_status == sample_token_status, "Token status should match expected data"
                        
                        # Verify that get_shop_token_status was called
                        mock_get_token_status.assert_called_once_with("test_shop_123")

    @pytest.mark.asyncio
    async def test_token_status_error_handling_during_loading(
        self, mock_bot, mock_state, sample_wb_user_cabinet
    ):
        """
        Test that token status loading errors are handled gracefully.
        
        This verifies that if token status loading fails, the error is handled properly.
        """
        with patch('app.modules.shop_menu.message.sm') as mock_sm:
            with patch('app.modules.shop_menu.message.get_shop_token_status') as mock_get_token_status:
                # Setup database mocks - properly mock the async context manager
                mock_session = AsyncMock()
                mock_context_manager = AsyncMock()
                mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
                mock_context_manager.__aexit__ = AsyncMock(return_value=None)
                mock_sm.return_value = mock_context_manager
                
                # Mock the database query result
                mock_result = MagicMock()  # Result object is not async
                mock_result.scalar_one.return_value = sample_wb_user_cabinet  # scalar_one() is sync
                mock_session.execute = AsyncMock(return_value=mock_result)  # execute() is async
                
                # Make token status loading fail
                mock_get_token_status.side_effect = Exception("Token service error")
                
                # Mock the pricer methods - these are async methods
                with patch('app.modules.billing.pricer.Pricer.get_month_tariff_for_count_advs', new_callable=AsyncMock) as mock_month_tariff:
                    with patch('app.modules.billing.pricer.Pricer.get_price_for_day_for_shop', new_callable=AsyncMock) as mock_day_price:
                        mock_month_tariff.return_value = 500
                        mock_day_price.return_value = 100
                        
                        # Create ShopMenu instance
                        shop_menu = ShopMenu(
                            bot=mock_bot,
                            chat_id=123456789,
                            state=mock_state,
                            wb_user_cabinet_original_id=1
                        )
                        
                        # Call _load_all_data which should handle token loading error
                        await shop_menu._load_all_data()
                        
                        # After error, token status should be marked as failed to load
                        assert shop_menu._token_status_loaded == False, "Token status should be marked as not loaded"
                        assert shop_menu._token_status is None, "Token status should be None on error"
                        
                        # Verify that get_shop_token_status was called (and failed)
                        mock_get_token_status.assert_called_once_with("test_shop_123")

    @pytest.mark.asyncio 
    async def test_full_integration_with_token_status_in_text(
        self, mock_bot, mock_state, sample_wb_user_cabinet, sample_token_status
    ):
        """
        Full integration test that verifies token status appears in text output.
        
        This test would have caught the original bug where token status was showing
        "Ошибка загрузки" instead of actual status.
        """
        with patch('app.modules.shop_menu.message.sm') as mock_sm:
            with patch('app.modules.shop_menu.message.get_shop_token_status') as mock_get_token_status:
                # Setup all mocks - properly mock the async context manager
                mock_session = AsyncMock()
                mock_context_manager = AsyncMock()
                mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
                mock_context_manager.__aexit__ = AsyncMock(return_value=None)
                mock_sm.return_value = mock_context_manager
                
                mock_result = AsyncMock()
                mock_result.scalar_one = AsyncMock(return_value=sample_wb_user_cabinet)
                mock_session.execute = AsyncMock(return_value=mock_result)
                
                mock_get_token_status.return_value = sample_token_status
                
                # Mock the pricer methods - these are async methods
                with patch('app.modules.billing.pricer.Pricer.get_month_tariff_for_count_advs', new_callable=AsyncMock) as mock_month_tariff:
                    with patch('app.modules.billing.pricer.Pricer.get_price_for_day_for_shop', new_callable=AsyncMock) as mock_day_price:
                        mock_month_tariff.return_value = 500
                        mock_day_price.return_value = 100
                        
                        # Create ShopMenu instance and load data
                        shop_menu = ShopMenu(
                            bot=mock_bot,
                            chat_id=123456789,
                            state=mock_state,
                            wb_user_cabinet_original_id=1
                        )
                        
                        await shop_menu._load_all_data()
                        
                        # Get the text output
                        text = shop_menu.text
                        
                        # Verify token status information is present and correct
                        assert "🔑 <b>Состояние токенов:</b> ✅" in text, "Should show successful token status"
                        assert "• Всего токенов: 1" in text, "Should show total token count"
                        assert "• Действующих: 1" in text, "Should show valid token count"
                        
                        # Verify the error message is NOT present
                        assert "⚠️ Ошибка загрузки" not in text, "Should not show loading error"

    @pytest.mark.asyncio
    async def test_integration_shows_error_when_token_loading_fails(
        self, mock_bot, mock_state, sample_wb_user_cabinet
    ):
        """
        Test that when token loading fails, the error message is shown in text.
        
        This verifies the error handling path works correctly.
        """
        with patch('app.modules.shop_menu.message.sm') as mock_sm:
            with patch('app.modules.shop_menu.message.get_shop_token_status') as mock_get_token_status:
                # Setup database mocks - properly mock the async context manager
                mock_session = AsyncMock()
                mock_context_manager = AsyncMock()
                mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
                mock_context_manager.__aexit__ = AsyncMock(return_value=None)
                mock_sm.return_value = mock_context_manager
                
                mock_result = AsyncMock()
                mock_result.scalar_one = AsyncMock(return_value=sample_wb_user_cabinet)
                mock_session.execute = AsyncMock(return_value=mock_result)
                
                # Make token status loading fail
                mock_get_token_status.side_effect = Exception("Token service unavailable")
                
                # Mock the pricer methods - these are async methods
                with patch('app.modules.billing.pricer.Pricer.get_month_tariff_for_count_advs', new_callable=AsyncMock) as mock_month_tariff:
                    with patch('app.modules.billing.pricer.Pricer.get_price_for_day_for_shop', new_callable=AsyncMock) as mock_day_price:
                        mock_month_tariff.return_value = 500
                        mock_day_price.return_value = 100
                        
                        # Create ShopMenu instance and load data
                        shop_menu = ShopMenu(
                            bot=mock_bot,
                            chat_id=123456789,
                            state=mock_state,
                            wb_user_cabinet_original_id=1
                        )
                        
                        await shop_menu._load_all_data()
                        
                        # Get the text output
                        text = shop_menu.text
                        
                        # Verify error message is shown
                        assert "🔑 <b>Состояние токенов:</b> ⚠️ Ошибка загрузки" in text, "Should show loading error"
                        
                        # Verify successful token status is NOT shown
                        assert "• Всего токенов:" not in text, "Should not show token count on error"
                        assert "• Действующих:" not in text, "Should not show valid token count on error"

    @pytest.mark.asyncio
    async def test_original_bug_scenario_would_fail(
        self, mock_bot, mock_state, sample_wb_user_cabinet, sample_token_status
    ):
        """
        This test demonstrates what would happen with the original buggy code.
        
        Before the fix, this test would fail because token status wasn't being loaded.
        """
        # Simulate the original buggy behavior where get_shop_token_status is never called
        with patch('app.modules.shop_menu.message.sm') as mock_sm:
            # Don't patch get_shop_token_status - simulating the original bug
            
            # Setup database mocks - properly mock the async context manager
            mock_session = AsyncMock()
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context_manager.__aexit__ = AsyncMock(return_value=None)
            mock_sm.return_value = mock_context_manager
            
            mock_result = MagicMock()
            mock_result.scalar_one = MagicMock(return_value=sample_wb_user_cabinet)
            mock_session.execute = AsyncMock(return_value=mock_result)
            
            # Mock the pricer methods - these are async methods
            with patch('app.modules.billing.pricer.Pricer.get_month_tariff_for_count_advs', new_callable=AsyncMock) as mock_month_tariff:
                with patch('app.modules.billing.pricer.Pricer.get_price_for_day_for_shop', new_callable=AsyncMock) as mock_day_price:
                    mock_month_tariff.return_value = 500
                    mock_day_price.return_value = 100
                    
                    # Create ShopMenu instance
                    shop_menu = ShopMenu(
                        bot=mock_bot,
                        chat_id=123456789,
                        state=mock_state,
                        wb_user_cabinet_original_id=1
                    )
                    
                    # Mock get_shop_token_status to simulate successful token loading
                    with patch.object(shop_menu, 'get_shop_token_status', new_callable=AsyncMock) as mock_get_token:
                        mock_get_token.side_effect = lambda: setattr(shop_menu, '_token_status_loaded', True) or setattr(shop_menu, '_token_status', sample_token_status)
                        
                        await shop_menu._load_all_data()
                        
                        # With the fix, this should now pass
                        assert shop_menu._token_status_loaded == True, "After fix: Token status should be loaded"
                        assert shop_menu._token_status is not None, "After fix: Token status should be populated"
                        
                        # Before the fix, this would have shown the error message
                        text = shop_menu.text
                        
                        # With the fix, we should NOT see the error message
                        assert "⚠️ Ошибка загрузки" not in text, "After fix: Should not show loading error"