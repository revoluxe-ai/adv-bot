import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater
from app.modules.common_slaves.wildberries.data_classes.adv import Adv
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from datetime import datetime, timedelta

@pytest.fixture
def mock_wb_access():
    class MockWBToken:
        def __init__(self):
            self._shop_id = "test_shop"
            self.expires = datetime.now() + timedelta(days=1)

        @property
        def shop_id(self):
            return self._shop_id

    class MockWBAccess:
        def __init__(self):
            self.wb_cabinet = AsyncMock()
            self.wb_cabinet.id = 1
            self.wb_cabinet.shop_id = "test_shop"
            self.tokens = [MockWBToken()]  # Добавляем токен в список
            self.wb_user_cabinet = AsyncMock()
    return MockWBAccess()

@pytest.fixture
def shop_data_updater(mock_wb_access):
    return ShopDataUpdater(mock_wb_access)

@pytest.mark.asyncio
async def test_quick_update_advs(shop_data_updater, test_async_db):
    # Подготовка тестовых данных
    mock_advs = [
        Adv({
            "advertId": 1,
            "name": "Test Adv 1",
            "type": 9,
            "unitedParams": [{
                "nms": [1234567],
                "searchCPM": 100,
                "subject": {"id": 1, "name": "Test Subject"}
            }],
            "status": 9,
            "dailyBudget": 1000,
            "startTime": "2024-03-24T10:00:00",
            "endTime": "2024-03-25T10:00:00",
            "createTime": "2024-03-24T10:00:00",
            "changeTime": "2024-03-24T10:00:00"
        }),
        Adv({
            "advertId": 2,
            "name": "Test Adv 2",
            "type": 9,
            "unitedParams": [{
                "nms": [7654321],
                "searchCPM": 200,
                "subject": {"id": 2, "name": "Test Subject 2"}
            }],
            "status": 9,
            "dailyBudget": 2000,
            "startTime": "2024-03-24T10:00:00",
            "endTime": "2024-03-25T10:00:00",
            "createTime": "2024-03-24T10:00:00",
            "changeTime": "2024-03-24T10:00:00"
        })
    ]

    mock_cards = [
        {
            "nmID": 1234567,
            "name": "Test Card 1",
            "brand": "Test Brand",
            "category": "Test Category"
        },
        {
            "nmID": 7654321,
            "name": "Test Card 2",
            "brand": "Test Brand",
            "category": "Test Category"
        }
    ]

    # Мокаем методы API
    shop_data_updater.wb_api.advert.get_advertIds = AsyncMock(return_value=[1, 2])
    shop_data_updater.wb_api.advert.get_advs = AsyncMock(return_value=mock_advs)
    shop_data_updater.wb_api.content.get_all_cards = AsyncMock(return_value=mock_cards)

    # Мокаем методы базы данных
    with patch('app.modules.common_slaves.wildberries.wb_db_manager.update_advs_in_db') as mock_update_advs:
        with patch('app.modules.common_slaves.wildberries.wb_db_manager.update_cards_in_db') as mock_update_cards:
            # Выполняем тестируемый метод
            await shop_data_updater.quick_update_all_data()

            # Проверяем, что методы были вызваны
            mock_update_advs.assert_called_once()
            mock_update_cards.assert_called_once()

@pytest.mark.asyncio
async def test_quick_update_advs_with_existing_advs(shop_data_updater, test_async_db):
    # Подготовка тестовых данных
    mock_advs = [
        Adv({
            "advertId": 1,
            "name": "Test Adv 1",
            "type": 9,
            "unitedParams": [{
                "nms": [1234567],
                "searchCPM": 100,
                "subject": {"id": 1, "name": "Test Subject"}
            }],
            "status": 9,
            "dailyBudget": 1000,
            "startTime": "2024-03-24T10:00:00",
            "endTime": "2024-03-25T10:00:00",
            "createTime": "2024-03-24T10:00:00",
            "changeTime": "2024-03-24T10:00:00"
        })
    ]

    mock_cards = [
        {
            "nmID": 1234567,
            "name": "Test Card 1",
            "brand": "Test Brand",
            "category": "Test Category"
        }
    ]

    # Мокаем методы API
    shop_data_updater.wb_api.advert.get_advertIds = AsyncMock(return_value=[1])
    shop_data_updater.wb_api.advert.get_advs = AsyncMock(return_value=mock_advs)
    shop_data_updater.wb_api.content.get_all_cards = AsyncMock(return_value=mock_cards)

    # Мокаем методы базы данных
    with patch('app.modules.common_slaves.wildberries.wb_db_manager.update_advs_in_db', new_callable=AsyncMock) as mock_update_advs, \
         patch('app.modules.common_slaves.wildberries.wb_db_manager.update_cards_in_db', new_callable=AsyncMock) as mock_update_cards:
        
        # Выполняем тестируемый метод
        await shop_data_updater.quick_update_all_data()

        # Проверяем вызовы методов
        assert mock_update_advs.called
        assert mock_update_cards.called
        assert shop_data_updater.wb_api.advert.get_advertIds.called
        assert shop_data_updater.wb_api.advert.get_advs.called
        assert shop_data_updater.wb_api.content.get_all_cards.called 