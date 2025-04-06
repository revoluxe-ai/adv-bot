import pytest
from aiogram import Bot, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select
from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet, User, AdvSetting
from datetime import datetime
from app.client_bot.user_interface.handlers.get_shop_for_admin import AdminsGetAdvByIdFilter
from app.client_bot import const
from unittest.mock import AsyncMock, MagicMock
from tests.mocks import MockAdvSetting

@pytest.fixture
def mock_message() -> AsyncMock:
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
    return MagicMock(spec=AdvSetting, id=1, name="Test Adv")

# @pytest.fixture
# def mock_wb_user_cabinet():
#     return MagicMock(spec=WBUserCabinet, id=1)


@pytest.mark.asyncio
async def test_create_adv_setting(test_async_db, mock_wb_cabinet):
    """Тест создания настройки рекламы"""
    async with test_async_db() as session:
        session.add(mock_wb_cabinet)
        await session.commit()

        adv_setting = MockAdvSetting(
            wb_cabinet_id=mock_wb_cabinet.id,
            name="Test Setting",
            description="Test Description",
            is_active=True
        )
        session.add(adv_setting)
        await session.commit()

        # Проверяем, что запись создана
        result = await session.get(MockAdvSetting, adv_setting.id)
        assert result is not None
        assert result.name == "Test Setting"
        assert result.description == "Test Description"
        assert result.is_active is True

@pytest.mark.asyncio
async def test_update_adv_setting(test_async_db, mock_wb_cabinet):
    """Тест обновления настройки рекламы"""
    async with test_async_db() as session:
        session.add(mock_wb_cabinet)
        await session.commit()

        # Создаем настройку
        adv_setting = MockAdvSetting(
            wb_cabinet_id=mock_wb_cabinet.id,
            name="Test Setting",
            description="Test Description",
            is_active=True
        )
        session.add(adv_setting)
        await session.commit()

        # Обновляем настройку
        adv_setting.name = "Updated Setting"
        adv_setting.description = "Updated Description"
        adv_setting.is_active = False
        await session.commit()

        # Проверяем обновление
        result = await session.get(MockAdvSetting, adv_setting.id)
        assert result is not None
        assert result.name == "Updated Setting"
        assert result.description == "Updated Description"
        assert result.is_active is False

@pytest.mark.asyncio
async def test_delete_adv_setting(test_async_db, mock_wb_cabinet):
    """Тест удаления настройки рекламы"""
    async with test_async_db() as session:
        session.add(mock_wb_cabinet)
        await session.commit()

        # Создаем настройку
        adv_setting = MockAdvSetting(
            wb_cabinet_id=mock_wb_cabinet.id,
            name="Test Setting",
            description="Test Description",
            is_active=True
        )
        session.add(adv_setting)
        await session.commit()

        # Удаляем настройку
        await session.delete(adv_setting)
        await session.commit()

        # Проверяем удаление
        result = await session.get(MockAdvSetting, adv_setting.id)
        assert result is None

@pytest.mark.asyncio
async def test_get_adv_settings_by_cabinet(test_async_db, mock_wb_cabinet):
    """Тест получения настроек рекламы по кабинету"""
    async with test_async_db() as session:
        session.add(mock_wb_cabinet)
        await session.commit()

        # Создаем несколько настроек
        settings = [
            MockAdvSetting(
                wb_cabinet_id=mock_wb_cabinet.id,
                name=f"Setting {i}",
                description=f"Description {i}",
                is_active=True
            )
            for i in range(3)
        ]
        for setting in settings:
            session.add(setting)
        await session.commit()

        # Получаем настройки
        from sqlalchemy import select
        query = select(MockAdvSetting).where(MockAdvSetting.wb_cabinet_id == mock_wb_cabinet.id)
        result = await session.execute(query)
        result_settings = result.scalars().all()

        assert len(result_settings) == 3
        for i, setting in enumerate(result_settings):
            assert setting.name == f"Setting {i}"
            assert setting.description == f"Description {i}"
            assert setting.is_active is True

@pytest.mark.asyncio
async def test_adv_setting_relationships(test_async_db, mock_wb_cabinet):
    """Тест связей настройки рекламы"""
    async with test_async_db() as session:
        session.add(mock_wb_cabinet)
        await session.commit()

        # Создаем настройку
        adv_setting = MockAdvSetting(
            wb_cabinet_id=mock_wb_cabinet.id,
            name="Test Setting",
            description="Test Description",
            is_active=True
        )
        session.add(adv_setting)
        await session.commit()

        # Проверяем связь с кабинетом
        result = await session.get(MockAdvSetting, adv_setting.id)
        assert result is not None
        assert result.wb_cabinet_id == mock_wb_cabinet.id

def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session

@pytest.fixture
def mock_sm(mock_session):
    class AsyncContextManager:
        async def __aenter__(self):
            return mock_session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    def session_maker():
        return AsyncContextManager()
    return session_maker

@pytest.mark.asyncio
async def test_admins_filter_with_admin_message(mock_message, mock_session, mock_sm, monkeypatch):
    """Тест фильтра AdminsGetAdvByIdFilter с сообщением от администратора"""
    admin_id = 373435337  # Используем реальный ID админа из const.ADMINS
    mock_message.from_user.id = admin_id
    mock_message.text = "12345"  # Валидный ID рекламной кампании
    
    # Создаем мок объект рекламной кампании
    mock_adv = MockAdvSetting(id=1, adv_id=12345)
    
    # Настраиваем мок для базы данных
    mock_result = AsyncMock()
    mock_result.scalar.return_value = mock_adv
    mock_session.execute.return_value = mock_result
    
    # Подменяем функцию get_async_session_maker
    monkeypatch.setattr("app.client_bot.user_interface.handlers.get_shop_for_admin.sm", mock_sm)
    
    filter_instance = AdminsGetAdvByIdFilter()
    result = await filter_instance(mock_message)
    assert result is True

@pytest.mark.asyncio
async def test_admins_filter_with_non_admin_message(mock_message, mock_sm, monkeypatch):
    """Тест фильтра AdminsGetAdvByIdFilter с сообщением от не-администратора"""
    non_admin_id = max(const.ADMINS) + 1  # Гарантированно не админский ID
    mock_message.from_user.id = non_admin_id
    mock_message.text = "12345"
    
    filter_instance = AdminsGetAdvByIdFilter()
    result = await filter_instance(mock_message)
    assert result is False

@pytest.mark.asyncio
async def test_admins_filter_with_invalid_message(mock_message, mock_sm, monkeypatch):
    """Тест фильтра AdminsGetAdvByIdFilter с невалидным сообщением"""
    admin_id = const.ADMINS[0]
    mock_message.from_user.id = admin_id
    mock_message.text = "invalid"  # Невалидный ID рекламной кампании
    
    filter_instance = AdminsGetAdvByIdFilter()
    result = await filter_instance(mock_message)
    assert result is False

