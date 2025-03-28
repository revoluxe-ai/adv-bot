import pytest
from aiogram import Bot, types
from aiogram.fsm.context import FSMContext
from app.client_bot.user_interface.handlers.adv_setting import AdminsFilter, CallbackStartsWithFilter, back_to_advs, cancel_delete
from app.client_bot import const
from unittest.mock import AsyncMock, MagicMock, patch
from tests.mocks import MockAdvSetting, MockWBUserCabinet, MockWBCabinet
from sqlalchemy import select
from sqlalchemy.future import select
from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet, User, WBToken, AdvSetting
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture
def mock_message():
    message = AsyncMock(spec=types.Message)
    message.from_user = MagicMock()
    message.from_user.id = 123456789
    message.chat = MagicMock()
    message.chat.id = 123456789
    return message

@pytest.fixture
def mock_callback_query():
    callback = AsyncMock(spec=types.CallbackQuery)
    callback.from_user = MagicMock()
    callback.from_user.id = 123456789
    callback.data = "back_to_adv:123"
    callback.message = AsyncMock(spec=types.Message)
    callback.message.chat = MagicMock()
    callback.message.chat.id = 123456789
    return callback

@pytest.fixture
def mock_bot():
    return AsyncMock(spec=Bot)

@pytest.fixture
def mock_state():
    return AsyncMock(spec=FSMContext)

@pytest.fixture
def mock_wb_cabinet():
    return MagicMock(spec=WBCabinet, id=1, shop_id="test_shop")

@pytest.fixture
def mock_user():
    return MagicMock(spec=User, id=1)

@pytest.fixture
def mock_wb_user_cabinet(mock_wb_cabinet, mock_user):
    cabinet = MagicMock(spec=WBUserCabinet)
    cabinet.wb_cabinet = mock_wb_cabinet
    cabinet.user = mock_user
    cabinet.wb_cabinet_id = mock_wb_cabinet.id
    cabinet.user_id = mock_user.id
    return cabinet

@pytest.fixture
def mock_adv_setting():
    return MagicMock(spec=AdvSetting, id=1, adv_id=123, name="test_adv")

@pytest.mark.asyncio
async def test_admins_filter_with_admin_message():
    """Тест фильтра AdminsFilter с сообщением от администратора"""
    admin_id = const.ADMINS[0]  # Берем первого админа из списка
    message = AsyncMock(spec=types.Message)
    message.from_user = MagicMock()
    message.from_user.id = admin_id
    
    filter_instance = AdminsFilter()
    result = await filter_instance(message)
    assert result is True

@pytest.mark.asyncio
async def test_admins_filter_with_non_admin_message():
    """Тест фильтра AdminsFilter с сообщением от не-администратора"""
    non_admin_id = max(const.ADMINS) + 1  # Гарантированно не админский ID
    message = AsyncMock(spec=types.Message)
    message.from_user = MagicMock()
    message.from_user.id = non_admin_id
    
    filter_instance = AdminsFilter()
    result = await filter_instance(message)
    assert result is False

@pytest.mark.asyncio
async def test_admins_filter_with_admin_callback():
    """Тест фильтра AdminsFilter с callback от администратора"""
    admin_id = const.ADMINS[0]
    callback = AsyncMock(spec=types.CallbackQuery)
    callback.from_user = MagicMock()
    callback.from_user.id = admin_id
    
    filter_instance = AdminsFilter()
    result = await filter_instance(callback)
    assert result is True

@pytest.mark.asyncio
async def test_callback_starts_with_filter_matching():
    """Тест CallbackStartsWithFilter с совпадающим префиксом"""
    callback = AsyncMock(spec=types.CallbackQuery)
    callback.data = "prefix_test:data"
    
    filter_instance = CallbackStartsWithFilter(prefix="prefix_")
    result = await filter_instance(callback)
    assert result is True

