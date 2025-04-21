import pytest
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from unittest.mock import AsyncMock, MagicMock, patch

from app.client_bot.user_interface.handlers.start import process_cabinet_api
from app.client_bot.user_interface import states
from tests.test_models import TestUser, TestWBToken, TestWBCabinet, TestWBUserCabinet
from app.modules.common_slaves.wildberries.exceptions import NotValidTokenError
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from app.utils.db.models import WBCabinet, WBToken, WBUserCabinet

# Фикстура для создания тестового пользователя
@pytest.fixture
async def test_user(test_async_db: AsyncSession):
    """Создает тестового пользователя в БД"""
    user = TestUser(
        user_telegram_id=12345,
        username="test_user"
    )
    test_async_db.add(user)
    await test_async_db.commit()
    await test_async_db.refresh(user)
    return user

# Фикстура для мока бота
@pytest.fixture
def bot():
    """Создает мок объекта бота"""
    return AsyncMock(spec=Bot)

# Фикстура для мока состояния
@pytest.fixture
def state():
    """Создает мок объекта состояния FSM"""
    class MockState:
        def __init__(self):
            self.state_data = {"cabinet_name": "test_cabinet"}
            self.current_state = states.CabinetRegistration.api

        async def get_state(self):
            return self.current_state

        async def set_state(self, new_state=None):
            self.current_state = new_state

        async def get_data(self):
            return self.state_data

        async def update_data(self, **kwargs):
            self.state_data.update(kwargs)

        async def clear(self):
            self.state_data = {}
            self.current_state = None

    return MockState()

# Фикстура для создания тестового сообщения
@pytest.fixture
def message():
    """Создает мок объекта сообщения"""
    class MockMessage:
        def __init__(self):
            self.text = "test_token"
            self.chat = type("MockChat", (), {"id": 12345})
            self.from_user = type("MockUser", (), {"id": 12345})

    return MockMessage()

@pytest.mark.asyncio
async def test_process_cabinet_api_success(test_async_db, test_user, bot, state, message):
    """Тест успешной регистрации нового кабинета"""
    # Подготавливаем тестовые данные
    test_token = "valid_test_token"
    test_shop_id = "test_shop_123"
    message.text = test_token

    # Мокаем get_shop_id_from_token для экземпляра WBToken
    with patch('app.modules.common_slaves.wildberries.models.WBToken.get_shop_id_from_token', 
               return_value=test_shop_id) as mock_get_shop_id:

        # Мокаем WBCabinetAccess
        with patch('app.client_bot.user_interface.handlers.start.WBCabinetAccess') as mock_access_class:
            mock_access_instance = AsyncMock()
            mock_access_class.return_value = mock_access_instance

            # Мокаем ShopDataUpdater
            with patch('app.client_bot.user_interface.handlers.start.ShopDataUpdater') as mock_updater_class:
                mock_updater_instance = AsyncMock()
                mock_updater_class.return_value = mock_updater_instance
                mock_updater_instance.update_advs_data = AsyncMock()

                # Вызываем тестируемую функцию
                await process_cabinet_api(message, bot, state)

                # Проверяем, что кабинет был создан
                stmt = select(WBCabinet).where(WBCabinet.shop_id == test_shop_id)
                result = await test_async_db.execute(stmt)
                cabinet = result.scalar_one_or_none()
                assert cabinet is not None
                assert cabinet.shop_id == test_shop_id
                assert cabinet.bonus == 0
                assert cabinet.balance == 0

                # Проверяем, что создана связь пользователя с кабинетом
                stmt = select(WBUserCabinet).where(
                    and_(
                        WBUserCabinet.wb_cabinet_id == cabinet.id,
                        WBUserCabinet.user_id == test_user.id
                    )
                )
                result = await test_async_db.execute(stmt)
                user_cabinet = result.scalar_one_or_none()
                assert user_cabinet is not None
                assert user_cabinet.name == state.state_data["cabinet_name"]

                # Проверяем, что токен был создан и привязан к пользователю
                stmt = select(WBToken).where(
                    and_(
                        WBToken.api_key == test_token,
                        WBToken.user_id == test_user.id,
                        WBToken.shop_id == test_shop_id
                    )
                )
                result = await test_async_db.execute(stmt)
                token = result.scalar_one_or_none()
                assert token is not None

                # Проверяем, что бот отправил сообщение об успехе
                bot.send_message.assert_called_with(
                    message.chat.id,
                    f"Магазин {state.state_data['cabinet_name']} успешно добавлен!"
                )

                # Проверяем, что обновление данных было запущено
                mock_updater_instance.update_advs_data.assert_called_once()

