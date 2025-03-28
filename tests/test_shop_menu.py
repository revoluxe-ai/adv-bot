import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from aiogram.fsm.context import FSMContext
from app.client_bot.user_interface.views.messages import ShopMenu
from tests.mocks import MockUser, MockWBCabinet, MockWBUserCabinet, MockWBToken, MockAdvSetting
import json
from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet, User, WBToken, AdvSetting
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture
def mock_bot():
    return AsyncMock()

@pytest.fixture
def mock_state():
    return AsyncMock(spec=FSMContext)

@pytest.fixture
def mock_chat_id():
    return 123456789

@pytest.fixture
def mock_wb_token():
    token = MockWBToken()
    token.id = 1
    token.api_key = "test_api_key"
    token.shop_id = "test_shop_id"
    token.active = True
    token.user_id = 1
    return token

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = 1
    user.user_telegram_id = 123456789
    return user

@pytest.fixture
def mock_wb_cabinet():
    cabinet = MagicMock(spec=WBCabinet)
    cabinet.id = 1
    cabinet.shop_id = "test_shop"
    cabinet.balance = 1000
    cabinet.bonus = 100
    return cabinet

@pytest.fixture
def mock_wb_user_cabinet(mock_wb_cabinet, mock_user):
    cabinet = MagicMock(spec=WBUserCabinet)
    cabinet.wb_cabinet = mock_wb_cabinet
    cabinet.user = mock_user
    cabinet.wb_cabinet_id = mock_wb_cabinet.id
    cabinet.user_id = mock_user.id
    cabinet.name = "Test Cabinet"
    return cabinet

@pytest.fixture
def mock_adv_setting(mock_wb_cabinet):
    return AdvSetting(
        id=1,
        adv_id="test_adv_id",
        name="Test Adv",
        wb_cabinet_id=mock_wb_cabinet.id,
        active_status=True,
        bot_active=True,
        nmids=[12345, 67890],
        type="search"
    )

@pytest.fixture
def shop_menu(mock_bot, mock_state, mock_chat_id, mock_wb_user_cabinet):
    return ShopMenu(
        bot=mock_bot,
        chat_id=mock_chat_id,
        state=mock_state,
        wb_user_cabinet_original_id=mock_wb_user_cabinet.id
    )

@pytest.mark.asyncio
async def test_shop_menu_call(shop_menu, mock_wb_user_cabinet, mock_user, mock_wb_cabinet, mock_wb_token, mock_adv_setting, test_async_db):
    # Подготовка тестовых данных
    test_async_db.add(mock_user)
    test_async_db.add(mock_wb_cabinet)
    await test_async_db.commit()
    
    # Устанавливаем отношения между объектами
    mock_wb_user_cabinet.user = mock_user
    mock_wb_user_cabinet.wb_cabinet = mock_wb_cabinet
    mock_wb_user_cabinet.user_id = mock_user.id
    mock_wb_user_cabinet.wb_cabinet_id = mock_wb_cabinet.id
    mock_wb_token.user = mock_user
    mock_wb_token.user_id = mock_user.id
    
    test_async_db.add(mock_wb_user_cabinet)
    test_async_db.add(mock_wb_token)
    test_async_db.add(mock_adv_setting)
    await test_async_db.commit()
    
    # Вызов метода
    await shop_menu()
    
    # Проверка результатов
    assert "Магазин" in shop_menu.text
    assert mock_wb_user_cabinet.name in shop_menu.text
    assert str(mock_wb_user_cabinet.wb_cabinet.balance) in shop_menu.text

@pytest.mark.asyncio
async def test_shop_menu_with_active_advs(shop_menu, mock_wb_user_cabinet, mock_user, mock_wb_cabinet, mock_wb_token, mock_adv_setting, test_async_db):
    # Подготовка тестовых данных
    test_async_db.add(mock_user)
    test_async_db.add(mock_wb_cabinet)
    await test_async_db.commit()
    
    # Устанавливаем отношения между объектами
    mock_wb_user_cabinet.user = mock_user
    mock_wb_user_cabinet.wb_cabinet = mock_wb_cabinet
    mock_wb_user_cabinet.user_id = mock_user.id
    mock_wb_user_cabinet.wb_cabinet_id = mock_wb_cabinet.id
    mock_wb_token.user = mock_user
    mock_wb_token.user_id = mock_user.id
    
    test_async_db.add(mock_wb_user_cabinet)
    test_async_db.add(mock_wb_token)
    test_async_db.add(mock_adv_setting)
    await test_async_db.commit()
    
    # Вызов метода
    await shop_menu()
    
    # Проверка результатов
    assert "Магазин" in shop_menu.text
    assert mock_wb_user_cabinet.name in shop_menu.text
    assert str(mock_wb_user_cabinet.wb_cabinet.balance) in shop_menu.text

@pytest.mark.asyncio
async def test_get_shop_menu(mock_wb_user_cabinet, test_async_db):
    shop_menu = ShopMenu()
    menu_text = await shop_menu.get_shop_menu(mock_wb_user_cabinet)
    
    assert "🏪 Меню магазина" in menu_text
    assert "test_shop" in menu_text
    assert "💰 Баланс: 1000.0" in menu_text
    assert "🎁 Бонус: 100.0" in menu_text

@pytest.mark.asyncio
async def test_get_adv_menu(mock_wb_user_cabinet, mock_adv_setting, test_async_db):
    shop_menu = ShopMenu()
    menu_text = await shop_menu.get_adv_menu(mock_wb_user_cabinet)
    
    assert "📊 Меню рекламных кампаний" in menu_text
    assert "Test Adv" in menu_text
    assert "✅ Активна" in menu_text

