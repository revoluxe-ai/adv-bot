import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date, timedelta

# Создаем модуль-заглушку для app.client_bot.bot
class MockBot:
    def __init__(self, *args, **kwargs):
        pass

# Создаем класс-заглушку для модуля
class MockBotModule:
    Bot = MockBot
    bot = MockBot()

# Патчим sys.modules, чтобы при импорте app.client_bot.bot использовался наш мок
sys.modules['app.client_bot.bot'] = MockBotModule()

# После патча импортируем тестируемую функцию
from app.modules.wb_adv_updater.wb_manager import process_payment_for_advs

# Создаем моки для тестирования
class MockWBCabinet:
    def __init__(self, balance=0, bonus=0, shop_id="test_shop", expiration_time=None):
        self.balance = balance
        self.calculated_balance = balance
        self.bonus = bonus
        self.bonus_payments = bonus
        self.shop_id = shop_id
        self.expiration_time = expiration_time or (datetime.now().date() - timedelta(days=1))
        self.adv_settings = []

class MockAdvSetting:
    def __init__(self, bot_active=True, wb_cabinet=None, adv_id=1, payments=None):
        self.bot_active = bot_active
        self.wb_cabinet = wb_cabinet
        self.adv_id = adv_id
        self.payments = payments or []
        if wb_cabinet:
            wb_cabinet.adv_settings.append(self)

class MockAdvPayment:
    def __init__(self, date=None, adv_setting_id=None, type=None):
        self.date = date or datetime.now().date()
        self.adv_setting_id = adv_setting_id
        self.type = type

class MockPricer:
    async def get_price_for_day_for_shop(self, shop_id):
        return 100

# Патчи для тестов
@pytest.fixture
def mock_sm():
    with patch('app.modules.wb_adv_updater.wb_manager.sm') as mock:
        # Создаем контекстный менеджер для mock_sm
        async_session = AsyncMock()
        mock.return_value.__aenter__.return_value = async_session
        
        # Имитируем метод execute
        execute_result = MagicMock()
        async_session.execute.return_value = execute_result
        
        # Имитируем уникальные скаляры
        scalars_result = MagicMock()
        execute_result.unique.return_value = execute_result
        execute_result.scalars.return_value = scalars_result
        
        yield mock, async_session, scalars_result

@pytest.fixture
def mock_pricer():
    with patch('app.modules.wb_adv_updater.wb_manager.Pricer', return_value=MockPricer()):
        yield

@pytest.mark.asyncio
async def test_process_payment_for_advs_with_bonus(mock_sm, mock_pricer):
    # Подготовка
    mock_sm_obj, mock_session, mock_scalars = mock_sm
    
    # Создаем тестовые объекты
    cabinet = MockWBCabinet(balance=0, bonus=200)
    adv_setting = MockAdvSetting(wb_cabinet=cabinet)
    
    # Настраиваем возвращаемое значение для all()
    mock_scalars.all.return_value = [adv_setting]
    
    # Вызываем тестируемую функцию
    await process_payment_for_advs()
    
    # Проверки
    assert mock_session.execute.called
    assert mock_session.commit.called
    assert len(adv_setting.payments) == 1
    assert cabinet.bonus == 100  # 200 - 100 (стоимость на день)
    assert adv_setting.bot_active is True

@pytest.mark.asyncio
async def test_process_payment_for_advs_with_balance(mock_sm, mock_pricer):
    # Подготовка
    mock_sm_obj, mock_session, mock_scalars = mock_sm
    
    # Создаем тестовые объекты
    cabinet = MockWBCabinet(balance=150, bonus=0)
    adv_setting = MockAdvSetting(wb_cabinet=cabinet)
    
    # Настраиваем возвращаемое значение для all()
    mock_scalars.all.return_value = [adv_setting]
    
    # Вызываем тестируемую функцию
    await process_payment_for_advs()
    
    # Проверки
    assert mock_session.execute.called
    assert mock_session.commit.called
    assert len(adv_setting.payments) == 1
    assert cabinet.balance == 50  # 150 - 100 (стоимость на день)
    assert adv_setting.bot_active is True

@pytest.mark.asyncio
async def test_process_payment_for_advs_insufficient_funds(mock_sm, mock_pricer):
    # Подготовка
    mock_sm_obj, mock_session, mock_scalars = mock_sm
    
    # Создаем тестовые объекты
    cabinet = MockWBCabinet(balance=0, bonus=0)
    adv_setting = MockAdvSetting(wb_cabinet=cabinet)
    
    # Настраиваем возвращаемое значение для all()
    mock_scalars.all.return_value = [adv_setting]
    
    # Вызываем тестируемую функцию
    await process_payment_for_advs()
    
    # Проверки
    assert mock_session.execute.called
    assert mock_session.commit.called
    assert len(adv_setting.payments) == 0  # Платеж не должен быть создан
    assert adv_setting.bot_active is False  # Бот должен быть деактивирован

@pytest.mark.asyncio
async def test_process_payment_for_advs_multiple_settings(mock_sm, mock_pricer):
    # Подготовка
    mock_sm_obj, mock_session, mock_scalars = mock_sm
    
    # Создаем тестовые объекты
    cabinet = MockWBCabinet(balance=0, bonus=200)
    adv_setting1 = MockAdvSetting(wb_cabinet=cabinet, adv_id=1)
    adv_setting2 = MockAdvSetting(wb_cabinet=cabinet, adv_id=2)
    
    # Настраиваем возвращаемое значение для all()
    mock_scalars.all.return_value = [adv_setting1, adv_setting2]
    
    # Вызываем тестируемую функцию
    await process_payment_for_advs()
    
    # Проверки
    assert mock_session.execute.called
    assert mock_session.commit.called
    assert len(adv_setting1.payments) == 1
    assert len(adv_setting2.payments) == 1
    assert cabinet.bonus == 100  # 200 - 50 - 50 = 100
    assert adv_setting1.bot_active is True
    assert adv_setting2.bot_active is True

@pytest.mark.asyncio
async def test_process_payment_for_advs_non_expired(mock_sm, mock_pricer):
    # Подготовка
    mock_sm_obj, mock_session, mock_scalars = mock_sm
    
    # Создаем тестовые объекты с будущей датой истечения (не должны обрабатываться)
    future_date = datetime.now().date() + timedelta(days=10)
    cabinet = MockWBCabinet(balance=200, bonus=0, expiration_time=future_date)
    adv_setting = MockAdvSetting(wb_cabinet=cabinet)
    
    # Пустой список - имитация того, что запрос не вернул ни одной записи
    mock_scalars.all.return_value = []
    
    # Вызываем тестируемую функцию
    await process_payment_for_advs()
    
    # Проверки
    assert mock_session.execute.called
    assert not mock_session.commit.called  # Не должен быть вызван, так как нет обрабатываемых настроек
    assert len(adv_setting.payments) == 0  # Платеж не должен быть создан
    assert adv_setting.bot_active is True  # Статус не меняется
    assert cabinet.balance == 200  # Баланс остается тем же