@pytest.mark.asyncio
async def test_process_cabinet_api_invalid_token(test_async_db, test_user, bot, state, message):
    """Тест обработки невалидного токена"""
    message.text = "invalid_token"

    # Создаем невалидный токен
    token = TestWBToken(
        api_key="invalid_token",
        shop_id=None,  # Невалидный токен не имеет shop_id
        user_id=None
    )
    test_async_db.add(token)
    await test_async_db.commit()

    # Мокаем WBCabinetAccess для имитации невалидного токена
    with patch('app.client_bot.user_interface.handlers.start.WBCabinetAccess') as mock_access:
        mock_access.get_shop_id_from_token.side_effect = NotValidTokenError("Invalid token")

        # Вызываем тестируемую функцию
        await process_cabinet_api(message, bot, state)

        # Проверяем, что было отправлено сообщение об ошибке
        bot.send_message.assert_called_once_with(
            message.chat.id,
            "Токен не валиден, попробуйте еще раз: "
        )

@pytest.mark.asyncio
async def test_process_cabinet_api_token_already_used(test_async_db, test_user, bot, state, message):
    """Тест обработки токена, который уже используется другим пользователем"""
    test_token = "existing_token"
    message.text = test_token

    # Создаем существующий токен другого пользователя
    existing_token = TestWBToken(
        api_key=test_token,
        user_id=test_user.id + 1,
        shop_id="existing_shop"
    )
    test_async_db.add(existing_token)
    await test_async_db.commit()

    # Вызываем тестируемую функцию
    await process_cabinet_api(message, bot, state)

    # Проверяем, что токен все еще привязан к другому пользователю
    stmt = select(TestWBToken).where(TestWBToken.api_key == test_token)
    result = await test_async_db.execute(stmt)
    token = result.scalar_one_or_none()
    assert token is not None
    assert token.user_id == test_user.id + 1

    # Проверяем, что было отправлено сообщение об ошибке
    bot.send_message.assert_called_once_with(
        message.chat.id,
        "Этот токен уже используется другим пользователем."
    )

@pytest.mark.asyncio
async def test_process_cabinet_api_existing_cabinet(test_async_db, test_user, bot, state, message):
    """Тест обработки существующего кабинета"""
    test_token = "new_token"
    test_shop_id = "existing_shop"
    message.text = test_token

    # Создаем существующий кабинет
    existing_cabinet = TestWBCabinet(shop_id=test_shop_id, bonus=0, balance=0)
    test_async_db.add(existing_cabinet)
    await test_async_db.commit()

    # Создаем новый токен с существующим shop_id
    token = TestWBToken(
        api_key=test_token,
        shop_id=test_shop_id,
        user_id=None
    )
    test_async_db.add(token)
    await test_async_db.commit()

    # Вызываем тестируемую функцию
    await process_cabinet_api(message, bot, state)

    # Проверяем, что создана связь пользователя с существующим кабинетом
    stmt = select(TestWBUserCabinet).where(
        TestWBUserCabinet.wb_cabinet_id == existing_cabinet.id,
        TestWBUserCabinet.user_id == test_user.id
    )
    result = await test_async_db.execute(stmt)
    user_cabinet = result.scalar_one_or_none()
    assert user_cabinet is not None

    # Проверяем, что токен привязан к пользователю
    stmt = select(TestWBToken).where(TestWBToken.api_key == test_token)
    result = await test_async_db.execute(stmt)
    token = result.scalar_one_or_none()
    assert token is not None
    assert token.user_id == test_user.id

    # Проверяем, что было отправлено сообщение о существующем кабинете
    bot.send_message.assert_called_with(
        message.chat.id,
        "Кабинет уже существует в системе."
    )

@pytest.mark.asyncio
async def test_process_cabinet_api_start_command(test_async_db, test_user, bot, state, message):
    """Тест обработки команды /start во время ввода токена"""
    message.text = "/start"

    # Мокаем функцию start_registration
    with patch('app.client_bot.user_interface.handlers.start.start_registration') as mock_start:
        # Вызываем тестируемую функцию
        await process_cabinet_api(message, bot, state)

        # Проверяем, что была вызвана функция start_registration
        mock_start.assert_called_once_with(message, bot, state) 