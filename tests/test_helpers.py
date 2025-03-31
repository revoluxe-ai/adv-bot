import os
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from aiogram.fsm.context import FSMContext

# Устанавливаем фиктивный токен в переменные окружения, если еще не установлен
if "TELEGRAM_BOT_TOKEN" not in os.environ:
    os.environ["TELEGRAM_BOT_TOKEN"] = "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk"

# Теперь безопасно импортировать Bot
from aiogram import Bot

# Создаем мок для Bot и патчим его
mock_bot = AsyncMock()
patch('aiogram.Bot', return_value=mock_bot).start()
patch('app.client_bot.bot.bot', new=mock_bot).start()

@pytest.fixture
def mock_bot():
    """Создает мок для бота."""
    return AsyncMock()

@pytest.fixture
def mock_message():
    """Создает мок для сообщения от пользователя."""
    message = MagicMock()
    message.chat = MagicMock()
    message.chat.id = 123456789
    message.from_user = MagicMock()
    message.from_user.id = 123456789
    message.from_user.username = "test_user"
    return message

@pytest.fixture
def mock_callback_query():
    """Создает мок для callback query от пользователя."""
    callback = MagicMock()
    callback.message = MagicMock()
    callback.message.chat = MagicMock()
    callback.message.chat.id = 123456789
    callback.from_user = MagicMock()
    callback.from_user.id = 123456789
    return callback

@pytest.fixture
def mock_state():
    """Создает мок для состояния FSM."""
    state = MagicMock(spec=FSMContext)
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.clear = AsyncMock()
    return state

def import_module_with_mocked_bot(module_path):
    """
    Импортирует модуль, предварительно создав моки для бота и связанных объектов.
    
    Args:
        module_path (str): Путь к модулю для импорта, например 'app.client_bot.user_interface.handlers.start'
    
    Returns:
        module: Импортированный модуль
    """
    # Создаем временный мок для бота
    temp_mock_bot = AsyncMock()
    
    with patch('aiogram.client.bot.Bot', return_value=temp_mock_bot), \
         patch('app.client_bot.bot.bot', new=temp_mock_bot):
        return __import__(module_path, fromlist=['*']) 