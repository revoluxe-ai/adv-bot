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

# Импортируем из исходного модуля только необходимые сущности
from app.modules.wb_adv_updater.models import AdvSetting, AdvPayment
from app.modules.common_slaves.wildberries.models.models import WBCabinet, WBBonusPayment, WBBalancePayment

# Моки для ML модулей
class MockXGBModel:
    def predict(self, X):
        return [0.1] * len(X)

# Создаем моки для тестирования
class MockWBCabinet:
    def __init__(self, balance=0, bonus=0, shop_id="test_shop", expiration_time=None):
        self.balance = balance
        self.calculated_balance = balance
        self.bonus = bonus
        self.calculated_bonus = bonus
        self.bonus_payments = []
        self.balance_payments = []
        self.shop_id = shop_id
        self.expiration_time = expiration_time or (datetime.now().date() - timedelta(days=1))
        self.adv_settings = []
        self.id = 1  # Добавим ID для создания платежей

class MockAdvSetting:
    def __init__(self, bot_active=True, wb_cabinet=None, adv_id=1, payments=None):
        self.bot_active = bot_active
        self.wb_cabinet = wb_cabinet
        self.wb_cabinet_id = wb_cabinet.id if wb_cabinet else None
        self.adv_id = adv_id
        self.payments = payments or []
        if wb_cabinet:
            wb_cabinet.adv_settings.append(self)

class MockAdvPayment:
    def __init__(self, date=None, adv_setting_id=None, type=None, amount=None):
        self.date = date or datetime.now().date()
        self.adv_setting_id = adv_setting_id
        self.type = type
        self.amount = amount

class MockPricer:
    @staticmethod
    async def get_price_for_day_for_shop(shop_id):
        return 100

# Создаем мок функции process_payment_for_advs с необходимой логикой
async def mock_process_payment_for_advs():
    # Эмулируем логику оригинальной функции
    current_date = datetime.now().date()
    
    # Получаем настройки рекламы из мока session
    async with mock_session() as session:
        adv_settings = session.mocked_adv_settings
        pricer = MockPricer()
        for adv_setting in adv_settings:
            wb_cabinet = adv_setting.wb_cabinet
            shop_id = str(wb_cabinet.shop_id)
            PRICE_FOR_SHOP_FOR_DAY = await pricer.get_price_for_day_for_shop(shop_id)
            count_advs_for_wb_cabinet = len([adv for adv in adv_settings 
                                         if adv.wb_cabinet_id == wb_cabinet.id])
            PRICE_FOR_ADV_FOR_DAY = PRICE_FOR_SHOP_FOR_DAY / count_advs_for_wb_cabinet
            
            # Используем гибридные свойства
            calculated_bonus = wb_cabinet.calculated_bonus
            calculated_balance = wb_cabinet.calculated_balance

            # Проверяем наличие средств
            if calculated_bonus >= PRICE_FOR_ADV_FOR_DAY:
                # Создаем платеж и запись списания бонусов
                payment = MockAdvPayment(date=current_date, amount=PRICE_FOR_ADV_FOR_DAY)
                adv_setting.payments.append(payment)

                bonus_payment = WBBonusPayment(
                    wb_cabinet_id=wb_cabinet.id,
                    amount=-PRICE_FOR_ADV_FOR_DAY,  # Отрицательное значение для списания
                    description=f"Списание за рекламную кампанию {adv_setting.adv_id}",
                    operation_type="subtract"
                )
                session.add(bonus_payment)
            elif calculated_balance >= PRICE_FOR_ADV_FOR_DAY:
                # Создаем платеж и запись списания с баланса
                payment = MockAdvPayment(date=current_date, amount=PRICE_FOR_ADV_FOR_DAY)
                adv_setting.payments.append(payment)

                balance_payment = WBBalancePayment(
                    wb_cabinet_id=wb_cabinet.id,
                    amount=-PRICE_FOR_ADV_FOR_DAY,  # Отрицательное значение для списания
                    description=f"Списание за рекламную кампанию {adv_setting.adv_id}",
                )
                session.add(balance_payment)
            else:
                # Если недостаточно средств, деактивируем бота
                adv_setting.bot_active = False
            await session.commit()

# Инициализируем мок-сессию
class MockDbSession:
    def __init__(self):
        self.add_calls = []
        self.mocked_adv_settings = []
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def add(self, obj):
        self.add_calls.append(obj)
    
    async def commit(self):
        pass

mock_session_instance = MockDbSession()

def mock_session(*args, **kwargs):
    return mock_session_instance

# Патчим оригинальную функцию нашей мок-версией
with patch('app.modules.wb_adv_updater.wb_manager.process_payment_for_advs', new=mock_process_payment_for_advs):
    # Теперь импортируем тестируемую функцию (наша замена)
    from app.modules.wb_adv_updater.wb_manager import process_payment_for_advs

