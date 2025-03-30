from datetime import datetime
import dotenv
import sys, os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select
from app.modules.cabinet_bonus_manager.bonus_service import add_bonus, subtract_bonus, reset_bonus, get_wb_cabinet_by_shop_id, get_cabinet_by_id
from app.modules.cabinet_bonus_manager.bonus_scene import BonusScene
from app.modules.cabinet_bonus_manager.callbacks import AdminBonus
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
            result = await subtract_bonus(
                            mock_wb_cabinet.id,
                            50.0,
                            1,
                            "Тестовое вычитание бонусов")
                            
            assert result is True

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
            result = await reset_bonus(
                            mock_wb_cabinet.id,
                            1,
                            "Тестовое обнуление бонусов")
                            
            assert result is True

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
async def test_get_cabinet_by_id(mock_test_db_session,
                                 mock_user, mock_wb_cabinet, cabinet_bonus_session_mocker):
    # Вызываем функцию получения кабинета по ID
    cabinet = await get_cabinet_by_id(mock_wb_cabinet.id)

    # Проверяем, что получен правильный кабинет
    assert cabinet is not None
    assert cabinet.id == mock_wb_cabinet.id


@pytest.mark.asyncio
async def test_get_wb_cabinet_by_shop_id(mock_test_db_session,
                                         mock_user, mock_wb_cabinet, cabinet_bonus_session_mocker):
    # Вызываем функцию получения кабинета по shop_id
    cabinet = await get_wb_cabinet_by_shop_id(mock_wb_cabinet.shop_id)

    # Проверяем, что получен правильный кабинет
    assert cabinet is not None
    assert cabinet.shop_id == mock_wb_cabinet.shop_id


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
            await subtract_bonus(mock_wb_cabinet.id,
                               1000.0,
                               1,
                               "Тестовое вычитание бонусов")


# Фикстуры для тестирования обработчиков сцены BonusScene
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


@pytest.fixture
def mock_scene_wizard():
    """Фикстура для имитации SceneWizard"""
    wizard = AsyncMock()
    wizard.exit = AsyncMock()
    return wizard


@pytest.fixture
def mock_bonus_scene(mock_scene_wizard):
    """Фикстура для создания экземпляра BonusScene"""
    scene = BonusScene(mock_scene_wizard)
    return scene


@pytest.mark.asyncio
async def test_bonus_scene_enter(mock_message, mock_state, mock_bonus_scene):
    """Тест входа в сцену управления бонусами"""
    # Вызываем метод входа в сцену
    await mock_bonus_scene.enter_scene(mock_message, mock_state)
    
    # Проверяем, что состояние обновлено
    assert mock_bonus_scene.state_context is mock_state
    
    # Проверяем, что данные состояния обновлены
    data = await mock_state.get_data()
    assert data.get("action") == "menu"
    
    # Проверяем, что отправлено сообщение
    mock_message.answer.assert_called_once_with("Введите shop_id кабинета для управления бонусами:")


@pytest.mark.asyncio
async def test_bonus_scene_enter_from_callback(mock_callback_query, mock_state, mock_bonus_scene, mock_bot):
    """Тест входа в сцену управления бонусами через callback"""
    # Вызываем метод входа в сцену через callback
    await mock_bonus_scene.enter_scene_from_callback(mock_callback_query, mock_bot, mock_state)
    
    # Проверяем, что состояние обновлено
    assert mock_bonus_scene.state_context is mock_state
    
    # Проверяем, что данные состояния обновлены
    data = await mock_state.get_data()
    assert data.get("action") == "menu"
    
    # Проверяем, что отправлено сообщение
    mock_bot.send_message.assert_called_once_with(
        mock_callback_query.from_user.id, 
        "Введите shop_id кабинета для управления бонусами:"
    )


