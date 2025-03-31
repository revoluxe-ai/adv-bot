import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from aiogram.fsm.context import FSMContext
from app.client_bot.user_interface.views.messages import ShopMenu
from tests.mocks import MockUser, MockWBCabinet, MockWBUserCabinet, MockWBToken, MockAdvSetting
import json

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
    user = MockUser()
    user.id = 1
    user.user_telegram_id = 123456789
    return user

@pytest.fixture
def mock_wb_cabinet():
    cabinet = MockWBCabinet()
    cabinet.id = 1
    cabinet.shop_id = "test_shop_id"
    cabinet.balance = 1000
    cabinet.bonus = 500
    cabinet.expiration_time = datetime.now() + timedelta(days=30)
    cabinet.active = True
    return cabinet

@pytest.fixture
def mock_wb_user_cabinet(mock_user, mock_wb_cabinet):
    cabinet = MockWBUserCabinet()
    cabinet.id = 1
    cabinet.wb_cabinet_id = mock_wb_cabinet.id
    cabinet.user_id = mock_user.id
    cabinet.name = "Test Cabinet"
    cabinet.wb_cabinet = mock_wb_cabinet
    cabinet.user = mock_user
    return cabinet

@pytest.fixture
def mock_adv_setting(mock_wb_cabinet):
    adv_setting = MockAdvSetting()
    adv_setting.id = 1
    adv_setting.adv_id = "test_adv_id"
    adv_setting.name = "Test Adv"
    adv_setting.wb_cabinet_id = mock_wb_cabinet.id
    adv_setting.active_status = True
    adv_setting.bot_active = True
    adv_setting.nmids = json.dumps([12345, 67890])
    adv_setting.type = "search"
    return adv_setting

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
    
    # Пересоздаем ShopMenu с теми же параметрами,
    # чтобы использовать новый патч для get_async_session_maker
    updated_shop_menu = ShopMenu(
        bot=shop_menu.bot,
        chat_id=shop_menu.chat_id,
        state=shop_menu._state,
        wb_user_cabinet_original_id=mock_wb_user_cabinet.id
    )
    
    # Вызов метода
    await updated_shop_menu()
    
    # Проверка результатов
    assert "Магазин" in updated_shop_menu.text
    assert mock_wb_user_cabinet.name in updated_shop_menu.text
    assert str(mock_wb_user_cabinet.wb_cabinet.balance) in updated_shop_menu.text

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
    
    # Пересоздаем ShopMenu с теми же параметрами,
    # чтобы использовать новый патч для get_async_session_maker
    updated_shop_menu = ShopMenu(
        bot=shop_menu.bot,
        chat_id=shop_menu.chat_id,
        state=shop_menu._state,
        wb_user_cabinet_original_id=mock_wb_user_cabinet.id
    )
    
    # Вызов метода
    await updated_shop_menu()
    
    # Проверка результатов
    assert "Магазин" in updated_shop_menu.text
    assert mock_wb_user_cabinet.name in updated_shop_menu.text
    assert str(mock_wb_user_cabinet.wb_cabinet.balance) in updated_shop_menu.text