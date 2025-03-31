import dotenv
dotenv.load_dotenv()
import pytest
from unittest.mock import AsyncMock, patch
from app.utils.pricer.pricer import Pricer

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