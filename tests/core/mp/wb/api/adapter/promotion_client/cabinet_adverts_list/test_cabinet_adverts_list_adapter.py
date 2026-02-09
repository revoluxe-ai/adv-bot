"""Unit tests for CabinetAdvertsListAdapter.get_cabinet_adv_ids."""

from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.mp.wb.api.adapter.promotion_client.cabinet_adverts_list import (
    CabinetAdvertsListAdapter,
)
from app.core.mp.wb.api.excs import BadRequestError
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
    GetAdvV1AdvertsResponse200Item,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.types import (
    Response,
)


def _make_response_item(advert_id: int) -> GetAdvV1AdvertsResponse200Item:
    return GetAdvV1AdvertsResponse200Item(advert_id=advert_id)


@pytest.fixture
def adapter():
    """CabinetAdvertsListAdapter with mocked dependencies."""
    mock_auth = MagicMock()
    mock_auth.get_proxy_client = AsyncMock(return_value=MagicMock())
    mock_auth.shop_id = "test_shop"
    mock_rlm = MagicMock()
    mock_rlm.api_call_state = {}
    return CabinetAdvertsListAdapter(
        base_url="https://test",
        auth_client_handler=mock_auth,
        request_limit_manager=mock_rlm,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_cabinet_adv_ids_empty_list(adapter) -> None:
    """Empty parsed list returns []."""
    with patch(
        "app.core.mp.wb.api.adapter.promotion_client.cabinet_adverts_list.adapter.with_raise_errors",
        new_callable=AsyncMock,
        return_value=Response(
            status_code=HTTPStatus.OK,
            content=b"",
            headers={},
            parsed=[],
        ),
    ):
        result = await adapter.get_cabinet_adv_ids()
    assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_cabinet_adv_ids_empty_parsed_none(adapter) -> None:
    """Parsed None or not list leads to break and return []."""
    with patch(
        "app.core.mp.wb.api.adapter.promotion_client.cabinet_adverts_list.adapter.with_raise_errors",
        new_callable=AsyncMock,
        return_value=Response(
            status_code=HTTPStatus.OK,
            content=b"",
            headers={},
            parsed=None,
        ),
    ):
        result = await adapter.get_cabinet_adv_ids()
    assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_cabinet_adv_ids_single_page(adapter) -> None:
    """One page with 2–3 items returns their advert_ids."""
    items = [
        _make_response_item(10),
        _make_response_item(20),
        _make_response_item(30),
    ]
    with patch(
        "app.core.mp.wb.api.adapter.promotion_client.cabinet_adverts_list.adapter.with_raise_errors",
        new_callable=AsyncMock,
        return_value=Response(
            status_code=HTTPStatus.OK,
            content=b"",
            headers={},
            parsed=items,
        ),
    ):
        result = await adapter.get_cabinet_adv_ids()
    assert result == [10, 20, 30]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_cabinet_adv_ids_pagination(adapter) -> None:
    """Two pages: first full PAGE_SIZE, second shorter; all ids collected."""
    page_size = CabinetAdvertsListAdapter.PAGE_SIZE
    first_page = [_make_response_item(i) for i in range(page_size)]
    second_page = [_make_response_item(page_size), _make_response_item(page_size + 1)]
    call_count = 0

    async def mock_with_raise_errors(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        offset = kwargs.get("offset", 0)
        if offset == 0:
            return Response(
                status_code=HTTPStatus.OK,
                content=b"",
                headers={},
                parsed=first_page,
            )
        return Response(
            status_code=HTTPStatus.OK,
            content=b"",
            headers={},
            parsed=second_page,
        )

    with patch(
        "app.core.mp.wb.api.adapter.promotion_client.cabinet_adverts_list.adapter.with_raise_errors",
        new_callable=AsyncMock,
        side_effect=mock_with_raise_errors,
    ):
        result = await adapter.get_cabinet_adv_ids()
    assert len(result) == page_size + 2
    assert result[0] == 0
    assert result[page_size - 1] == page_size - 1
    assert result[page_size] == page_size
    assert result[page_size + 1] == page_size + 1
    assert call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_cabinet_adv_ids_bad_request_path_not_found(adapter) -> None:
    """BadRequestError with 'path not found' returns []."""
    err = BadRequestError("path not found")
    with patch(
        "app.core.mp.wb.api.adapter.promotion_client.cabinet_adverts_list.adapter.with_raise_errors",
        new_callable=AsyncMock,
        side_effect=err,
    ):
        result = await adapter.get_cabinet_adv_ids()
    assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_cabinet_adv_ids_bad_request_not_found(adapter) -> None:
    """BadRequestError with 'not found' returns []."""
    err = BadRequestError("resource not found")
    with patch(
        "app.core.mp.wb.api.adapter.promotion_client.cabinet_adverts_list.adapter.with_raise_errors",
        new_callable=AsyncMock,
        side_effect=err,
    ):
        result = await adapter.get_cabinet_adv_ids()
    assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_cabinet_adv_ids_bad_request_404(adapter) -> None:
    """BadRequestError with '404' returns []."""
    err = BadRequestError("404 error")
    with patch(
        "app.core.mp.wb.api.adapter.promotion_client.cabinet_adverts_list.adapter.with_raise_errors",
        new_callable=AsyncMock,
        side_effect=err,
    ):
        result = await adapter.get_cabinet_adv_ids()
    assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_cabinet_adv_ids_bad_request_other_reraises(adapter) -> None:
    """Other BadRequestError is re-raised."""
    err = BadRequestError("invalid request body")
    with patch(
        "app.core.mp.wb.api.adapter.promotion_client.cabinet_adverts_list.adapter.with_raise_errors",
        new_callable=AsyncMock,
        side_effect=err,
    ):
        with pytest.raises(BadRequestError):
            await adapter.get_cabinet_adv_ids()
