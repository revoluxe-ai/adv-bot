from datetime import datetime
import dotenv
import sys, os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select
from app.modules.cabinet_bonus_manager.bonus_service import add_bonus, subtract_bonus, reset_bonus, get_wb_cabinet_by_shop_id
from app.modules.cabinet_bonus_manager.state_manager import BonusManagerStateGroup
from tests.mocks import MockWBBonusPayment
from contextlib import asynccontextmanager

dotenv.load_dotenv(dotenv.find_dotenv())


@pytest.fixture
def cabinet_bonus_session_mocker() -> AsyncMock:
    """
    Фикстура для создания мока асинхронной сессии для тестирования функций управления бонусами.
    Учитывает двойную структуру вызова контекстного менеджера в функциях cabinet_bonus_manager.
    """

    @asynccontextmanager
    async def _mock_get_async_session_maker() -> AsyncMock:
        yield AsyncMock()

    with patch('app.modules.cabinet_bonus_manager.bonus_service.get_async_session_maker',
               return_value=_mock_get_async_session_maker):
        yield


@pytest.mark.asyncio
async def test_add_bonus(mock_test_db_session,
                         mock_user, mock_wb_cabinet, cabinet_bonus_session_mocker):
    # Получаем начальный бонус непосредственно из БД
    mock_test_db_session.refresh(mock_wb_cabinet)
    initial_bonus = mock_wb_cabinet.bonus

    # Патчим datetime.now() для установки transaction_date_time
    current_time = datetime(2023, 1, 1, 12)
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = current_time
        # Патчим метод calculated_bonus, чтобы избежать DetachedInstanceError
        with patch('app.modules.common_slaves.wildberries.models.WBCabinet.calculated_bonus',
                   new_callable=MagicMock) as mock_bonus:
            # Устанавливаем возвращаемые значения для calculated_bonus
            mock_bonus.__get__ = MagicMock(return_value=initial_bonus + 200.0)

            # Вызываем функцию добавления бонусов
            result = await add_bonus(
                            wb_cabinet_original_id=mock_wb_cabinet.id,
                            amount=200.0,
                            admin_user_id=1,
                            description="Тестовое начисление бонусов")
            
            assert result is True

            # Проверяем запись о платеже
            bonus_payment = await mock_test_db_session.execute(
                select(MockWBBonusPayment).filter_by(wb_cabinet_id=mock_wb_cabinet.id, operation_type="add")
            )
            bonus_payment = bonus_payment.scalars().first()

            assert bonus_payment is not None
            assert bonus_payment.transaction_date_time == current_time
            assert bonus_payment.amount == 200.0
            assert bonus_payment.operation_type == "add"
            assert bonus_payment.admin_user_id == 1

            # Проверяем calculated_bonus через мок
            assert mock_bonus.__get__.called
            assert mock_wb_cabinet.calculated_bonus == initial_bonus + 200.0


