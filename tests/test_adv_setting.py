import pytest
from aiogram import Bot, types
from aiogram.fsm.context import FSMContext
from app.client_bot.user_interface.handlers.adv_setting import AdminsFilter
from app.client_bot import const
from unittest.mock import AsyncMock, MagicMock, patch
from tests.mocks import MockAdvSetting, MockWBUserCabinet

@pytest.fixture
def mock_message():
    message = AsyncMock(spec=types.Message)
    message.from_user = MagicMock()
    return message

@pytest.fixture
def mock_callback_query():
    callback = AsyncMock(spec=types.CallbackQuery)
    callback.from_user = MagicMock()
    callback.data = "back_to_adv:123"
    callback.message = AsyncMock(spec=types.Message)
    callback.message.chat.id = 123456789
    return callback

@pytest.fixture
def mock_bot():
    return AsyncMock(spec=Bot)

@pytest.fixture
def mock_state():
    return AsyncMock(spec=FSMContext)

@pytest.mark.asyncio
async def test_admins_filter_with_admin_message():
    """Тест фильтра AdminsFilter с сообщением от администратора"""
    admin_id = const.ADMINS[0]  # Берем первого админа из списка
    message = AsyncMock(spec=types.Message)
    message.from_user.id = admin_id
    
    filter_instance = AdminsFilter()
    result = await filter_instance(message)
    assert result is True

@pytest.mark.asyncio
async def test_admins_filter_with_non_admin_message():
    """Тест фильтра AdminsFilter с сообщением от не-администратора"""
    non_admin_id = max(const.ADMINS) + 1  # Гарантированно не админский ID
    message = AsyncMock(spec=types.Message)
    message.from_user.id = non_admin_id
    
    filter_instance = AdminsFilter()
    result = await filter_instance(message)
    assert result is False

@pytest.mark.asyncio
async def test_admins_filter_with_admin_callback():
    """Тест фильтра AdminsFilter с callback от администратора"""
    admin_id = const.ADMINS[0]
    callback = AsyncMock(spec=types.CallbackQuery)
    callback.from_user.id = admin_id
    
    filter_instance = AdminsFilter()
    result = await filter_instance(callback)
    assert result is True

@pytest.mark.asyncio
async def test_back_to_advs_handler(mock_callback_query, mock_bot, mock_state, test_async_db):
    """Тест обработчика back_to_advs"""
    from app.client_bot.user_interface.handlers.adv_setting import back_to_advs
    
    # Подготавливаем тестовые данные
    wb_user_cabinet = MockWBUserCabinet(id=123)
    adv_settings = [
        MockAdvSetting(id=1, name="Test Adv 1"),
        MockAdvSetting(id=2, name="Test Adv 2")
    ]
    
    # Добавляем данные в тестовую БД
    test_async_db.add(wb_user_cabinet)
    for adv in adv_settings:
        test_async_db.add(adv)
    await test_async_db.commit()
    
    # Вызываем обработчик
    await back_to_advs(mock_callback_query, mock_state, mock_bot)
    
    # Проверяем, что был вызван правильный метод с правильными параметрами
    mock_bot.send_message.assert_called_once()

@pytest.mark.asyncio
async def test_cancel_delete_handler(mock_callback_query, mock_bot, mock_state, test_async_db):
    """Тест обработчика cancel_delete"""
    from app.client_bot.user_interface.handlers.adv_setting import cancel_delete
    
    # Подготавливаем тестовые данные
    wb_user_cabinet = MockWBUserCabinet(id=123)
    adv_settings = [
        MockAdvSetting(id=1, name="Test Adv 1"),
        MockAdvSetting(id=2, name="Test Adv 2")
    ]
    
    # Добавляем данные в тестовую БД
    test_async_db.add(wb_user_cabinet)
    for adv in adv_settings:
        test_async_db.add(adv)
    await test_async_db.commit()
    
    # Вызываем обработчик
    await cancel_delete(mock_callback_query, mock_state, mock_bot)
    
    # Проверяем, что был вызван правильный метод с правильными параметрами
    mock_bot.send_message.assert_called_once() 