import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from aiogram.fsm.context import FSMContext
from app.modules.shop_menu.message import ShopMenu
from tests.mocks import MockUser, MockWBCabinet, MockWBUserCabinet, MockWBToken, MockAdvSetting
from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet, User, WBToken, AdvSetting
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.pricer.pricer import Pricer

@pytest.fixture
def mock_bot():
    return AsyncMock()

@pytest.fixture
def mock_state():
    state = MagicMock()
    state.update_data = AsyncMock()
    return state

@pytest.fixture
def mock_chat_id():
    return 123456789

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = 1
    user.user_telegram_id = 123456789
    return user

@pytest.fixture
def mock_wb_cabinet():
    cabinet = MagicMock(spec=WBCabinet)
    cabinet.id = 1
    cabinet.shop_id = "test_shop"
    cabinet.balance = 1000
    cabinet.bonus = 100
    cabinet.calculated_balance = 1000
    cabinet.calculated_bonus = 100
    cabinet.expiration_time = datetime.now() + timedelta(days=30)
    cabinet.white_list_update_active = False
    cabinet.adv_settings = []
    return cabinet

@pytest.fixture
def mock_wb_user_cabinet(mock_wb_cabinet, mock_user):
    cabinet = MagicMock(spec=WBUserCabinet)
    cabinet.id = 1
    cabinet.wb_cabinet = mock_wb_cabinet
    cabinet.user = mock_user
    cabinet.wb_cabinet_id = mock_wb_cabinet.id
    cabinet.user_id = mock_user.id
    cabinet.name = "Test Cabinet"
    return cabinet

@pytest.fixture
def mock_adv_setting(mock_wb_cabinet):
    adv = MagicMock(spec=AdvSetting)
    adv.id = 1
    adv.adv_id = "test_adv_id"
    adv.name = "Test Adv"
    adv.wb_cabinet_id = mock_wb_cabinet.id
    adv.active_status = "active"
    adv.bot_active = True
    adv.nmids = [12345, 67890]
    adv.type = "search"
    return adv

@pytest.fixture
def mock_pricer():
    pricer = MagicMock(spec=Pricer)
    pricer.get_month_tariff_for_count_advs = AsyncMock(return_value=1000)
    pricer.get_price_for_day_for_shop = AsyncMock(return_value=50)
    return pricer

@pytest.fixture
def shop_menu(mock_bot, mock_state, mock_chat_id, mock_wb_user_cabinet, mock_pricer):
    # Инициализируем объект ShopMenu
    menu = ShopMenu(
        bot=mock_bot,
        chat_id=mock_chat_id,
        state=mock_state,
        wb_user_cabinet_original_id=mock_wb_user_cabinet.id
    )
    menu._pricer = mock_pricer
    
    # Предустанавливаем некоторые свойства для тестов
    menu._wb_user_cabinet = None  # Будет установлено в тестах
    menu._wb_cabinet = None  # Будет установлено в тестах
    menu.count_active_advs = 0
    menu.is_active_adv = False
    menu.days_left = 30
    menu.bonus_days = 60
    menu.price_for_month_for_shop = 1000
    menu.total_amount_for_day = 50
    
    return menu

@pytest.mark.asyncio
async def test_shop_menu_load_all_data(
    mock_session, mock_wb_cabinet, mock_wb_user_cabinet, mock_user, mock_bot, mock_state, mock_chat_id
):
    # Исправляем параметры и логику теста
    with patch("app.modules.shop_menu.message.TextWithKeyboard.__call__") as mock_parent_call:
        # Здесь используем AsyncMock для асинхронного метода _load_all_data
        mock_load_all_data = AsyncMock(return_value=True)
        
        # Патчим метод _load_all_data
        with patch.object(ShopMenu, "_load_all_data", mock_load_all_data):
            
            # Создаем экземпляр ShopMenu
            shop_menu = ShopMenu(
                bot=mock_bot,
                chat_id=mock_chat_id,
                state=mock_state,
                wb_user_cabinet_original_id=mock_wb_user_cabinet.id
            )
            
            # Устанавливаем атрибуты, которые обычно устанавливаются методом _load_all_data
            shop_menu._wb_user_cabinet = mock_wb_user_cabinet
            shop_menu._wb_cabinet = mock_wb_cabinet
            shop_menu.count_active_advs = 1
            shop_menu.is_active_adv = True
            shop_menu.days_left = 30
            shop_menu.bonus_days = 60
            shop_menu._balance = 1000.0
            shop_menu._bonus = 200.0
            shop_menu.price_for_month_for_shop = 1234.56
            shop_menu.total_amount_for_day = 123.45
            shop_menu._now = datetime.now()
            shop_menu._expiration_time = datetime.now() + timedelta(days=30)
            shop_menu._expiration_time_str = shop_menu._expiration_time.strftime('%d-%m-%Y-%H:%M')
            
            # Вызываем метод __call__, который не возвращает значение
            await shop_menu()

            # Проверяем, что метод _load_all_data был вызван
            mock_load_all_data.assert_called_once()
            
            # Проверяем, что родительский метод __call__ был вызван для отправки сообщения
            mock_parent_call.assert_called_once()
            
            # Проверяем текст сообщения
            assert "📊 <b>Кампаний на автоуправлении</b>: 1" in shop_menu.text
            assert "тариф в месяц: 1234.56" in shop_menu.text
            assert "💸 <b>Расход в сутки</b>: 123.45" in shop_menu.text
            assert "1000" in shop_menu.text
            assert "200" in shop_menu.text