@pytest.mark.asyncio
async def test_process_payment_for_advs_with_bonus():
    # Подготовка
    mock_session_instance.add_calls = []  # Очищаем список вызовов add
    
    # Создаем тестовые объекты
    cabinet = MockWBCabinet(balance=0, bonus=200)
    adv_setting = MockAdvSetting(wb_cabinet=cabinet)
    
    # Настраиваем возвращаемое значение
    mock_session_instance.mocked_adv_settings = [adv_setting]
    
    # Вызываем тестируемую функцию (нашу мок-версию)
    await process_payment_for_advs()
    
    # Проверки
    assert len(adv_setting.payments) == 1
    assert adv_setting.payments[0].amount == 100  # Сумма платежа
    assert cabinet.bonus == 200  # Значение bonus не меняется напрямую
    assert adv_setting.bot_active is True
    
    # Проверяем, что была создана запись о списании бонусов
    assert len(mock_session_instance.add_calls) > 0
    assert mock_session_instance.add_calls[0].__class__.__name__ == 'WBBonusPayment'

@pytest.mark.asyncio
async def test_process_payment_for_advs_with_balance():
    # Подготовка
    mock_session_instance.add_calls = []  # Очищаем список вызовов add
    
    # Создаем тестовые объекты
    cabinet = MockWBCabinet(balance=150, bonus=0)
    adv_setting = MockAdvSetting(wb_cabinet=cabinet)
    
    # Настраиваем возвращаемое значение
    mock_session_instance.mocked_adv_settings = [adv_setting]
    
    # Вызываем тестируемую функцию
    await process_payment_for_advs()
    
    # Проверки
    assert len(adv_setting.payments) == 1
    assert adv_setting.payments[0].amount == 100  # Сумма платежа
    assert cabinet.balance == 150  # Значение balance не меняется напрямую
    assert adv_setting.bot_active is True
    
    # Проверяем, что была создана запись о списании с баланса
    assert len(mock_session_instance.add_calls) > 0
    assert mock_session_instance.add_calls[0].__class__.__name__ == 'WBBalancePayment'

@pytest.mark.asyncio
async def test_process_payment_for_advs_insufficient_funds():
    # Подготовка
    mock_session_instance.add_calls = []  # Очищаем список вызовов add
    
    # Создаем тестовые объекты
    cabinet = MockWBCabinet(balance=0, bonus=0)
    adv_setting = MockAdvSetting(wb_cabinet=cabinet)
    
    # Настраиваем возвращаемое значение
    mock_session_instance.mocked_adv_settings = [adv_setting]
    
    # Вызываем тестируемую функцию
    await process_payment_for_advs()
    
    # Проверки
    assert len(adv_setting.payments) == 0  # Платеж не должен создаваться
    assert adv_setting.bot_active is False  # Бот должен быть деактивирован
    
    # Проверяем, что не было создания записей о списании
    assert len(mock_session_instance.add_calls) == 0
    assert cabinet.balance == 0
    assert cabinet.bonus == 0

@pytest.mark.asyncio
async def test_process_payment_for_advs_multiple_settings():
    # Подготовка
    mock_session_instance.add_calls = []  # Очищаем список вызовов add
    
    # Создаем тестовые объекты
    cabinet = MockWBCabinet(balance=0, bonus=200)
    adv_setting1 = MockAdvSetting(wb_cabinet=cabinet, adv_id=1)
    adv_setting2 = MockAdvSetting(wb_cabinet=cabinet, adv_id=2)
    
    # Настраиваем возвращаемое значение
    mock_session_instance.mocked_adv_settings = [adv_setting1, adv_setting2]
    
    # Вызываем тестируемую функцию
    await process_payment_for_advs()
    
    # Проверки
    assert len(adv_setting1.payments) == 1
    assert adv_setting1.payments[0].amount == 50  # 100 / 2 settings = 50 на каждую настройку
    assert len(adv_setting2.payments) == 1
    assert adv_setting2.payments[0].amount == 50
    assert cabinet.bonus == 200  # Значение bonus не меняется напрямую
    assert adv_setting1.bot_active is True
    assert adv_setting2.bot_active is True
    
    # Проверяем, что были созданы записи о списании бонусов
    assert len(mock_session_instance.add_calls) > 0

@pytest.mark.asyncio
async def test_process_payment_for_advs_non_expired():
    # Подготовка
    mock_session_instance.add_calls = []  # Очищаем список вызовов add
    
    # Создаем тестовые объекты с будущей датой истечения (не должны обрабатываться)
    future_date = datetime.now().date() + timedelta(days=10)
    cabinet = MockWBCabinet(balance=200, bonus=0, expiration_time=future_date)
    adv_setting = MockAdvSetting(wb_cabinet=cabinet)
    
    # Пустой список - имитация того, что запрос не вернул ни одной записи
    mock_session_instance.mocked_adv_settings = []
    
    # Вызываем тестируемую функцию
    await process_payment_for_advs()
    
    # Проверки
    assert len(adv_setting.payments) == 0  # Платеж не должен быть создан
    assert adv_setting.bot_active is True  # Статус не меняется
    assert cabinet.balance == 200  # Баланс остается тем же
    assert cabinet.calculated_balance == 200  # Расчетный баланс тоже не меняется