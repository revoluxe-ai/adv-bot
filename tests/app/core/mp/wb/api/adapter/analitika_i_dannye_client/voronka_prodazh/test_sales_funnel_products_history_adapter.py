import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.mp.wb.api.adapter.analitika_i_dannye_client.voronka_prodazh.adapter import (
    Adapter as VoronkaProdazhAdapter,
)
from app.core.mp.wb.api.adapter.analitika_i_dannye_client.voronka_prodazh.post_sales_funnel_products_history import (
    SalesFunnelProductsHistoryCommand,
    command_to_body,
)
from app.core.mp.wb.api.generated.analitika_i_dannye_client.models import (
    History,
    ProductHistoryResponseItem,
    ProductHistoryResponseItemProduct,
)
from app.core.mp.wb.api.request_limit_manager import RequestLimitManager


@pytest.fixture
def mock_auth_client_handler():
    return AsyncMock()


@pytest.fixture
def mock_request_limit_manager():
    mock = AsyncMock(spec=RequestLimitManager)
    mock.api_call_state = {}
    return mock


@pytest.fixture
def voronka_adapter(mock_auth_client_handler, mock_request_limit_manager):
    return VoronkaProdazhAdapter(
        base_url="http://test_url",
        auth_client_handler=mock_auth_client_handler,
        request_limit_manager=mock_request_limit_manager,
    )


@pytest.mark.asyncio
async def test_post_sales_funnel_products_history(voronka_adapter, mock_auth_client_handler):
    start = datetime.date(2025, 12, 15)
    end = datetime.date(2025, 12, 21)
    command = SalesFunnelProductsHistoryCommand(
        nmids=[111, 222],
        start=start,
        end=end,
    )
    expected_body = command_to_body(command)

    mock_client = AsyncMock()
    mock_auth_client_handler.get_proxy_client = AsyncMock(return_value=mock_client)

    # Создаём типизированные объекты как в реальном API
    product = ProductHistoryResponseItemProduct(
        nm_id=111,
        title="Test Product",
        vendor_code="TEST123",
        brand_name="Test Brand",
        subject_id=1,
        subject_name="Test Subject",
    )
    history_item = History(
        date=datetime.date(2025, 12, 21),
        open_count=5,
        cart_count=2,
        order_count=1,
        order_sum=100,
        buyout_count=1,
        buyout_sum=100,
        buyout_percent=100,
        add_to_cart_conversion=40,
        cart_to_order_conversion=50,
        add_to_wishlist_count=0,
    )
    parsed_response = [
        ProductHistoryResponseItem(
            product=product,
            history=[history_item],
        )
    ]

    mock_response_from_api = SimpleNamespace(
        status_code=200,
        parsed=parsed_response,
    )

    with patch(
        "app.core.mp.wb.api.adapter.analitika_i_dannye_client.voronka_prodazh.adapter.asyncio_detailed",
        new_callable=AsyncMock,
    ) as mock_asyncio_detailed:
        mock_asyncio_detailed.return_value = mock_response_from_api

        result = await voronka_adapter.post_sales_funnel_products_history(command)

        mock_auth_client_handler.get_proxy_client.assert_awaited_once_with(voronka_adapter)
        mock_asyncio_detailed.assert_awaited_once_with(client=mock_client, body=expected_body)

        assert len(result) == 1
        row = result[0]
        assert row.nmid == 111
        assert row.open_card == 5
        assert row.add_to_cart == 2
        assert row.orders == 1
        assert row.orders_sum == 100.0
        assert row.buy_outs == 1


