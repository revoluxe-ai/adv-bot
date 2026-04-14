import pytest
from unittest.mock import AsyncMock

from app.core.mp.wb.api.adapter.promotion_client.promotion_client import PromotionClient
from app.core.mp.wb.api.domain_managers.promotion.promotion_manager import PromotionManager


@pytest.fixture
def mock_promotion_client():
    return AsyncMock(spec=PromotionClient)


@pytest.fixture
def promotion_manager(mock_promotion_client):
    return PromotionManager(promotion_client=mock_promotion_client)
