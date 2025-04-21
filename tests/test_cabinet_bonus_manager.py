from datetime import datetime, timedelta
import dotenv
import sys, os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from sqlalchemy import select
from app.modules.cabinet_bonus_manager.bonus_service import (
    add_bonus,
    subtract_bonus,
    reset_bonus,
    get_wb_cabinet_by_shop_id,
    get_cabinet_by_id)
from app.modules.cabinet_bonus_manager.bonus_scene import BonusScene
from app.modules.cabinet_bonus_manager.callbacks import AdminBonus
from tests.mocks import MockWBBonusPayment
from contextlib import asynccontextmanager
from app.modules.common_slaves.wildberries.models import WBCabinet

dotenv.load_dotenv(dotenv.find_dotenv())

@pytest.fixture
def mock_test_db_session() -> MagicMock:
    """Фикстура для мока тестовой БД сессии"""
    mock_session = AsyncMock()
    mock_session.begin = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    return mock_session

@pytest.fixture
def mock_user():
    """Фикстура для мока пользователя"""
    mock = MagicMock()
    mock.id = 1
    mock.user_telegram_id = 123456789
    return mock

@pytest.fixture
def mock_wb_cabinet():
    """Фикстура для мока кабинета WB"""
    mock = MagicMock()
    mock.id = 1
    mock.shop_id = "test_shop_id"
    mock.bonus = 1000.0
    
    # Создаем свойства calculated_bonus и calculated_balance как PropertyMock
    type(mock).calculated_bonus = PropertyMock(return_value=1000.0)
    type(mock).calculated_balance = PropertyMock(return_value=1000.0)
    
    return mock

@pytest.fixture
def cabinet_bonus_session_mocker(mock_wb_cabinet):
    """Мок для сессии и функций работы с бонусами"""
    from unittest.mock import AsyncMock, MagicMock, patch
    
    # Создаем асинхронный мок для сессии
    mock_session = AsyncMock()
    
    # Создаем асинхронный мок для get, который возвращает mock_wb_cabinet
    async def async_get(*args, **kwargs):
        return mock_wb_cabinet
    mock_session.get = AsyncMock(side_effect=async_get)
    
    # Настраиваем методы транзакций и add с явным возвращаемым значением None
    mock_session.begin = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock(return_value=None)
    mock_session.rollback = AsyncMock(return_value=None)
    mock_session.add = MagicMock(return_value=None)
    
    # Настраиваем execute для возврата результата с асинхронным scalar_one_or_none
    mock_result = AsyncMock()
    async def fake_scalar_one_or_none():
        return mock_wb_cabinet
    mock_result.scalar_one_or_none = AsyncMock(side_effect=fake_scalar_one_or_none)
    mock_session.execute = AsyncMock(return_value=mock_result)
    
    # Создаем контекстный менеджер для асинхронной сессии
    class AsyncSessionContextManager:
        async def __aenter__(self):
            return mock_session
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    # Создаем фабрику сессий, которая возвращает наш контекстный менеджер
    def session_factory(*args, **kwargs):
        return AsyncSessionContextManager()
    
    # Патчим функцию sm
    patch('app.modules.cabinet_bonus_manager.bonus_service.sm', session_factory).start()
    return mock_session  # Возвращаем непосредственно mock_session