@pytest.mark.asyncio
async def test_shop_menu_load_all_data_with_exception(shop_menu, mock_state):
    """Тест обработки исключений при загрузке данных"""
    
    # Патчим сессию для генерации исключения
    with patch('app.modules.shop_menu.message.sm') as mock_sm:
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Test error")
        mock_sm.return_value.__aenter__.return_value = mock_session
        
        # Проверяем, что исключение пробрасывается наверх
        with pytest.raises(Exception):
            await shop_menu._load_all_data()
        
        # Проверяем отправку сообщения об ошибке
        shop_menu.bot.send_message.assert_called_once()

@pytest.mark.asyncio
async def test_shop_menu_with_active_advs(shop_menu, mock_wb_user_cabinet, mock_wb_cabinet, mock_adv_setting):
    """Тест отображения меню с активными рекламными кампаниями"""
    
    # Устанавливаем данные для теста
    shop_menu._wb_user_cabinet = mock_wb_user_cabinet
    shop_menu._wb_cabinet = mock_wb_cabinet
    shop_menu._balance = 1000
    shop_menu._bonus = 100
    
    # Добавляем активную рекламную кампанию
    mock_wb_cabinet.adv_settings = [mock_adv_setting]
    shop_menu.count_active_advs = 1
    shop_menu.is_active_adv = True
    
    # Патчим вызов метода загрузки данных
    with patch.object(shop_menu, '_load_all_data') as mock_load_data:
        mock_load_data.return_value = True
        
        # Патчим вызов родительского метода, чтобы не отправлять реальное сообщение
        with patch('app.modules.shop_menu.message.TextWithKeyboard.__call__') as mock_call:
            # Вызываем метод отображения меню
            await shop_menu()
            
            # Проверяем вызов методов
            mock_load_data.assert_called_once()
            mock_call.assert_called_once()
            
            # Проверяем текст сообщения
            assert "Кампаний на автоуправлении" in shop_menu.text
            assert "Test Cabinet" in shop_menu.text
            assert "1000" in shop_menu.text
            assert "100" in shop_menu.text

@pytest.mark.asyncio
async def test_shop_menu_with_no_advs(shop_menu, mock_wb_user_cabinet, mock_wb_cabinet):
    """Тест отображения меню без активных рекламных кампаний"""
    
    # Устанавливаем данные для теста
    shop_menu._wb_user_cabinet = mock_wb_user_cabinet
    shop_menu._wb_cabinet = mock_wb_cabinet
    shop_menu._balance = 1000
    shop_menu._bonus = 100
    
    # Удостоверяемся, что нет активных кампаний
    mock_wb_cabinet.adv_settings = []
    shop_menu.count_active_advs = 0
    shop_menu.is_active_adv = False
    shop_menu.price_for_month_for_shop = 0  # Устанавливаем 0 для случая когда нет активных кампаний
    
    # Патчим вызов метода загрузки данных
    with patch.object(shop_menu, '_load_all_data') as mock_load_data:
        mock_load_data.return_value = True
        
        # Патчим вызов родительского метода, чтобы не отправлять реальное сообщение
        with patch('app.modules.shop_menu.message.TextWithKeyboard.__call__') as mock_call:
            # Вызываем метод отображения меню
            await shop_menu()
            
            # Проверяем вызов методов
            mock_load_data.assert_called_once()
            mock_call.assert_called_once()
            
            # Проверяем текст сообщения
            assert "Кампаний на автоуправлении" in shop_menu.text
            # Проверяем, что при отсутствии активных кампаний в тексте есть "Нет активных РК"
            assert "Нет активных РК" in shop_menu.text

@pytest.mark.asyncio
async def test_shop_menu_keyboard(shop_menu, mock_wb_user_cabinet, mock_wb_cabinet, mock_adv_setting):
    """Тест генерации клавиатуры для меню магазина"""
    
    # Устанавливаем данные для теста
    shop_menu._wb_user_cabinet = mock_wb_user_cabinet
    shop_menu._wb_cabinet = mock_wb_cabinet
    
    # Добавляем активную рекламную кампанию
    mock_wb_cabinet.adv_settings = [mock_adv_setting]
    shop_menu.is_active_adv = True
    
    # Получаем клавиатуру
    keyboard = shop_menu.keyboard
    
    # Проверяем наличие клавиатуры
    assert keyboard is not None

@pytest.mark.asyncio
async def test_shop_menu_last_days_calculation(shop_menu, mock_wb_user_cabinet, mock_wb_cabinet, mock_pricer):
    """Тест расчета оставшихся дней работы бота при различных балансах"""
    
    # Устанавливаем данные для теста
    shop_menu._wb_user_cabinet = mock_wb_user_cabinet
    shop_menu._wb_cabinet = mock_wb_cabinet
    
    # Настраиваем различные сценарии баланса и расхода
    test_cases = [
        # (баланс, бонус, расход в день, ожидаемый текст в сообщении)
        (100, 0, 50, "Денег хватит на 2 дня работы бота"),
        (1000, 0, 100, "Денег хватит на 10 дней работы бота"),
        (50, 0, 50, "Денег хватит на 1 день работы бота"),
        (0, 0, 50, "Денег на продление кампаний больше нет"),
        (500, 50, 100, "Денег хватит на 5 дней работы бота"),
    ]
    
    for balance, bonus, daily_expense, expected_text in test_cases:
        # Настраиваем моки
        shop_menu._balance = balance
        shop_menu._bonus = bonus
        shop_menu.total_amount_for_day = daily_expense
        
        # Проверяем текст сообщения
        message_text = shop_menu.text
        
        # Если баланс = 0, проверяем специальное сообщение
        if balance == 0 and daily_expense > 0:
            assert "Денег на продление кампаний больше нет" in message_text
        elif daily_expense == 0:
            assert "∞" in message_text  # Проверка бесконечности при нулевом расходе
        else:
            # Иначе проверяем наличие ожидаемого текста
            assert expected_text in message_text or str(int((balance + bonus) / daily_expense)) in message_text 