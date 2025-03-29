import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select
from app.modules.cabinet_bonus_manager.bonus_service import add_bonus, subtract_bonus, reset_bonus, get_wb_cabinet
from app.modules.cabinet_bonus_manager.handlers import BonusAdminStates, process_shop_id, process_shop_bonus_callback, process_amount, process_description, process_confirm_callback, process_cancel_callback
from app.client_bot.user_interface.views.callbacks import AdminBonus
from tests.mocks import MockWBCabinet, MockWBBonusPayment, MockUser
from contextlib import asynccontextmanager

@pytest.fixture
def cabinet_bonus_session_mocker():
    """
    Фикстура для создания мока асинхронной сессии для тестирования функций управления бонусами.
    Учитывает двойную структуру вызова контекстного менеджера в функциях cabinet_bonus_manager.
    """
    @asynccontextmanager
    async def _mock_get_async_session_maker():
        yield AsyncMock()

    with patch('app.modules.cabinet_bonus_manager.bonus_service.get_async_session_maker', 
               return_value=_mock_get_async_session_maker):
        yield

@pytest.mark.asyncio
async def test_add_bonus(mock_get_async_session_factory, mock_test_db_session, 
                         mock_user, mock_wb_cabinet, cabinet_bonus_session_mocker):
    # Получаем начальный бонус непосредственно из БД
    mock_test_db_session.refresh(mock_wb_cabinet)
    initial_bonus = mock_wb_cabinet.bonus
    
    # Патчим datetime.now() для установки transaction_date_time
    current_time = datetime(2023, 1, 1, 12, 0, 0)
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = current_time
        # Патчим метод calculated_bonus, чтобы избежать DetachedInstanceError
        with patch('app.modules.common_slaves.wildberries.models.WBCabinet.calculated_bonus', 
                   new_callable=MagicMock) as mock_bonus:
            # Устанавливаем возвращаемое значение для calculated_bonus
            mock_bonus.__get__ = MagicMock(return_value=initial_bonus + 200.0)
            
            # Вызываем функцию добавления бонусов
            await add_bonus(mock_test_db_session, "test_shop", 200.0, "Тестовое добавление бонусов", 1)
            
            # Проверяем, что запись о бонусе создана с правильным временем транзакции
            bonus_payment = await mock_test_db_session.execute(
                select(MockWBBonusPayment).filter_by(wb_cabinet_id=mock_wb_cabinet.id, operation_type="add")
            )
            bonus_payment = bonus_payment.scalars().first()
            
            assert bonus_payment is not None
            assert bonus_payment.transaction_date_time == current_time
            assert bonus_payment.amount == 200.0
            assert bonus_payment.operation_type == "add"
            assert bonus_payment.admin_user_id == 1

@pytest.mark.asyncio
async def test_subtract_bonus(mock_get_async_session_factory, mock_test_db_session, 
                              mock_user, mock_wb_cabinet, cabinet_bonus_session_mocker):
    # Получаем начальный бонус непосредственно из БД
    mock_test_db_session.refresh(mock_wb_cabinet)
    initial_bonus = mock_wb_cabinet.bonus
    
    # Патчим datetime.now() для установки transaction_date_time
    current_time = datetime(2023, 1, 1, 12, 0, 0)
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = current_time
        # Патчим метод calculated_bonus, чтобы избежать DetachedInstanceError
        with patch('app.modules.common_slaves.wildberries.models.WBCabinet.calculated_bonus', 
                   new_callable=MagicMock) as mock_bonus:
            # Устанавливаем возвращаемые значения для calculated_bonus
            mock_bonus.__get__ = MagicMock(return_value=initial_bonus - 50.0)
            
            # Вызываем функцию вычитания бонусов
            await subtract_bonus(mock_test_db_session, "test_shop", 50.0, "Тестовое вычитание бонусов", 1)
            
            # Проверяем, что запись о бонусе создана с правильным временем транзакции
            bonus_payment = await mock_test_db_session.execute(
                select(MockWBBonusPayment).filter_by(wb_cabinet_id=mock_wb_cabinet.id, operation_type="subtract")
            )
            bonus_payment = bonus_payment.scalars().first()
            
            assert bonus_payment is not None
            assert bonus_payment.transaction_date_time == current_time
            assert bonus_payment.amount == -50.0
            assert bonus_payment.operation_type == "subtract"
            assert bonus_payment.admin_user_id == 1