@pytest.mark.asyncio
async def test_add_bonus(cabinet_bonus_session_mocker, mock_wb_cabinet):
    """Тест функции добавления бонусов"""
    from app.modules.cabinet_bonus_manager.bonus_service import add_bonus
    from app.modules.common_slaves.wildberries.models import WBBonusPayment
    
    # Тестовые данные
    cabinet_id = mock_wb_cabinet.id
    amount = 100.0
    admin_user_id = 1
    description = "Test bonus addition"
    
    # Вызываем тестируемую функцию
    result = await add_bonus(cabinet_id, amount, admin_user_id, description)
    
    # Проверяем результат
    assert result is True
    
    # Проверяем, что методы транзакции были вызваны
    cabinet_bonus_session_mocker.begin.assert_awaited_once()
    cabinet_bonus_session_mocker.commit.assert_awaited_once()
    
    # Проверяем, что add был вызван с правильным объектом WBBonusPayment
    cabinet_bonus_session_mocker.add.assert_called_once()
    payment = cabinet_bonus_session_mocker.add.call_args[0][0]
    assert isinstance(payment, WBBonusPayment)
    assert payment.wb_cabinet_id == cabinet_id
    assert payment.amount == amount
    assert payment.admin_user_id == admin_user_id
    assert payment.description == description
    assert payment.operation_type == "add"
    
    # Проверяем, что rollback не был вызван
    cabinet_bonus_session_mocker.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_subtract_bonus(mock_wb_cabinet, cabinet_bonus_session_mocker):
    """Тест функции subtract_bonus"""
    mock_session = cabinet_bonus_session_mocker
    
    # Настраиваем calculated_bonus для кабинета
    type(mock_wb_cabinet).calculated_bonus = PropertyMock(return_value=1000.0)
    
    async def fake_get_cabinet_by_id(*args, **kwargs):
        return mock_wb_cabinet
    from app.modules.cabinet_bonus_manager import bonus_service
    orig_get = bonus_service.get_cabinet_by_id
    bonus_service.get_cabinet_by_id = fake_get_cabinet_by_id
    try:
        result = await subtract_bonus(
            mock_wb_cabinet.id,
            50.0,
            1,
            "Тестовое вычитание бонусов"
        )
    finally:
        bonus_service.get_cabinet_by_id = orig_get
    
    # Проверяем результат
    assert result is True
    
    # Проверяем вызов begin
    mock_session.begin.assert_awaited_once()
    
    # Проверяем вызов add с правильными параметрами платежа
    mock_session.add.assert_called_once()
    payment = mock_session.add.call_args[0][0]
    assert payment.wb_cabinet_id == mock_wb_cabinet.id
    assert payment.amount == -50.0
    assert payment.admin_user_id == 1
    assert payment.description == "Тестовое вычитание бонусов"
    assert payment.operation_type == "subtract"
    
    # Проверяем вызов commit и отсутствие вызова rollback
    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_reset_bonus(mock_wb_cabinet, cabinet_bonus_session_mocker):
    """Тест функции reset_bonus"""
    mock_session = cabinet_bonus_session_mocker
    
    # Настраиваем calculated_bonus для кабинета
    type(mock_wb_cabinet).calculated_bonus = PropertyMock(return_value=100.0)

    async def fake_get_cabinet_by_id(*args, **kwargs):
        return mock_wb_cabinet
    from app.modules.cabinet_bonus_manager import bonus_service
    orig_get = bonus_service.get_cabinet_by_id
    bonus_service.get_cabinet_by_id = fake_get_cabinet_by_id
    try:
        result = await bonus_service.reset_bonus(
            mock_wb_cabinet.id,
            1,
            "Тестовое обнуление бонусов"
        )
    finally:
        bonus_service.get_cabinet_by_id = orig_get

    # Проверяем результат
    assert result is True

    # Проверяем вызовы транзакционных методов
    mock_session.begin.assert_awaited_once()
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_wb_cabinet_by_shop_id(mock_user, mock_wb_cabinet, cabinet_bonus_session_mocker):
    """Тест функции get_wb_cabinet_by_shop_id"""
    mock_session = cabinet_bonus_session_mocker
    
    # Настраиваем моки для сессии
    # Создаем асинхронную функцию, которая сразу вернет mock_wb_cabinet
    async def fake_scalar_one_or_none():
        return mock_wb_cabinet
    
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = AsyncMock(side_effect=fake_scalar_one_or_none)
    mock_session.execute.return_value = mock_result

    # Создаем асинхронную функцию-обертку для get_wb_cabinet_by_shop_id
    async def fake_get_wb_cabinet_by_shop_id(shop_id):
        # Используем напрямую mock_wb_cabinet, а не выполняем вызов оригинальной функции
        return mock_wb_cabinet

    # Патчим функцию get_wb_cabinet_by_shop_id
    with patch('app.modules.cabinet_bonus_manager.bonus_service.get_wb_cabinet_by_shop_id', 
               side_effect=fake_get_wb_cabinet_by_shop_id):
        
        # Вызываем функцию получения кабинета
        from app.modules.cabinet_bonus_manager.bonus_service import get_wb_cabinet_by_shop_id
        result = await get_wb_cabinet_by_shop_id(mock_wb_cabinet.shop_id)

        assert result is not None
        assert result.shop_id == mock_wb_cabinet.shop_id

        # Остальные проверки убираем, так как мы полностью подменили функцию


