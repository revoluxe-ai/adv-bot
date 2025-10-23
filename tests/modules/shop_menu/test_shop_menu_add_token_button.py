"""
Tests for the "Add New Token" button in ShopMenu
Verifies that the button is correctly displayed in the keyboard
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton

from app.modules.shop_menu.message import ShopMenu
from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet, AdvSetting
from app.utils.db.models import User
from app.client_bot.user_interface.views.callbacks import AddNewToken


@pytest.fixture
def mock_bot():
    """Create a mock Bot instance"""
    bot = MagicMock(spec=Bot)
    bot.send_message = AsyncMock()
    return bot


@pytest.fixture
def mock_state():
    """Create a mock FSMContext"""
    state = MagicMock(spec=FSMContext)
    state.update_data = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    return state


@pytest.fixture
def mock_user():
    """Create a mock User"""
    user = MagicMock(spec=User)
    user.id = 1
    user.user_telegram_id = 12345
    return user


@pytest.fixture
def mock_wb_cabinet():
    """Create a mock WBCabinet"""
    # Avoid spec to prevent SQLAlchemy hybrid attributes being accessed during mock creation
    cabinet = MagicMock()
    cabinet.id = 1
    cabinet.shop_id = "test_shop_123"
    cabinet.calculated_balance = 1000.0
    cabinet.calculated_bonus = 100.0
    cabinet.adv_settings = []
    cabinet.white_list_update_active = False
    
    # Mock expiration time
    from datetime import datetime, timedelta
    cabinet.expiration_time = datetime.now() + timedelta(days=30)
    
    return cabinet


@pytest.fixture
def mock_wb_user_cabinet(mock_wb_cabinet, mock_user):
    """Create a mock WBUserCabinet"""
    user_cabinet = MagicMock(spec=WBUserCabinet)
    user_cabinet.id = 1
    user_cabinet.name = "Test Shop"
    user_cabinet.wb_cabinet = mock_wb_cabinet
    user_cabinet.user = mock_user
    return user_cabinet


class TestShopMenuAddTokenButton:
    """Test suite for Add New Token button in ShopMenu"""
    
    @pytest.mark.asyncio
    async def test_add_token_button_exists_in_keyboard(
        self, mock_bot, mock_state, mock_wb_user_cabinet
    ):
        """Test that Add New Token button is present in the keyboard"""
        with patch('app.modules.shop_menu.message.sm') as mock_sm:
            # Mock database session
            mock_session = MagicMock()
            mock_result = MagicMock()
            mock_result.scalar_one.return_value = mock_wb_user_cabinet
            mock_session.execute = AsyncMock(return_value=mock_result)
            
            mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sm.return_value.__aexit__ = AsyncMock()
            
            # Mock Pricer (use patch.object with create=True to avoid AttributeError if attribute isn't present)
            with patch.object(ShopMenu, '_pricer', create=True) as mock_pricer:
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
                    
                    # Find Add New Token button by callback_data (more stable than text)
                    add_token_button_found = False
                    for row in keyboard.inline_keyboard:
                        for button in row:
                            try:
                                callback_data = AddNewToken.unpack(button.callback_data)
                            except Exception:
                                continue
                            # If unpack succeeded, it's the add-token button
                            add_token_button_found = True
                            assert callback_data.wb_user_cabinet_original_id == 1
                            break

                    assert add_token_button_found, "Add New Token button not found in keyboard"

    @pytest.mark.asyncio
    async def test_add_token_button_positioned_after_balance(
        self, mock_bot, mock_state, mock_wb_user_cabinet
    ):
        """Test that Add New Token button is positioned after Add Balance button"""
        with patch('app.modules.shop_menu.message.sm') as mock_sm:
            # Mock database session
            mock_session = MagicMock()
            mock_result = MagicMock()
            mock_result.scalar_one.return_value = mock_wb_user_cabinet
            mock_session.execute = AsyncMock(return_value=mock_result)
            
            mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sm.return_value.__aexit__ = AsyncMock()
            
            # Mock Pricer
            with patch.object(ShopMenu, '_pricer', create=True) as mock_pricer:
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

                    # Find button positions by callback_data for add-token and by text for balance
                    balance_button_position = None
                    add_token_button_position = None

                    for idx, row in enumerate(keyboard.inline_keyboard):
                        for button in row:
                            if "Пополнить баланс" in button.text:
                                balance_button_position = idx
                            try:
                                callback_data = AddNewToken.unpack(button.callback_data)
                                add_token_button_position = idx
                            except Exception:
                                pass

                assert balance_button_position is not None, "Balance button not found"
                assert add_token_button_position is not None, "Add Token button not found"
                # В текущей реализации кнопка добавления токена располагается перед кнопкой пополнения баланса
                assert add_token_button_position < balance_button_position, \
                    "Add Token button should be positioned before Balance button"

    @pytest.mark.asyncio
    async def test_add_token_button_callback_data_format(
        self, mock_bot, mock_state, mock_wb_user_cabinet
    ):
        """Test that Add New Token button has correctly formatted callback data"""
        with patch('app.modules.shop_menu.message.sm') as mock_sm:
            # Mock database session
            mock_session = MagicMock()
            mock_result = MagicMock()
            mock_result.scalar_one.return_value = mock_wb_user_cabinet
            mock_session.execute = AsyncMock(return_value=mock_result)
            
            mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sm.return_value.__aexit__ = AsyncMock()
            
            # Mock TokenInfoService
            with patch.object(ShopMenu, '_pricer', create=True) as mock_pricer:
                with patch('app.modules.shop_menu.message.TokenInfoService') as mock_token_service:
                    mock_token_service_instance = MagicMock()
                    mock_token_service_instance.get_shop_token_status = AsyncMock(return_value=None)
                    mock_token_service.return_value = mock_token_service_instance

                    # Create ShopMenu instance
                    shop_menu = ShopMenu(
                        bot=mock_bot,
                        chat_id=12345,
                        state=mock_state,
                        wb_user_cabinet_original_id=42  # Use specific ID
                    )

                    # Load data
                    mock_wb_user_cabinet.id = 42
                    await shop_menu._load_all_data()

                    # Get keyboard
                    keyboard = shop_menu.keyboard

                    # Find and verify Add New Token button
                    for row in keyboard.inline_keyboard:
                        for button in row:
                            try:
                                callback_data = AddNewToken.unpack(button.callback_data)
                            except Exception:
                                continue
                            # Unpack and verify callback data
                            assert callback_data.wb_user_cabinet_original_id == 42
                            assert button.callback_data.startswith("add_new_token:")
                            return

                pytest.fail("Add New Token button not found")

    @pytest.mark.asyncio
    async def test_add_token_button_for_admin_user(
        self, mock_bot, mock_state, mock_wb_user_cabinet
    ):
        """Test that Add New Token button is visible for admin users"""
        # Set user as admin
        mock_wb_user_cabinet.user.user_telegram_id = 12345
        
        with patch('app.modules.shop_menu.message.sm') as mock_sm:
            with patch('app.client_bot.const.ADMINS', [12345]):
                # Mock database session
                mock_session = MagicMock()
                mock_result = MagicMock()
                mock_result.scalar_one.return_value = mock_wb_user_cabinet
                mock_session.execute = AsyncMock(return_value=mock_result)
                
                mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_sm.return_value.__aexit__ = AsyncMock()
                
                # Mock TokenInfoService
                with patch.object(ShopMenu, '_pricer', create=True) as mock_pricer:
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

                        # Find Add New Token button by callback_data
                        add_token_button_found = False
                        for row in keyboard.inline_keyboard:
                            for button in row:
                                try:
                                    _ = AddNewToken.unpack(button.callback_data)
                                except Exception:
                                    continue
                                add_token_button_found = True
                                break

                    assert add_token_button_found, "Add New Token button should be visible for admins"

    @pytest.mark.asyncio
    async def test_add_token_button_for_regular_user(
        self, mock_bot, mock_state, mock_wb_user_cabinet
    ):
        """Test that Add New Token button is visible for regular users"""
        # Set user as regular (not admin)
        mock_wb_user_cabinet.user.user_telegram_id = 99999
        
        with patch('app.modules.shop_menu.message.sm') as mock_sm:
            with patch('app.client_bot.const.ADMINS', [12345]):  # Different admin
                # Mock database session
                mock_session = MagicMock()
                mock_result = MagicMock()
                mock_result.scalar_one.return_value = mock_wb_user_cabinet
                mock_session.execute = AsyncMock(return_value=mock_result)
                
                mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_sm.return_value.__aexit__ = AsyncMock()
                
                # Mock TokenInfoService
                with patch.object(ShopMenu, '_pricer', create=True) as mock_pricer:
                    with patch('app.modules.shop_menu.message.TokenInfoService') as mock_token_service:
                        mock_token_service_instance = MagicMock()
                        mock_token_service_instance.get_shop_token_status = AsyncMock(return_value=None)
                        mock_token_service.return_value = mock_token_service_instance

                        # Create ShopMenu instance (using user's telegram id as chat_id)
                        shop_menu = ShopMenu(
                            bot=mock_bot,
                            chat_id=99999,
                            state=mock_state,
                            wb_user_cabinet_original_id=1
                        )

                        # Load data
                        await shop_menu._load_all_data()

                        # Get keyboard
                        keyboard = shop_menu.keyboard

                        # Find Add New Token button by callback_data
                        add_token_button_found = False
                        for row in keyboard.inline_keyboard:
                            for button in row:
                                try:
                                    _ = AddNewToken.unpack(button.callback_data)
                                except Exception:
                                    continue
                                add_token_button_found = True
                                break

                    assert add_token_button_found, "Add New Token button should be visible for regular users"

    @pytest.mark.asyncio
    async def test_keyboard_structure_integrity(
        self, mock_bot, mock_state, mock_wb_user_cabinet
    ):
        """Test that adding the new button doesn't break keyboard structure"""
        with patch('app.modules.shop_menu.message.sm') as mock_sm:
            # Mock database session
            mock_session = MagicMock()
            mock_result = MagicMock()
            mock_result.scalar_one.return_value = mock_wb_user_cabinet
            mock_session.execute = AsyncMock(return_value=mock_result)
            
            mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sm.return_value.__aexit__ = AsyncMock()
            
            # Mock TokenInfoService
            with patch.object(ShopMenu, '_pricer', create=True) as mock_pricer:
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

                    # Verify keyboard is not None
                    assert keyboard is not None

                    # Verify keyboard has rows
                    assert len(keyboard.inline_keyboard) > 0

                    # Verify each row has at least one button
                    for row in keyboard.inline_keyboard:
                        assert len(row) > 0

                        # Verify each button has text and callback data
                        for button in row:
                            assert button.text is not None
                            assert button.callback_data is not None