@pytest.mark.asyncio
async def test_reset_bonus(mock_get_async_session_factory, mock_test_db_session, 
                           mock_user, mock_wb_cabinet, cabinet_bonus_session_mocker):
    # Получаем начальный бонус непосредственно из БД
    mock_test_db_session.refresh(mock_wb_cabinet)
    initial_bonus = mock_wb_cabinet.bonus
    
    # Патчим datetime.now() для установки transaction_date_time
    current_time = datetime(2023, 1, 1, 12, 0, 0)
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = current_time
        # Патчим метод calculated_bonus, чтобы избежать DetachedInstanceError
        with patch('app.modules.common_slaves.wildberries.models.WBCabinet.calculated_bonus', 
                   new_callable=MagicMock) as mock_bonus:
            # Устанавливаем возвращаемые значения для calculated_bonus
            mock_bonus.__get__ = MagicMock(return_value=0.0)
            
            # Вызываем функцию сброса бонусов
            await reset_bonus(mock_test_db_session, "test_shop", "Тестовый сброс бонусов", 1)
            
            # Проверяем, что запись о бонусе создана с правильным временем транзакции
            bonus_payment = await mock_test_db_session.execute(
                select(MockWBBonusPayment).filter_by(wb_cabinet_id=mock_wb_cabinet.id, operation_type="reset")
            )
            bonus_payment = bonus_payment.scalars().first()
            
            assert bonus_payment is not None
            assert bonus_payment.transaction_date_time == current_time
            assert bonus_payment.amount == -initial_bonus
            assert bonus_payment.operation_type == "reset"
            assert bonus_payment.admin_user_id == 1

@pytest.mark.asyncio
async def test_get_cabinet_bonus(mock_get_async_session_factory, mock_test_db_session, 
                                 mock_user, mock_wb_cabinet, cabinet_bonus_session_mocker):
    # Получаем начальный бонус непосредственно из БД
    mock_test_db_session.refresh(mock_wb_cabinet)
    initial_bonus = mock_wb_cabinet.bonus
    
    # Патчим метод calculated_bonus, чтобы избежать DetachedInstanceError
    with patch('app.modules.common_slaves.wildberries.models.WBCabinet.calculated_bonus', 
               new_callable=MagicMock) as mock_bonus:
        # Устанавливаем возвращаемое значение для calculated_bonus
        mock_bonus.__get__ = MagicMock(return_value=initial_bonus)
        
        # Вызываем функцию получения бонусов
        bonus = await get_wb_cabinet(mock_test_db_session, "test_shop")
        
        # Проверяем, что возвращается правильное значение бонуса
        assert bonus == initial_bonus

@pytest.mark.asyncio
async def test_subtract_bonus_insufficient_funds(mock_get_async_session_factory, mock_test_db_session, 
                                                 mock_user, mock_wb_cabinet, cabinet_bonus_session_mocker):
    # Получаем начальный бонус непосредственно из БД
    mock_test_db_session.refresh(mock_wb_cabinet)
    initial_bonus = mock_wb_cabinet.bonus
    
    # Патчим метод calculated_bonus, чтобы избежать DetachedInstanceError
    with patch('app.modules.common_slaves.wildberries.models.WBCabinet.calculated_bonus', 
               new_callable=MagicMock) as mock_bonus:
        # Устанавливаем возвращаемое значение для calculated_bonus
        mock_bonus.__get__ = MagicMock(return_value=initial_bonus)
        
        # Попытка вычесть больше бонусов, чем доступно
        with pytest.raises(ValueError, match="Недостаточно бонусов"):
            await subtract_bonus(mock_test_db_session, "test_shop", initial_bonus + 100.0, 
                                "Тестовое вычитание бонусов", 1)

# Фикстуры для тестирования обработчиков
@pytest.fixture
def mock_message():
    """Фикстура для имитации сообщения от пользователя"""
    message = AsyncMock()
    message.from_user.id = 123456789  # ID администратора
    message.text = None
    # Делаем методы отправки сообщений AsyncMock
    message.answer = AsyncMock()
    message.reply = AsyncMock()
    return message