@pytest.mark.asyncio
async def test_callback_starts_with_filter_not_matching():
    """Тест CallbackStartsWithFilter с несовпадающим префиксом"""
    callback = AsyncMock(spec=types.CallbackQuery)
    callback.data = "different:data"
    
    filter_instance = CallbackStartsWithFilter(prefix="prefix_")
    result = await filter_instance(callback)
    assert result is False

@pytest.mark.asyncio
async def test_callback_starts_with_filter_empty_data():
    """Тест CallbackStartsWithFilter с пустыми данными"""
    callback = AsyncMock(spec=types.CallbackQuery)
    callback.data = None
    
    filter_instance = CallbackStartsWithFilter(prefix="prefix_")
    result = await filter_instance(callback)
    assert result is False

@pytest.mark.asyncio
async def test_back_to_advs_handler_simple(mock_callback_query, mock_bot, mock_state, test_async_db):
    """Тест обработчика back_to_advs"""
    # Подготавливаем тестовые данные
    wb_cabinet = MockWBCabinet(id=1, shop_id="test_shop", active=True)
    wb_user_cabinet = MockWBUserCabinet(id=123, wb_cabinet_id=1, user_id=1, name="Test Cabinet")
    adv_settings = [
        MockAdvSetting(id=1, name="Test Adv 1", wb_cabinet_id=1),
        MockAdvSetting(id=2, name="Test Adv 2", wb_cabinet_id=1)
    ]
    
    # Добавляем данные в тестовую БД
    test_async_db.add(wb_cabinet)
    test_async_db.add(wb_user_cabinet)
    for adv in adv_settings:
        test_async_db.add(adv)
    await test_async_db.commit()
    
    # Настраиваем mock_callback_query
    mock_callback_query.from_user.id = const.ADMINS[0]  # ID админа
    
    # Создаем мок для результата запроса
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None
    
    # Настраиваем цепочку моков для имитации результата запроса
    mock_scalar_result = AsyncMock()
    mock_scalar_result.all = AsyncMock(return_value=adv_settings)
    
    mock_execute_result = AsyncMock()
    mock_execute_result.scalars.return_value = mock_scalar_result
    
    # Устанавливаем, что результат выполнения запроса будет mock_execute_result
    mock_session.execute = AsyncMock(return_value=mock_execute_result)
    
    # Патчим session_maker чтобы возвращал наш мок-сессии
    with patch('app.client_bot.user_interface.handlers.adv_setting.sm', return_value=mock_session):
        # Вызываем обработчик
        await back_to_advs(mock_callback_query, mock_state, mock_bot)
    
    # Проверяем, что был вызван правильный метод с правильными параметрами
    mock_bot.send_message.assert_called_once()

@pytest.mark.asyncio
async def test_cancel_delete_handler_simple(mock_callback_query, mock_bot, mock_state, test_async_db):
    """Тест обработчика cancel_delete"""
    # Подготавливаем тестовые данные
    wb_cabinet = MockWBCabinet(id=1, shop_id="test_shop", active=True)
    wb_user_cabinet = MockWBUserCabinet(id=123, wb_cabinet_id=1, user_id=1, name="Test Cabinet")
    adv_settings = [
        MockAdvSetting(id=1, name="Test Adv 1", wb_cabinet_id=1),
        MockAdvSetting(id=2, name="Test Adv 2", wb_cabinet_id=1)
    ]
    
    # Добавляем данные в тестовую БД
    test_async_db.add(wb_cabinet)
    test_async_db.add(wb_user_cabinet)
    for adv in adv_settings:
        test_async_db.add(adv)
    await test_async_db.commit()
    
    # Настраиваем mock_callback_query
    mock_callback_query.from_user.id = const.ADMINS[0]  # ID админа
    
    # Создаем мок для результата запроса
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None
    
    # Настраиваем цепочку моков для имитации результата запроса
    mock_scalar_result = AsyncMock()
    mock_scalar_result.all = AsyncMock(return_value=adv_settings)
    
    mock_execute_result = AsyncMock()
    mock_execute_result.scalars.return_value = mock_scalar_result
    
    # Устанавливаем, что результат выполнения запроса будет mock_execute_result
    mock_session.execute = AsyncMock(return_value=mock_execute_result)
    
    # Патчим session_maker чтобы возвращал наш мок-сессии
    with patch('app.client_bot.user_interface.handlers.adv_setting.sm', return_value=mock_session):
        # Вызываем обработчик
        await cancel_delete(mock_callback_query, mock_state, mock_bot)
    
    # Проверяем, что был вызван правильный метод с правильными параметрами
    mock_bot.send_message.assert_called_once()