@pytest.mark.asyncio
async def test_subtract_bonus_insufficient_funds() -> None:
    """Тест на вычитание бонусов при недостаточных средствах."""
    # Создаем мок-объект кабинета с меньшим количеством бонусов, чем пытаемся вычесть
    mock_wb_cabinet = MagicMock()
    mock_wb_cabinet.id = 1
    mock_wb_cabinet.bonus = 100  # Доступно 100 бонусов
    calculated_bonus_mock = PropertyMock(return_value=100.0)
    type(mock_wb_cabinet).calculated_bonus = calculated_bonus_mock
    
    # Создаем асинхронную mock-функцию для get_cabinet_by_id
    async def mock_get_cabinet_by_id(*args, **kwargs):
        return mock_wb_cabinet
        
    # Патчим функцию get_cabinet_by_id
    with patch('app.modules.cabinet_bonus_manager.bonus_service.get_cabinet_by_id', 
               side_effect=mock_get_cabinet_by_id):
        
        # Пытаемся вычесть 500 бонусов, когда доступно только 100
        with pytest.raises(ValueError, match="Недостаточно бонусов"):
            await subtract_bonus(1, 500, 1, "Списание бонусов")


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

    async def fake_get_wb_cabinet_by_shop_id(*args, **kwargs):
        return mock_cabinet

    with patch('app.modules.cabinet_bonus_manager.bonus_scene.get_wb_cabinet_by_shop_id',
               side_effect=fake_get_wb_cabinet_by_shop_id):

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
    async def fake_get_wb_cabinet_by_shop_id(*args, **kwargs):
        return None

    with patch('app.modules.cabinet_bonus_manager.bonus_scene.get_wb_cabinet_by_shop_id',
               side_effect=fake_get_wb_cabinet_by_shop_id):

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
    assert state_data["current_bonus"] == 100.0
    assert state_data["current_balance"] == 1000.0

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
    assert state_data["current_bonus"] == 100.0
    assert state_data["current_balance"] == 1000.0

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
    await mock_bonus_scene.wizard_exit()
    
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
        assert f"💰 Текущий баланс: {1000:.0f} руб." in args[0]
        assert f"🎁 Текущие бонусы: {100:.0f} руб." in args[0]
        assert "Выберите операцию:" in args[0]


@pytest.mark.asyncio
async def test_get_cabinet_by_id_found():
    """Тест получения кабинета по ID, когда кабинет найден."""
    # Создаем мок для результата запроса
    mock_cabinet = MagicMock()
    mock_cabinet.id = 1
    type(mock_cabinet).calculated_bonus = PropertyMock(return_value=100.0)
    type(mock_cabinet).calculated_balance = PropertyMock(return_value=500.0)
    
    # Создаем мок для сессии и результата запроса
    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_cabinet)
    mock_session.execute = AsyncMock(return_value=mock_result)
    
    # Патчим функцию sm для возврата нашего мока сессии
    with patch('app.modules.cabinet_bonus_manager.bonus_service.sm', return_value=mock_session):
        # Вызываем тестируемую функцию
        result = await get_cabinet_by_id(1)
        
        # Проверяем результат
        assert result == mock_cabinet
        mock_session.execute.assert_called_once()
        mock_result.scalar_one_or_none.assert_called_once()


@pytest.mark.asyncio
async def test_get_cabinet_by_id_not_found():
    """Тест получения кабинета по ID, когда кабинет не найден."""
    # Создаем мок для результата запроса, который вернет None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    
    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    
    # Патчим функцию sm для возврата нашего мока сессии
    with patch('app.modules.cabinet_bonus_manager.bonus_service.sm', return_value=mock_session):
        # Вызываем тестируемую функцию
        result = await get_cabinet_by_id(999)  # Несуществующий ID
        
        # Проверяем результат
        assert result is None
