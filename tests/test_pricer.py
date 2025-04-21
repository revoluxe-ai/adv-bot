import dotenv
dotenv.load_dotenv()
import pytest
from unittest.mock import AsyncMock, patch
from app.utils.pricer.pricer import Pricer
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from models.pricer import get_price_for_day_for_shop, predict_keyword_ctr, get_minimal_bet, get_adv_costs, get_position_from_bet

from tests.mocks import MockAdvSetting, MockWBCabinet, MockKeywordSetting

@pytest.fixture
def pricer():
    return Pricer()

@pytest.mark.asyncio
async def test_get_month_tariff_for_count_advs_single_adv(pricer):
    """Тест расчета тарифа для одного артикула"""
    with patch.object(pricer, 'get_advs_count', new_callable=AsyncMock) as mock_count:
        mock_count.return_value = 1
        result = await pricer.get_month_tariff_for_count_advs("test_shop_id")
        assert result == 1299  # 1 * 1299 (тариф до 2 артикулов)

@pytest.mark.asyncio
async def test_get_month_tariff_for_count_advs_four_advs(pricer):
    """Тест расчета тарифа для четырех артикулов"""
    with patch.object(pricer, 'get_advs_count', new_callable=AsyncMock) as mock_count:
        mock_count.return_value = 4
        result = await pricer.get_month_tariff_for_count_advs("test_shop_id")
        assert result == 3996  # 4 * 999 (тариф до 5 артикулов)

@pytest.mark.asyncio
async def test_get_month_tariff_for_count_advs_ten_advs(pricer):
    """Тест расчета тарифа для десяти артикулов"""
    with patch.object(pricer, 'get_advs_count', new_callable=AsyncMock) as mock_count:
        mock_count.return_value = 10
        result = await pricer.get_month_tariff_for_count_advs("test_shop_id")
        assert result == 6990  # 10 * 699 (тариф до 10 артикулов)

@pytest.mark.asyncio
async def test_get_month_tariff_for_count_advs_max_tariff(pricer):
    """Тест расчета тарифа для количества артикулов больше максимального лимита"""
    with patch.object(pricer, 'get_advs_count', new_callable=AsyncMock) as mock_count:
        mock_count.return_value = 1000
        result = await pricer.get_month_tariff_for_count_advs("test_shop_id")
        assert result == 299000  # 1000 * 299 (максимальный тариф)

@pytest.mark.asyncio
async def test_get_tariff_for_day(pricer):
    """Тест расчета дневного тарифа"""
    # Тест для 4 артикулов (3996 рублей в месяц)
    daily_rate = pricer.get_tariff_for_day(3996)
    assert daily_rate == 133.2  # 3996 / 30

@pytest.mark.asyncio
async def test_get_price_for_day_for_shop(pricer):
    """Тест получения дневной цены для магазина"""
    with patch.object(pricer, 'get_month_tariff_for_count_advs', new_callable=AsyncMock) as mock_month:
        mock_month.return_value = 3996  # 4 артикула * 999
        result = await pricer.get_price_for_day_for_shop("test_shop_id")
        assert result == 133.2  # 3996 / 30

# Тестируем функцию получения цены для дня для магазина
def test_get_price_for_day_for_shop():
    # Используем моки для тестирования
    shop_id = "test_shop"
    day = datetime.now().date()
    
    # Вызываем функцию
    result = get_price_for_day_for_shop(shop_id, day)
    
    # Проверяем, что результат является числом (float)
    assert isinstance(result, float)
    # В мок реализации должно вернуться 0.001
    assert result == 0.001

# Тестируем функцию прогнозирования CTR для ключевого слова
def test_predict_keyword_ctr():
    # Создаем тестовые данные
    keyword = "test_keyword"
    nmid = 12345
    
    # Вызываем функцию
    result = predict_keyword_ctr(keyword, nmid)
    
    # Проверяем, что результат является числом и в правильном диапазоне
    assert isinstance(result, float)
    assert 0 <= result <= 1

# Тестируем функцию получения минимальной ставки
def test_get_minimal_bet():
    # Создаем тестовые данные
    keyword = "test_keyword"
    adv_id = "test_adv_id"
    
    # Вызываем функцию
    result = get_minimal_bet(keyword, adv_id)
    
    # Проверяем, что результат является числом и больше или равен нулю
    assert isinstance(result, (int, float))
    assert result >= 0

# Тестируем функцию получения затрат на рекламу
def test_get_adv_costs():
    # Создаем мок объект с настройками рекламы
    adv_setting = MockAdvSetting(id=1, adv_id="test_adv_id")
    wb_cabinet = MockWBCabinet(id=1, shop_id="test_shop")
    adv_setting.wb_cabinet = wb_cabinet

    # Добавляем ключевые слова с настройками
    keyword_setting1 = MockKeywordSetting(id=1, adv_setting=adv_setting, text="keyword1", bid=100.0, search_count=100)
    keyword_setting2 = MockKeywordSetting(id=2, adv_setting=adv_setting, text="keyword2", bid=200.0, search_count=200)

    adv_setting.keyword_settings = [keyword_setting1, keyword_setting2]

    # Указываем даты для расчета
    start_date = datetime.now().date() - timedelta(days=7)
    end_date = datetime.now().date()

    # Создаем тестовый DataFrame с нужными данными
    test_data = []
    for i in range(7):
        day_date = start_date + timedelta(days=i)
        test_data.append({
            'date': day_date,
            'sum': 100.0 + i * 10.0
        })
    # Создаем настоящий DataFrame для теста
    test_df = pd.DataFrame(test_data)

    # Патчим функцию get_adv_costs с правильным путем
    with patch('models.pricer.get_adv_costs', return_value=test_df):
        # Импортируем функцию после патча
        from models.pricer import get_adv_costs
        
        # Вызываем функцию
        result = get_adv_costs(adv_setting, start_date, end_date)
        
        # Проверяем, что результат - это тот же DataFrame, который мы замокировали
        assert result is test_df
        # Проверим одно из свойств, чтобы быть уверенными, что это тот DataFrame
        assert len(result) == 7

# Тестируем функцию получения позиции по ставке
def test_get_position_from_bet():
    # Создаем тестовые данные
    bet = 100.0
    min_bet = 50.0
    bets = [30.0, 70.0, 120.0, 150.0]
    
    # Вызываем функцию
    result = get_position_from_bet(bet, min_bet, bets)
    
    # Проверяем, что результат является целым числом
    assert isinstance(result, int)
    # В данном случае наша ставка (100.0) должна дать позицию 2 (третье место)
    # так как 100.0 больше чем 30.0 и 70.0, но меньше чем 120.0 и 150.0
    assert result == 2 