@pytest.mark.asyncio
async def test_create_adv_setting(test_async_db):
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
            name="test_adv",
            wb_cabinet_id=wb_cabinet.id,
            active_status="active",
            bot_active=True
        )
        session.add(adv_setting)
        await session.commit()

        # Verify
        result = await session.get(AdvSetting, adv_setting.id)
        assert result is not None
        assert result.adv_id == 123
        assert result.name == "test_adv"

@pytest.mark.asyncio
async def test_update_adv_setting(test_async_db):
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
            name="test_adv",
            wb_cabinet_id=wb_cabinet.id,
            active_status="active",
            bot_active=True
        )
        session.add(adv_setting)
        await session.commit()

        # Update
        adv_setting.name = "updated_adv"
        await session.commit()

        # Verify
        result = await session.get(AdvSetting, adv_setting.id)
        assert result.name == "updated_adv"

@pytest.mark.asyncio
async def test_delete_adv_setting(test_async_db):
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
            name="test_adv",
            wb_cabinet_id=wb_cabinet.id,
            active_status="active",
            bot_active=True
        )
        session.add(adv_setting)
        await session.commit()

        # Delete
        await session.delete(adv_setting)
        await session.commit()

        # Verify
        result = await session.get(AdvSetting, adv_setting.id)
        assert result is None

@pytest.mark.asyncio
async def test_get_adv_settings_by_cabinet(test_async_db):
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
        
        adv_setting1 = AdvSetting(
            adv_id=123,
            name="test_adv1",
            wb_cabinet_id=wb_cabinet.id,
            active_status="active",
            bot_active=True
        )
        adv_setting2 = AdvSetting(
            adv_id=124,
            name="test_adv2",
            wb_cabinet_id=wb_cabinet.id,
            active_status="active",
            bot_active=True
        )
        session.add_all([adv_setting1, adv_setting2])
        await session.commit()

        # Query
        stmt = select(AdvSetting).where(AdvSetting.wb_cabinet_id == wb_cabinet.id)
        result = await session.execute(stmt)
        settings = result.scalars().all()

        # Verify
        assert len(settings) == 2
        assert all(s.wb_cabinet_id == wb_cabinet.id for s in settings)

@pytest.mark.asyncio
async def test_adv_setting_relationships(test_async_db):
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
            name="test_adv",
            wb_cabinet_id=wb_cabinet.id,
            active_status="active",
            bot_active=True
        )
        session.add(adv_setting)
        await session.commit()

        # Verify relationships
        stmt = select(AdvSetting).where(AdvSetting.id == adv_setting.id)
        result = await session.execute(stmt)
        loaded_setting = result.scalar_one()
        
        assert loaded_setting.wb_cabinet_id == wb_cabinet.id

@pytest.mark.asyncio
async def test_back_to_advs_handler_simple():
    # Mock data
    mock_message = AsyncMock()
    mock_state = AsyncMock()
    
    # Test handler
    from app.client_bot.user_interface.handlers.adv_setting import back_to_advs_handler
    await back_to_advs_handler(mock_message, mock_state)
    
    # Verify
    mock_message.answer.assert_called_once()
    mock_state.clear.assert_called_once()

@pytest.mark.asyncio
async def test_cancel_delete_handler_simple():
    # Mock data
    mock_message = AsyncMock()
    mock_state = AsyncMock()
    
    # Test handler
    from app.client_bot.user_interface.handlers.adv_setting import cancel_delete_handler
    await cancel_delete_handler(mock_message, mock_state)
    
    # Verify
    mock_message.answer.assert_called_once()
    mock_state.clear.assert_called_once() 