@pytest.mark.asyncio
async def test_process_shop_id_valid(mock_message, mock_state, mock_bonus_scene):
    """Тест обработки правильного shop_id в BonusScene"""
    shop_id = "test_shop"
    current_bonus = 500.0
    current_balance = 1000.0
    cabinet_id = 1

    # Устанавливаем текст сообщения
    mock_message.text = shop_id

    # Настраиваем состояние
    await mock_state.update_data(action="menu")
    mock_bonus_scene.state_context = mock_state

    # Мокаем функцию get_wb_cabinet_by_shop_id
    mock_cabinet = AsyncMock()
    mock_cabinet.id = cabinet_id
    mock_cabinet.calculated_bonus = current_bonus
    mock_cabinet.calculated_balance = current_balance

    with patch('app.modules.cabinet_bonus_manager.bonus_scene.get_wb_cabinet_by_shop_id',
               new_callable=AsyncMock, return_value=mock_cabinet):
        
        # Вызываем тестируемую функцию
        await mock_bonus_scene.process_shop_id(mock_message, mock_state)

        # Проверяем, что в состояние были сохранены правильные данные
        data = await mock_state.get_data()
        assert data.get("shop_id") == shop_id
        assert data.get("cabinet_id") == cabinet_id
        assert data.get("wb_cabinet_original_id") == cabinet_id
        assert data.get("current_bonus") == current_bonus
        assert data.get("current_balance") == current_balance

        # Проверяем, что пользователю было отправлено сообщение
        mock_message.answer.assert_called_once()
        args = mock_message.answer.call_args[0]
        assert f"🏪 Магазин: {shop_id}" in args[0]
        assert f"💰 Текущий баланс: {current_balance:.0f} руб." in args[0]
        assert f"🎁 Текущие бонусы: {current_bonus:.0f} руб." in args[0]


@pytest.mark.asyncio
async def test_process_shop_id_invalid(mock_message, mock_state, mock_bonus_scene):
    """Тест обработки несуществующего shop_id в BonusScene"""
    shop_id = "nonexistent_shop"

    # Устанавливаем текст сообщения
    mock_message.text = shop_id

    # Настраиваем состояние
    await mock_state.update_data(action="menu")
    mock_bonus_scene.state_context = mock_state

    # Мокаем функцию get_wb_cabinet_by_shop_id
    with patch('app.modules.cabinet_bonus_manager.bonus_scene.get_wb_cabinet_by_shop_id',
               new_callable=AsyncMock, return_value=None):
        
        # Вызываем тестируемую функцию
        await mock_bonus_scene.process_shop_id(mock_message, mock_state)

        # Проверяем, что пользователю было отправлено сообщение об ошибке
        mock_message.answer.assert_called_once()
        args = mock_message.answer.call_args[0]
        assert f"Кабинет с shop_id {shop_id} не найден" in args[0]


@pytest.mark.asyncio
async def test_process_shop_bonus_callback_add(mock_callback_query, mock_state, mock_bonus_scene):
    """Тест обработки callback для добавления бонусов"""
    # Создаем callback_data
    callback_data = AdminBonus(action="add")
    
    # Настраиваем состояние
    await mock_state.update_data({
        "shop_id": "test_shop",
        "current_bonus": 100.0,
        "current_balance": 1000.0
    })
    mock_bonus_scene.state_context = mock_state

    # Вызываем функцию
    await mock_bonus_scene.process_shop_bonus_callback(mock_callback_query, callback_data, mock_state)

    # Проверяем, что состояние обновлено
    state_data = await mock_state.get_data()
    assert state_data["operation"] == "add"
    assert state_data["action"] == "amount"

    # Проверяем, что сообщение обновлено
    mock_callback_query.message.edit_text.assert_called_once()
    edit_text_args = mock_callback_query.message.edit_text.call_args[0][0]
    assert "Введите сумму для пополнения бонусов:" in edit_text_args


@pytest.mark.asyncio
async def test_process_shop_bonus_callback_reset(mock_callback_query, mock_state, mock_bonus_scene):
    """Тест обработки callback для обнуления бонусов"""
    # Создаем callback_data
    callback_data = AdminBonus(action="reset")
    
    # Настраиваем состояние
    await mock_state.update_data({
        "shop_id": "test_shop",
        "current_bonus": 100.0,
        "current_balance": 1000.0
    })
    mock_bonus_scene.state_context = mock_state

    # Вызываем функцию
    await mock_bonus_scene.process_shop_bonus_callback(mock_callback_query, callback_data, mock_state)

    # Проверяем, что состояние обновлено
    state_data = await mock_state.get_data()
    assert state_data["operation"] == "reset"
    assert state_data["action"] == "description"

    # Проверяем, что сообщение обновлено
    mock_callback_query.message.edit_text.assert_called_once()
    edit_text_args = mock_callback_query.message.edit_text.call_args[0][0]
    assert "Введите описание операции обнуления:" in edit_text_args


@pytest.mark.asyncio
async def test_process_cancel_callback(mock_callback_query, mock_state, mock_bonus_scene):
    """Тест обработки callback для отмены операции"""
    # Настраиваем состояние
    await mock_state.update_data({
        "shop_id": "test_shop",
        "current_bonus": 100.0,
        "current_balance": 1000.0,
        "wb_cabinet_original_id": 1
    })
    mock_bonus_scene.state_context = mock_state

    # Вызываем функцию
    await mock_bonus_scene.process_cancel_callback(mock_callback_query, mock_state)

    # Проверяем, что состояние обновлено
    state_data = await mock_state.get_data()
    assert state_data["action"] == "menu"

    # Проверяем, что сообщение обновлено
    mock_callback_query.message.edit_text.assert_called_once()
    edit_text_args = mock_callback_query.message.edit_text.call_args[0][0]
    assert "Операция отменена. Выберите действие:" in edit_text_args


