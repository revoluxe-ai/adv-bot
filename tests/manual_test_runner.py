"""
Manual test runner to verify test logic without pytest's conftest issues
Run this directly with: python tests/manual_test_runner.py
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from unittest.mock import AsyncMock, MagicMock, patch


async def test_empty_message_text():
    """Test handler with empty message text - should return early"""
    print("Running: test_empty_message_text...")
    
    from app.client_bot.user_interface.handlers.start.start import process_add_new_token
    
    # Create mocks
    mock_message = MagicMock()
    mock_message.text = None
    mock_message.chat.id = 12345
    mock_message.from_user = MagicMock()
    mock_message.from_user.id = 67890
    
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()
    
    mock_state = MagicMock()
    mock_state.get_data = AsyncMock(return_value={})
    
    # Run handler
    result = await process_add_new_token(mock_message, mock_bot, mock_state)
    
    # Verify
    assert result is None, "Should return None"
    mock_bot.send_message.assert_not_called()
    
    print("✓ test_empty_message_text PASSED")


async def test_start_command_triggers_restart():
    """Test /start command in message triggers registration restart"""
    print("Running: test_start_command_triggers_restart...")
    
    from app.client_bot.user_interface.handlers.start.start import process_add_new_token
    
    # Create mocks
    mock_message = MagicMock()
    mock_message.text = "/start"
    mock_message.chat.id = 12345
    mock_message.from_user = MagicMock()
    mock_message.from_user.id = 67890
    
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()
    
    mock_state = MagicMock()
    mock_state.get_data = AsyncMock(return_value={})
    
    # Run handler with patched start_registration
    with patch('app.client_bot.user_interface.handlers.start.start.start_registration') as mock_start_reg:
        mock_start_reg.return_value = AsyncMock()
        
        await process_add_new_token(mock_message, mock_bot, mock_state)
        
        # Verify
        mock_start_reg.assert_called_once_with(mock_message, mock_bot, mock_state)
    
    print("✓ test_start_command_triggers_restart PASSED")


async def test_missing_cabinet_id_in_state():
    """Test handler when wb_user_cabinet_original_id is missing from state"""
    print("Running: test_missing_cabinet_id_in_state...")
    
    from app.client_bot.user_interface.handlers.start.start import process_add_new_token
    
    # Create mocks
    mock_message = MagicMock()
    mock_message.text = "some_token"
    mock_message.chat.id = 12345
    mock_message.from_user = MagicMock()
    mock_message.from_user.id = 67890
    
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()
    
    mock_state = MagicMock()
    mock_state.get_data = AsyncMock(return_value={})  # Missing cabinet_id
    mock_state.clear = AsyncMock()
    
    # Run handler
    await process_add_new_token(mock_message, mock_bot, mock_state)
    
    # Verify
    mock_bot.send_message.assert_called_once()
    call_args = mock_bot.send_message.call_args
    assert call_args[0][0] == 12345
    assert "Ошибка" in call_args[0][1]
    mock_state.clear.assert_called_once()
    
    print("✓ test_missing_cabinet_id_in_state PASSED")


async def test_invalid_token_format():
    """Test handler with invalid JWT token format"""
    print("Running: test_invalid_token_format...")
    
    from app.client_bot.user_interface.handlers.start.start import process_add_new_token
    from app.core.wb_api.exceptions import NotValidTokenError
    
    # Create mocks
    mock_message = MagicMock()
    mock_message.text = "invalid_token"
    mock_message.chat.id = 12345
    mock_message.from_user = MagicMock()
    mock_message.from_user.id = 67890
    
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()
    
    mock_state = MagicMock()
    mock_state.get_data = AsyncMock(return_value={"wb_user_cabinet_original_id": 1})
    
    # Run handler with patched WBToken
    with patch('app.client_bot.user_interface.handlers.start.start.wb_models.WBToken') as mock_token_class:
        mock_token_instance = MagicMock()
        mock_token_instance.get_shop_id_from_token.side_effect = NotValidTokenError()
        mock_token_class.return_value = mock_token_instance
        
        await process_add_new_token(mock_message, mock_bot, mock_state)
        
        # Verify
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        assert call_args[0][0] == 12345
        assert "не валиден" in call_args[0][1]
    
    print("✓ test_invalid_token_format PASSED")


async def test_shop_menu_has_add_token_button():
    """Test that ShopMenu includes Add New Token button"""
    print("Running: test_shop_menu_has_add_token_button...")
    
    from app.modules.shop_menu.message import ShopMenu
    from app.client_bot.user_interface.views.callbacks import AddNewToken
    
    # Create mocks
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()
    
    mock_state = MagicMock()
    mock_state.update_data = AsyncMock()
    mock_state.get_data = AsyncMock(return_value={})
    
    # Mock WBUserCabinet and WBCabinet
    from datetime import datetime, timedelta
    
    mock_wb_cabinet = MagicMock()
    mock_wb_cabinet.id = 1
    mock_wb_cabinet.shop_id = "test_shop_123"
    mock_wb_cabinet.calculated_balance = 1000.0
    mock_wb_cabinet.calculated_bonus = 100.0
    mock_wb_cabinet.adv_settings = []
    mock_wb_cabinet.white_list_update_active = False
    mock_wb_cabinet.expiration_time = datetime.now() + timedelta(days=30)
    
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.user_telegram_id = 12345
    
    mock_wb_user_cabinet = MagicMock()
    mock_wb_user_cabinet.id = 1
    mock_wb_user_cabinet.name = "Test Shop"
    mock_wb_user_cabinet.wb_cabinet = mock_wb_cabinet
    mock_wb_user_cabinet.user = mock_user
    
    # Patch database and services
    with patch('app.modules.shop_menu.message.sm') as mock_sm:
        # Mock database session
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = mock_wb_user_cabinet
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sm.return_value.__aexit__ = AsyncMock()
        
        # Mock TokenInfoService
        with patch('app.modules.shop_menu.message.TokenInfoService') as mock_token_service:
            mock_token_service_instance = MagicMock()
            mock_token_service_instance.get_shop_token_status = AsyncMock(return_value=None)
            mock_token_service.return_value = mock_token_service_instance
            
            # Create ShopMenu instance
            shop_menu = ShopMenu(
                bot=mock_bot,
                chat_id=12345,
                state=mock_state,
                wb_user_cabinet_original_id=1
            )
            
            # Load data
            await shop_menu._load_all_data()
            
            # Get keyboard
            keyboard = shop_menu.keyboard
            
            # Find Add New Token button
            add_token_button_found = False
            for row in keyboard.inline_keyboard:
                for button in row:
                    if "Добавить токен" in button.text:
                        add_token_button_found = True
                        
                        # Verify callback data
                        callback_data = AddNewToken.unpack(button.callback_data)
                        assert callback_data.wb_user_cabinet_original_id == 1
                        break
            
            assert add_token_button_found, "Add New Token button not found in keyboard"
    
    print("✓ test_shop_menu_has_add_token_button PASSED")


async def main():
    """Run all manual tests"""
    print("\n" + "="*60)
    print("MANUAL TEST RUNNER - Add New Token Feature")
    print("="*60 + "\n")
    
    tests = [
        test_empty_message_text,
        test_start_command_triggers_restart,
        test_missing_cabinet_id_in_state,
        test_invalid_token_format,
        test_shop_menu_has_add_token_button,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"✗ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print(f"Test Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("="*60 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    import os
    
    # Set minimal environment variables (must be done BEFORE any app imports)
    os.environ.setdefault("TELEGRAM_WEB_PORT", "8080")
    os.environ.setdefault("MIN_SUM", "0")
    os.environ.setdefault("BIDDER_STEP_RUB", "1")
    os.environ.setdefault("POSTGRES_PORT", "5432")
    os.environ.setdefault("POSTGRES_USER", "test")
    os.environ.setdefault("POSTGRES_PASSWORD", "test")
    os.environ.setdefault("POSTGRES_DBNAME", "test")
    os.environ.setdefault("POSTGRES_MASTER_HOST", "localhost")
    os.environ.setdefault("POSTGRES_REPLICA_HOST", "localhost")
    os.environ.setdefault("CLICK_HOUSE_HOST", "localhost")
    os.environ.setdefault("CLICKHOUSE_PORT", "9000")
    os.environ.setdefault("CLICKHOUSE_USER", "default")
    os.environ.setdefault("CLICKHOUSE_PASSWORD", "pass")
    os.environ.setdefault("CLICK_HOUSE_USER", "default")
    os.environ.setdefault("CLICK_HOUSE_PASSWORD", "pass")
    os.environ.setdefault("REDIS_MASTER_HOST", "localhost")
    os.environ.setdefault("REDIS_REPLICA_HOST", "localhost")
    os.environ.setdefault("YOOKASSA_TOKEN", "token")
    os.environ.setdefault("WEBHOOK_SECRET", "secret")
    os.environ.setdefault("CH_MAX_THREAD", "10")
    os.environ.setdefault("BOT_TOKEN", "test_token_123")
    
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