@pytest.mark.asyncio
async def test_subtract_bonus(mock_test_db_session,
                              mock_user, mock_wb_cabinet, cabinet_bonus_session_mocker):
    # Получаем начальный бонус непосредственно из БД
    mock_test_db_session.refresh(mock_wb_cabinet)
    initial_bonus = mock_wb_cabinet.bonus

    # Патчим datetime.now() для установки transaction_date_time
    current_time = datetime(2023, 1, 1, 12)
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = current_time
        # Патчим метод calculated_bonus, чтобы избежать DetachedInstanceError
        with patch('app.modules.common_slaves.wildberries.models.WBCabinet.calculated_bonus',
                   new_callable=MagicMock) as mock_bonus:
            # Устанавливаем возвращаемые значения для calculated_bonus
            mock_bonus.__get__ = MagicMock(return_value=initial_bonus - 50.0)

            # Вызываем функцию вычитания бонусов
            await subtract_bonus("test_shop", 50.0, 1, "Тестовое вычитание бонусов")

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
async def test_reset_bonus(mock_test_db_session,
                           mock_user, mock_wb_cabinet, cabinet_bonus_session_mocker):
    # Получаем начальный бонус непосредственно из БД
    mock_test_db_session.refresh(mock_wb_cabinet)
    initial_bonus = mock_wb_cabinet.bonus

    # Патчим datetime.now() для установки transaction_date_time
    current_time = datetime(2023, 1, 1, 12)
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = current_time
        # Патчим метод calculated_bonus, чтобы избежать DetachedInstanceError
        with patch('app.modules.common_slaves.wildberries.models.WBCabinet.calculated_bonus',
                   new_callable=MagicMock) as mock_bonus:
            # Устанавливаем возвращаемые значения для calculated_bonus
            mock_bonus.__get__ = MagicMock(return_value=0.0)

            # Вызываем функцию сброса бонусов
            await reset_bonus("test_shop", 1, "Тестовое обнуление бонусов")

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
async def test_get_cabinet_bonus(mock_test_db_session,
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
        bonus = await get_wb_cabinet_by_shop_id("test_shop")

        # Проверяем, что возвращается правильное значение бонуса
        assert bonus == initial_bonus


@pytest.mark.asyncio
async def test_subtract_bonus_insufficient_funds(mock_test_db_session,
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
            await subtract_bonus('test_shop',
                                 1000.0,
                                 1,
                                 "Тестовое вычитание бонусов")


# Фикстуры для тестирования обработчиков
@pytest.fixture
def mock_message() -> AsyncMock:
    """Фикстура для имитации сообщения от пользователя"""
    message = AsyncMock()
    message.from_user.id = 123456789  # ID администратора
    message.text = None
    # Делаем методы отправки сообщений AsyncMock
    message.answer = AsyncMock()
    message.reply = AsyncMock()
    return message


@pytest.fixture
def mock_callback_query() -> AsyncMock:
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

    # Создаем отдельные асинхронные моки для каждого метода
    state.update_data = AsyncMock()
    state.get_data = AsyncMock()
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    state.current_state = None

    # Настраиваем поведение моков
    async def _update_data(*args, **kwargs):
        if args and isinstance(args[0], dict):
            # Если первый аргумент - словарь, обновляем данные из него
            state_data.update(args[0])
        else:
            # Иначе используем именованные аргументы
            state_data.update(kwargs)
        return None

    async def _get_data():
        return state_data

    async def _set_state(new_state=None):
        state.current_state = new_state
        return None

    async def _clear():
        state_data.clear()
        state.current_state = None
        return None

    # Привязываем реализацию к мокам
    state.update_data.side_effect = _update_data
    state.get_data.side_effect = _get_data
    state.set_state.side_effect = _set_state
    state.clear.side_effect = _clear

    return state


# Тесты для обработчиков из handlers.py
@pytest.mark.asyncio
async def test_process_shop_id_valid(mock_message, mock_state) -> None:
    """Тест обработки правильного shop_id"""
    shop_id = "test_shop"
    current_bonus = 500.0

    # Устанавливаем текст сообщения
    mock_message.text = shop_id

    # Мокаем функцию get_cabinet_bonus - используем AsyncMock вместо MagicMock
    with patch('app.modules.cabinet_bonus_manager.main_handler.get_wb_cabinet',
               new_callable=AsyncMock, return_value=MagicMock(
                calculated_bonus=current_bonus, calculated_balance=1000.0)
               ) as mock_get_bonus:
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

    # Мокаем функцию get_cabinet_bonus
    with patch('app.modules.cabinet_bonus_manager.main_handler.get_wb_cabinet',
               new_callable=AsyncMock, return_value=None) as mock_get_bonus:
        # Вызываем тестируемую функцию
        await process_shop_id(mock_message, mock_state)

        # Проверяем, что функция get_cabinet_bonus была вызвана с правильным shop_id
        mock_get_bonus.assert_called_once_with(shop_id)

        # Проверяем, что пользователю было отправлено сообщение об ошибке
        mock_message.answer.assert_called_once()
        args, kwargs = mock_message.answer.call_args
        assert f"Кабинет с shop_id {shop_id} не найден" in args[0]


@pytest.mark.asyncio
async def test_process_shop_bonus_callback_add(mock_test_db_session,
                                              mock_user, mock_wb_cabinet, mock_callback_query, mock_state):
    # Настраиваем callback_data
    mock_callback_query.data = "shop_bonus_add_test_shop"
    
    # Настраиваем состояние
    await mock_state.update_data({
        "shop_id": "test_shop",
        "current_bonus": 100.0,
        "current_balance": 1000.0
    })

    # Вызываем функцию
    await process_shop_bonus_callback(mock_callback_query, mock_state)

    # Проверяем, что состояние обновлено
    state_data = await mock_state.get_data()
    assert state_data["operation"] == "add"

    # Проверяем, что установлено новое состояние
    mock_state.set_state.assert_called_once_with(BonusManagerStateGroup.waiting_for_amount)

    # Проверяем, что сообщение обновлено
    mock_callback_query.message.edit_text.assert_called_once()
    edit_text_args = mock_callback_query.message.edit_text.call_args[0][0]
    assert "Введите сумму для пополнения бонусов:" in edit_text_args


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
    assert mock_state.current_state == BonusManagerStateGroup.waiting_for_description

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
    assert mock_state.current_state == BonusManagerStateGroup.waiting_for_description

    # Проверяем, что пользователю было отправлено сообщение для ввода описания
    mock_message.answer.assert_called_once()
    args, kwargs = mock_message.answer.call_args
    assert "Введите описание операции" in args[0]


@pytest.mark.asyncio
async def test_process_confirm_callback(mock_callback_query, mock_state) -> None:
    """Тест обработки callback подтверждения операции"""
    # Устанавливаем callback_data в правильном формате: bonus_confirm_{operation}_{shop_id}_{amount}
    mock_callback_query.data = "bonus_confirm_add_test-shop_100.0"

    # Подготавливаем данные состояния
    await mock_state.update_data(
        shop_id="test-shop",
        amount=100.0,
        operation="add",
        description="Тестовое описание"
    )

    # Мокаем функции для операций с бонусами
    with patch('app.modules.cabinet_bonus_manager.main_handler.add_bonus',
               new_callable=AsyncMock, return_value=True) as mock_add_bonus, \
            patch('app.modules.cabinet_bonus_manager.main_handler.subtract_bonus',
                  new_callable=AsyncMock) as mock_subtract_bonus, \
            patch('app.modules.cabinet_bonus_manager.main_handler.reset_bonus',
                  new_callable=AsyncMock) as mock_reset_bonus, \
            patch('app.modules.cabinet_bonus_manager.main_handler.get_wb_cabinet',
                  new_callable=AsyncMock) as mock_get_wb_cabinet:
        
        # Настраиваем return_value для get_wb_cabinet
        mock_cabinet = MagicMock()
        mock_cabinet.calculated_bonus = 200.0
        mock_cabinet.calculated_balance = 1000.0
        mock_get_wb_cabinet.return_value = mock_cabinet
        
        # Вызываем тестируемую функцию
        await process_confirm_callback(mock_callback_query, mock_state)

        # Проверяем, что была вызвана правильная функция с правильными параметрами
        mock_add_bonus.assert_called_once_with(
            "test-shop", 100.0, mock_callback_query.from_user.id, "Тестовое описание"
        )
        mock_subtract_bonus.assert_not_called()
        mock_reset_bonus.assert_not_called()

        # Проверяем, что состояние было обновлено
        data = await mock_state.get_data()
        assert data.get("current_bonus") == 200.0
        assert data.get("current_balance") == 1000.0
        
        # Проверяем, что состояние было сброшено
        assert mock_state.set_state.called

        # Проверяем отправку сообщения пользователю
        assert mock_callback_query.message.edit_text.called