@pytest.mark.asyncio
async def test_wizard_exit(mock_state, mock_bonus_scene):
    """Тест метода выхода из сцены"""
    # Устанавливаем состояние
    await mock_state.update_data({
        "shop_id": "test_shop",
        "current_bonus": 100.0,
        "current_balance": 1000.0
    })
    mock_bonus_scene.state_context = mock_state
    
    # Вызываем метод выхода с сохранением данных
    await mock_bonus_scene.wizard_exit(with_data=True)
    
    # Проверяем, что был вызван метод выхода из SceneWizard
    mock_bonus_scene.wizard.exit.assert_called_once()
    
    # Проверяем, что данные сохранены
    data = await mock_state.get_data()
    assert data.get("shop_id") == "test_shop"
    assert data.get("current_bonus") == 100.0
    assert data.get("current_balance") == 1000.0


@pytest.mark.asyncio
async def test_wizard_exit_without_data(mock_state, mock_bonus_scene):
    """Тест метода выхода из сцены без сохранения данных"""
    # Устанавливаем состояние
    await mock_state.update_data({
        "shop_id": "test_shop",
        "current_bonus": 100.0,
        "current_balance": 1000.0
    })
    mock_bonus_scene.state_context = mock_state
    
    # Вызываем метод выхода без сохранения данных
    await mock_bonus_scene.wizard_exit(with_data=False)
    
    # Проверяем, что был вызван метод выхода из SceneWizard
    mock_bonus_scene.wizard.exit.assert_called_once()


@pytest.fixture
def mock_bot() -> AsyncMock:
    """Фикстура для имитации объекта Bot"""
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    return bot


@pytest.mark.asyncio
async def test_process_confirm_callback(mock_callback_query, mock_state, mock_bonus_scene):
    """Тест обработки callback для подтверждения операции"""
    # Создаем callback_data для операции добавления бонусов
    callback_data = AdminBonus(
        action="confirm",
        operation="add",
        wb_cabinet_original_id=1,
        amount=100.0
    )
    
    # Настраиваем состояние
    await mock_state.update_data({
        "shop_id": "test_shop",
        "description": "Тестовое описание",
        "wb_cabinet_original_id": 1
    })
    mock_bonus_scene.state_context = mock_state
    
    # Мокаем функции операций с бонусами и получения кабинета
    with patch('app.modules.cabinet_bonus_manager.bonus_scene.add_bonus',
               new_callable=AsyncMock, return_value=True) as mock_add_bonus, \
         patch('app.modules.cabinet_bonus_manager.bonus_scene.get_cabinet_by_id',
               new_callable=AsyncMock) as mock_get_cabinet:
        
        # Настраиваем возвращаемое значение для get_cabinet_by_id
        mock_cabinet = MagicMock()
        mock_cabinet.calculated_bonus = 200.0
        mock_cabinet.calculated_balance = 1000.0
        mock_get_cabinet.return_value = mock_cabinet
        
        # Вызываем функцию
        await mock_bonus_scene.process_confirm_callback(mock_callback_query, callback_data, mock_state)
        
        # Проверяем, что была вызвана функция add_bonus
        mock_add_bonus.assert_called_once_with(
            1, 100.0, mock_callback_query.from_user.id, "Тестовое описание"
        )
        
        # Проверяем, что было получено новое состояние кабинета
        mock_get_cabinet.assert_called_once_with(1)
        
        # Проверяем, что состояние обновлено
        state_data = await mock_state.get_data()
        assert state_data["current_bonus"] == 200.0
        assert state_data["current_balance"] == 1000.0
        assert state_data["action"] == "menu"
        
        # Проверяем, что сообщение обновлено
        mock_callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_process_confirm_callback_reset(mock_callback_query, mock_state, mock_bonus_scene):
    """Тест обработки callback для подтверждения операции обнуления"""
    # Создаем callback_data для операции обнуления бонусов
    callback_data = AdminBonus(
        action="confirm",
        operation="reset",
        wb_cabinet_original_id=1,
        amount=None
    )
    
    # Настраиваем состояние
    await mock_state.update_data({
        "shop_id": "test_shop",
        "description": "Тестовое обнуление",
        "wb_cabinet_original_id": 1
    })
    mock_bonus_scene.state_context = mock_state
    
    # Мокаем функции операций с бонусами и получения кабинета
    with patch('app.modules.cabinet_bonus_manager.bonus_scene.reset_bonus',
               new_callable=AsyncMock, return_value=True) as mock_reset_bonus, \
         patch('app.modules.cabinet_bonus_manager.bonus_scene.get_cabinet_by_id',
               new_callable=AsyncMock) as mock_get_cabinet:
        
        # Настраиваем возвращаемое значение для get_cabinet_by_id
        mock_cabinet = MagicMock()
        mock_cabinet.calculated_bonus = 0.0
        mock_cabinet.calculated_balance = 1000.0
        mock_get_cabinet.return_value = mock_cabinet
        
        # Вызываем функцию
        await mock_bonus_scene.process_confirm_callback(mock_callback_query, callback_data, mock_state)
        
        # Проверяем, что была вызвана функция reset_bonus
        mock_reset_bonus.assert_called_once_with(
            1, mock_callback_query.from_user.id, "Тестовое обнуление"
        )
        
        # Проверяем, что было получено новое состояние кабинета
        mock_get_cabinet.assert_called_once_with(1)
        
        # Проверяем, что состояние обновлено
        state_data = await mock_state.get_data()
        assert state_data["current_bonus"] == 0.0
        assert state_data["current_balance"] == 1000.0
        assert state_data["action"] == "menu"
        
        # Проверяем, что сообщение обновлено
        mock_callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_cmd_check_bonus(mock_message, mock_state, mock_bonus_scene):
    """Тест команды проверки бонусов кабинета"""
    # Вызываем обработчик команды
    await mock_bonus_scene.cmd_check_bonus(mock_message, mock_state)
    
    # Проверяем, что состояние обновлено
    state_data = await mock_state.get_data()
    assert state_data["action"] == "check_bonus"
    
    # Проверяем, что отправлено сообщение
    mock_message.answer.assert_called_once_with("Введите shop_id кабинета для проверки бонусов:")


