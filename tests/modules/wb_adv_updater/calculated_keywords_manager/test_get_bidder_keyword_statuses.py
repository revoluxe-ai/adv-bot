import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.wb_adv_updater.calculated_keywords_manager.calculated_keywords_manager import (
    CalculatedKeywordsManager,
)
from app.shared.domains.wb.dto.redis_keyword_bidder_status_manager.bidder_keyword_status import (
    BidderKeywordStatus,
)


@pytest.fixture
def complex_adv():
    adv = MagicMock()
    adv.shop_id = 987
    adv.adv_id = 654
    return adv


@pytest.fixture
def texts():
    return ["alpha", "beta"]


def _get_redis_manager_stub(return_value):
    redis_manager = MagicMock()
    redis_manager.get_statuses = AsyncMock(return_value=return_value)
    redis_manager_factory = MagicMock(return_value=redis_manager)
    return redis_manager_factory


@pytest.mark.asyncio
async def test_get_bidder_keyword_statuses_context_available(complex_adv, texts):
    manager = CalculatedKeywordsManager()
    expected_statuses = {
        "alpha": BidderKeywordStatus.GOOD,
        "beta": BidderKeywordStatus.BAD,
    }
    redis_manager_factory = _get_redis_manager_stub(expected_statuses)
    hub_mock = MagicMock()
    hub_mock.redis_keyword_bidder_status_manager = redis_manager_factory

    with patch(
        "app.core.di.wb_manager_hub.WBManagerHubFactory.get_wb_manager_from_context",
        return_value=hub_mock,
    ):
        result = await manager._get_bidder_keyword_statuses(complex_adv, texts)

    assert result == expected_statuses
    redis_manager_factory.assert_called_once_with()
    redis_manager_factory.return_value.get_statuses.assert_awaited_once_with(complex_adv, texts)


@pytest.mark.asyncio
async def test_get_bidder_keyword_statuses_fallback_creates_container(complex_adv, texts):
    manager = CalculatedKeywordsManager()
    expected_statuses = {"alpha": BidderKeywordStatus.GOOD}
    redis_manager_factory = _get_redis_manager_stub(expected_statuses)
    hub_mock = MagicMock()
    hub_mock.redis_keyword_bidder_status_manager = redis_manager_factory

    redis_config = types.SimpleNamespace(
        host="localhost",
        port=6379,
        db=5,
        password="secret",
    )
    config_stub = types.SimpleNamespace(infrastructure=types.SimpleNamespace(redis=redis_config))

    raw_redis_mock = MagicMock(name="raw_redis")
    redis_wrapper_mock = MagicMock(name="redis_wrapper")
    httpx_handler_mock = MagicMock(name="httpx_handler")
    container_instance = MagicMock()
    container_instance.wb_manager_hub.return_value = hub_mock

    with patch(
        "app.core.di.wb_manager_hub.WBManagerHubFactory.get_wb_manager_from_context",
        side_effect=RuntimeError,
    ), patch(
        "app.configs.AppConfig.create",
        return_value=config_stub,
    ) as app_config_create_mock, patch(
        "redis.asyncio.Redis",
        return_value=raw_redis_mock,
    ) as redis_cls_mock, patch(
        "app.core.redis_manager_v2.redis_client.RedisClient",
        return_value=redis_wrapper_mock,
    ) as redis_client_mock, patch(
        "app.core.mp.wb.api.httpx_client_handler.HttpxClientHandler",
        return_value=httpx_handler_mock,
    ) as httpx_handler_cls_mock, patch(
        "app.core.di.client_di.wb_manager_hub_container.WBManagerHubContainer",
        return_value=container_instance,
    ) as container_cls_mock:
        result = await manager._get_bidder_keyword_statuses(complex_adv, texts)

    assert result == expected_statuses
    redis_manager_factory.assert_called_once_with()
    redis_manager_factory.return_value.get_statuses.assert_awaited_once_with(complex_adv, texts)

    app_config_create_mock.assert_called_once_with()
    redis_cls_mock.assert_called_once_with(
        host=redis_config.host,
        port=redis_config.port,
        db=redis_config.db,
        password=redis_config.password,
        decode_responses=True,
    )
    redis_client_mock.assert_called_once_with(redis_client=raw_redis_mock)
    httpx_handler_cls_mock.assert_called_once_with()
    container_cls_mock.assert_called_once_with(
        _shop_id=complex_adv.shop_id,
        _httpx_client_handler=httpx_handler_mock,
        _redis_wrapper=redis_wrapper_mock,
    )
    container_instance.wb_manager_hub.assert_called_once_with()