@pytest.fixture
def mock_callback_query():
    """Фикстура для имитации callback query от пользователя"""
    callback = AsyncMock()
    callback.from_user.id = 123456789  # ID администратора
    callback.data = None
    # Делаем асинхронные методы
    callback.answer = AsyncMock()
    callback.message = AsyncMock()
    callback.message.edit_text = AsyncMock()
    callback.message.edit_reply_markup = AsyncMock()
    return callback

@pytest.fixture
def mock_state():
    """Фикстура для имитации FSMContext"""
    state = AsyncMock()
    state_data = {}
    
    async def update_data(**kwargs):
        state_data.update(kwargs)
    
    async def get_data():
        return state_data
    
    async def set_state(new_state):
        state.current_state = new_state
    
    async def clear():
        state_data.clear()
        state.current_state = None
        
    state.update_data = update_data
    state.get_data = get_data
    state.set_state = set_state
    state.clear = clear
    state.current_state = None
    
    return state

# Тесты для обработчиков из handlers.py
@pytest.mark.asyncio
async def test_process_shop_id_valid(mock_message, mock_state):
    """Тест обработки правильного shop_id"""
    shop_id = "test_shop"
    current_bonus = 500.0
    
    # Устанавливаем текст сообщения
    mock_message.text = shop_id
    
    # Мокаем функцию get_cabinet_bonus - используем AsyncMock вместо MagicMock
    with patch('app.modules.cabinet_bonus_manager.handlers.get_cabinet_bonus', 
               new_callable=AsyncMock, return_value=current_bonus) as mock_get_bonus:
        
        # Вызываем тестируемую функцию
        await process_shop_id(mock_message, mock_state)
        
        # Проверяем, что функция get_cabinet_bonus была вызвана с правильным shop_id
        mock_get_bonus.assert_called_once_with(shop_id)
        
        # Проверяем, что в состояние были сохранены правильные данные
        data = await mock_state.get_data()
        assert data.get("shop_id") == shop_id
        assert data.get("current_bonus") == current_bonus
        
        # Проверяем, что пользователю было отправлено сообщение с клавиатурой
        mock_message.answer.assert_called_once()
        args, kwargs = mock_message.answer.call_args
        assert f"Магазин: {shop_id}" in args[0]
        assert "reply_markup" in kwargs

@pytest.mark.asyncio
async def test_process_shop_id_invalid(mock_message, mock_state):
    """Тест обработки несуществующего shop_id"""
    shop_id = "nonexistent_shop"
    
    # Устанавливаем текст сообщения
    mock_message.text = shop_id
    
    # Мокаем функцию get_cabinet_bonus для возврата None (кабинет не найден)
    with patch('app.modules.cabinet_bonus_manager.handlers.get_cabinet_bonus', 
               new_callable=AsyncMock, return_value=None) as mock_get_bonus:
        
        # Вызываем тестируемую функцию
        await process_shop_id(mock_message, mock_state)
        
        # Проверяем, что функция get_cabinet_bonus была вызвана с правильным shop_id
        mock_get_bonus.assert_called_once_with(shop_id)
        
        # Проверяем, что пользователю было отправлено сообщение об ошибке
        mock_message.answer.assert_called_once()
        args, kwargs = mock_message.answer.call_args
        assert "не найден" in args[0]

@pytest.mark.asyncio
async def test_process_shop_bonus_callback_add(mock_callback_query, mock_state):
    """Тест обработки callback для добавления бонусов"""
    shop_id = "test_shop"
    current_bonus = 500.0
    
    # Настраиваем callback данные
    mock_callback_query.data = f"shop_bonus_add_{shop_id}"
    
    # Настраиваем состояние
    await mock_state.update_data(shop_id=shop_id, current_bonus=current_bonus)
    
    # Вызываем тестируемую функцию
    await process_shop_bonus_callback(mock_callback_query, mock_state)
    
    # Проверяем, что callback был обработан
    mock_callback_query.answer.assert_called_once()
    
    # Проверяем, что в состояние была добавлена операция
    data = await mock_state.get_data()
    assert data.get("operation") == "add"
    
    # Проверяем, что установлено состояние ожидания суммы
    assert mock_state.current_state == BonusAdminStates.waiting_for_amount
    
    # Проверяем, что пользователю было отправлено сообщение для ввода суммы
    mock_callback_query.message.edit_text.assert_called_once()
    args, kwargs = mock_callback_query.message.edit_text.call_args
    assert "Введите сумму для пополнения" in args[0]