@pytest.mark.asyncio
async def test_handle_start_command(mock_message, mock_state, mock_bonus_scene):
    """Тест обработки команды /start"""
    # Вызываем обработчик команды
    await mock_bonus_scene.handle_start_command(mock_message, mock_state)
    
    # Проверяем, что состояние очищено
    mock_state.clear.assert_called_once()
    
    # Проверяем, что произошел выход из сцены
    mock_bonus_scene.wizard.exit.assert_called_once()


@pytest.mark.asyncio
async def test_process_shop_id_check_bonus(mock_message, mock_state, mock_bonus_scene):
    """Тест обработки shop_id при проверке бонусов"""
    # Устанавливаем текст для сообщения
    mock_message.text = "test_shop"
    
    # Устанавливаем состояние на check_bonus
    await mock_state.update_data({"action": "check_bonus"})
    
    # Мокаем функцию получения кабинета по shop_id
    with patch('app.modules.cabinet_bonus_manager.bonus_scene.get_wb_cabinet_by_shop_id',
               new_callable=AsyncMock) as mock_get_cabinet:
        # Настраиваем возвращаемое значение для get_wb_cabinet_by_shop_id
        mock_cabinet = MagicMock()
        mock_cabinet.id = 1
        mock_cabinet.calculated_bonus = 100.0
        mock_cabinet.calculated_balance = 1000.0
        mock_get_cabinet.return_value = mock_cabinet
        
        # Вызываем функцию
        await mock_bonus_scene.process_shop_id(mock_message, mock_state)
        
        # Проверяем, что была вызвана функция get_wb_cabinet_by_shop_id
        mock_get_cabinet.assert_called_once_with("test_shop")
        
        # Проверяем, что состояние обновлено
        state_data = await mock_state.get_data()
        assert state_data["shop_id"] == "test_shop"
        assert state_data["cabinet_id"] == 1
        assert state_data["wb_cabinet_original_id"] == 1
        assert state_data["current_bonus"] == 100.0
        assert state_data["current_balance"] == 1000.0
        assert state_data["action"] == "menu"
        
        # Проверяем, что отправлено сообщение с правильными данными
        mock_message.answer.assert_called_once()
        args, kwargs = mock_message.answer.call_args
        
        # Проверяем содержимое сообщения
        assert "🏪 Магазин: test_shop" in args[0]
        assert "💰 Текущий баланс: 1000 руб." in args[0]
        assert "🎁 Текущие бонусы: 100 руб." in args[0]
        assert "Выберите операцию:" in args[0]
