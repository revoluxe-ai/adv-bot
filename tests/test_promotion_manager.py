from unittest.mock import AsyncMock

import pytest

from app.core.mp.wb.factories.adapter_factory import WbApiAdapterFactory
from app.core.mp.wb.managers.promotion import PromotionManager


@pytest.mark.asyncio
async def test_promotion_manager_delegates_calls():
    shop_id = "shop123"
    adv_id = 456
    nmids = [111, 222]

    # создаём мок адаптера
    adapter_mock = AsyncMock()
    adapter_mock.get_min_bids.return_value = {111: 10, 222: 15}
    adapter_mock.get_current_bids.return_value = {111: 20, 222: 25}
    adapter_mock.update_bids.return_value = None

    # создаём фабрику, которая всегда возвращает мок адаптера
    factory = WbApiAdapterFactory()
    factory.get_adapter = lambda shop_id, section, version: adapter_mock

    # создаём PromotionManager
    manager = PromotionManager(factory)

    # проверяем get_min_bids
    result = await manager.get_min_bids(shop_id, adv_id, nmids)
    assert result == {111: 10, 222: 15}
    adapter_mock.get_min_bids.assert_awaited_once_with(adv_id, nmids)

    # проверяем get_current_bids
    result = await manager.get_current_bids(shop_id, adv_id, nmids)
    assert result == {111: 20, 222: 25}
    adapter_mock.get_current_bids.assert_awaited_once_with(adv_id, nmids)

    # проверяем update_bids
    batch_payload = {"adv_id": adv_id, "bids": [{111: 30}, {222: 40}]}
    await manager.update_bids(shop_id, batch_payload)
    adapter_mock.update_bids.assert_awaited_once_with(batch_payload)