@pytest.mark.asyncio
async def test_get_adv_menu_no_advs(mock_wb_user_cabinet, test_async_db):
    shop_menu = ShopMenu()
    menu_text = await shop_menu.get_adv_menu(mock_wb_user_cabinet)
    
    assert "📊 Меню рекламных кампаний" in menu_text
    assert "У вас пока нет рекламных кампаний" in menu_text

@pytest.mark.asyncio
async def test_get_adv_menu_with_error(mock_wb_user_cabinet, test_async_db):
    shop_menu = ShopMenu()
    
    # Симулируем ошибку при получении данных
    with patch("app.client_bot.user_interface.views.shop_menu.get_async_session_maker") as mock_session:
        mock_session.side_effect = Exception("Database Error")
        
        with pytest.raises(Exception) as exc_info:
            await shop_menu.get_adv_menu(mock_wb_user_cabinet)
        assert str(exc_info.value) == "Database Error"

@pytest.mark.asyncio
async def test_shop_menu_call():
    # Mock data
    mock_message = AsyncMock()
    mock_state = AsyncMock()
    
    # Test handler
    from app.client_bot.user_interface.handlers.shop_menu import shop_menu_call
    await shop_menu_call(mock_message, mock_state)
    
    # Verify
    mock_message.answer.assert_called_once()
    mock_state.set_state.assert_called_once()

@pytest.mark.asyncio
async def test_shop_menu_with_active_advs(test_async_db):
    async with test_async_db as session:
        # Create test data
        wb_cabinet = WBCabinet(
            id=1,
            shop_id="test_shop",
            balance=1000,
            bonus=100,
            expiration_time="2024-01-01",
            active=True
        )
        await session.merge(wb_cabinet)
        
        user = User(
            id=1,
            user_telegram_id=123456789,
            username="test_user"
        )
        session.add(user)
        
        wb_user_cabinet = WBUserCabinet(
            id=1,
            wb_cabinet_id=wb_cabinet.id,
            user_id=user.id,
            name="Test Cabinet"
        )
        session.add(wb_user_cabinet)
        
        adv_setting = AdvSetting(
            adv_id=123,
            name="Test Adv",
            wb_cabinet_id=wb_cabinet.id,
            active_status="active",
            bot_active=True
        )
        session.add(adv_setting)
        await session.commit()
        
        # Create menu instance
        menu = ShopMenu(session)
        
        # Get menu text
        menu_text = await menu.get_shop_menu(wb_user_cabinet.id)
        
        # Verify
        assert "Test Cabinet" in menu_text
        assert "1000" in menu_text
        assert "100" in menu_text

@pytest.mark.asyncio
async def test_get_shop_menu(test_async_db):
    async with test_async_db as session:
        # Create test data
        wb_cabinet = WBCabinet(
            id=1,
            shop_id="test_shop",
            balance=1000,
            bonus=100,
            expiration_time="2024-01-01",
            active=True
        )
        await session.merge(wb_cabinet)
        
        user = User(
            id=1,
            user_telegram_id=123456789,
            username="test_user"
        )
        session.add(user)
        
        wb_user_cabinet = WBUserCabinet(
            id=1,
            wb_cabinet_id=wb_cabinet.id,
            user_id=user.id,
            name="Test Cabinet"
        )
        session.add(wb_user_cabinet)
        await session.commit()
        
        # Create menu instance
        menu = ShopMenu(session)
        
        # Get menu text
        menu_text = await menu.get_shop_menu(wb_user_cabinet.id)
        
        # Verify
        assert "Test Cabinet" in menu_text
        assert "1000" in menu_text
        assert "100" in menu_text

@pytest.mark.asyncio
async def test_get_adv_menu(test_async_db):
    async with test_async_db as session:
        # Create test data
        wb_cabinet = WBCabinet(
            id=1,
            shop_id="test_shop",
            balance=1000,
            bonus=100,
            expiration_time="2024-01-01",
            active=True
        )
        await session.merge(wb_cabinet)
        
        adv_setting = AdvSetting(
            adv_id=123,
            name="Test Adv",
            wb_cabinet_id=wb_cabinet.id,
            active_status="active",
            bot_active=True
        )
        session.add(adv_setting)
        await session.commit()
        
        # Create menu instance
        menu = ShopMenu(session)
        
        # Get menu text
        menu_text = await menu.get_adv_menu(wb_cabinet.id)
        
        # Verify
        assert "Test Adv" in menu_text
        assert "active" in menu_text.lower()

@pytest.mark.asyncio
async def test_get_adv_menu_no_advs(test_async_db):
    async with test_async_db as session:
        # Create test data
        wb_cabinet = WBCabinet(
            id=1,
            shop_id="test_shop",
            balance=1000,
            bonus=100,
            expiration_time="2024-01-01",
            active=True
        )
        await session.merge(wb_cabinet)
        await session.commit()
        
        # Create menu instance
        menu = ShopMenu(session)
        
        # Get menu text
        menu_text = await menu.get_adv_menu(wb_cabinet.id)
        
        # Verify
        assert "No active advertisements" in menu_text

@pytest.mark.asyncio
async def test_get_adv_menu_with_error(test_async_db):
    async with test_async_db as session:
        # Create menu instance with error-raising mock session
        menu = ShopMenu(AsyncMock())
        menu.session.execute.side_effect = Exception("Database Error")
        
        # Get menu text should raise exception
        with pytest.raises(Exception) as exc_info:
            await menu.get_adv_menu(1)
        
        assert str(exc_info.value) == "Database Error"