@pytest.mark.asyncio
async def test_process_shop_bonus_callback_reset(mock_callback_query, mock_state):
    """Тест обработки callback для обнуления бонусов"""
    shop_id = "test_shop"
    current_bonus = 500.0
    
    # Настраиваем callback данные
    mock_callback_query.data = f"shop_bonus_reset_{shop_id}"
    
    # Настраиваем состояние
    await mock_state.update_data(shop_id=shop_id, current_bonus=current_bonus)
    
    # Вызываем тестируемую функцию
    await process_shop_bonus_callback(mock_callback_query, mock_state)
    
    # Проверяем, что callback был обработан
    mock_callback_query.answer.assert_called_once()
    
    # Проверяем, что в состояние была добавлена операция
    data = await mock_state.get_data()
    assert data.get("operation") == "reset"
    
    # Проверяем, что установлено состояние ожидания описания
    assert mock_state.current_state == BonusAdminStates.waiting_for_description
    
    # Проверяем, что пользователю было отправлено сообщение для ввода описания
    mock_callback_query.message.edit_text.assert_called_once()
    args, kwargs = mock_callback_query.message.edit_text.call_args
    assert "Введите описание операции обнуления" in args[0]

@pytest.mark.asyncio
async def test_process_amount_valid(mock_message, mock_state):
    """Тест обработки корректной суммы"""
    shop_id = "test_shop"
    current_bonus = 500.0
    amount = "100.5"
    
    # Настраиваем сообщение
    mock_message.text = amount
    
    # Настраиваем состояние
    await mock_state.update_data(shop_id=shop_id, current_bonus=current_bonus, operation="add")
    
    # Вызываем тестируемую функцию
    await process_amount(mock_message, mock_state)
    
    # Проверяем, что в состояние была добавлена сумма
    data = await mock_state.get_data()
    assert data.get("amount") == 100.5
    
    # Проверяем, что установлено состояние ожидания описания
    assert mock_state.current_state == BonusAdminStates.waiting_for_description
    
    # Проверяем, что пользователю было отправлено сообщение для ввода описания
    mock_message.answer.assert_called_once()
    args, kwargs = mock_message.answer.call_args
    assert "Введите описание операции" in args[0]

@pytest.mark.asyncio
async def test_process_confirm_callback(mock_callback_query, mock_state):
    """Тест обработки подтверждения операции"""
    shop_id = "test_shop"
    amount = 100.5
    description = "Тестовое описание"
    admin_user_id = 123456789
    
    # Настраиваем callback данные
    mock_callback_query.data = f"bonus_confirm_add_{shop_id}_{amount}"
    mock_callback_query.from_user.id = admin_user_id
    
    # Настраиваем состояние
    await mock_state.update_data(
        shop_id=shop_id, 
        current_bonus=500.0,
        operation="add",
        amount=amount,
        description=description
    )
    
    # Мокаем функции бизнес-логики и получения текущего бонуса
    with patch('app.modules.cabinet_bonus_manager.handlers.add_bonus',
              new_callable=AsyncMock, return_value=True) as mock_add_bonus, \
         patch('app.modules.cabinet_bonus_manager.handlers.get_cabinet_bonus',
              new_callable=AsyncMock, return_value=600.5) as mock_get_bonus:
        
        # Вызываем тестируемую функцию
        await process_confirm_callback(mock_callback_query, mock_state, AsyncMock())
        
        # Проверяем, что callback был обработан
        mock_callback_query.answer.assert_called_once()
        
        # Проверяем, что функция add_bonus была вызвана с правильными параметрами
        mock_add_bonus.assert_called_once_with(shop_id, amount, admin_user_id, description)
        
        # Проверяем, что функция get_cabinet_bonus была вызвана для получения нового баланса
        mock_get_bonus.assert_called_once_with(shop_id)
        
        # Проверяем, что пользователю было отправлено сообщение об успешной операции
        mock_callback_query.message.edit_text.assert_called_once()
        args, kwargs = mock_callback_query.message.edit_text.call_args
        assert "успешно добавлены" in args[0]
        assert "Новый баланс бонусов: 600.5" in args[0]
        assert "reply_markup" in kwargs  # Проверяем, что присутствует клавиатура 