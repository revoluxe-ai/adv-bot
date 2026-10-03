from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_api_v1_analytics_banned_products_blocked_order import (
    GetApiV1AnalyticsBannedProductsBlockedOrder,
)
from ...models.get_api_v1_analytics_banned_products_blocked_response_200 import (
    GetApiV1AnalyticsBannedProductsBlockedResponse200,
)
from ...models.get_api_v1_analytics_banned_products_blocked_response_400 import (
    GetApiV1AnalyticsBannedProductsBlockedResponse400,
)
from ...models.get_api_v1_analytics_banned_products_blocked_sort import (
    GetApiV1AnalyticsBannedProductsBlockedSort,
)
from ...types import UNSET, Response


def _get_kwargs(
    *,
    sort: GetApiV1AnalyticsBannedProductsBlockedSort,
    order: GetApiV1AnalyticsBannedProductsBlockedOrder,
) -> Dict[str, Any]:

    params: Dict[str, Any] = {}

    json_sort = sort.value
    params["sort"] = json_sort

    json_order = order.value
    params["order"] = json_order

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/analytics/banned-products/blocked",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[
        Any,
        GetApiV1AnalyticsBannedProductsBlockedResponse200,
        GetApiV1AnalyticsBannedProductsBlockedResponse400,
    ]
]:
    if response.status_code == HTTPStatus.OK:
        response_200 = GetApiV1AnalyticsBannedProductsBlockedResponse200.from_dict(
            response.json()
        )

        return response_200
    if response.status_code == HTTPStatus.BAD_REQUEST:
        response_400 = GetApiV1AnalyticsBannedProductsBlockedResponse400.from_dict(
            response.json()
        )

        return response_400
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        response_401 = cast(Any, None)
        return response_401
    if response.status_code == HTTPStatus.PAYMENT_REQUIRED:
        response_402 = cast(Any, None)
        return response_402
    if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
        response_429 = cast(Any, None)
        return response_429
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[
    Union[
        Any,
        GetApiV1AnalyticsBannedProductsBlockedResponse200,
        GetApiV1AnalyticsBannedProductsBlockedResponse400,
    ]
]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    sort: GetApiV1AnalyticsBannedProductsBlockedSort,
    order: GetApiV1AnalyticsBannedProductsBlockedOrder,
) -> Response[
    Union[
        Any,
        GetApiV1AnalyticsBannedProductsBlockedResponse200,
        GetApiV1AnalyticsBannedProductsBlockedResponse400,
    ]
]:
    r"""Get Report

     Returns the list of [blocked listings](https://seller.wildberries.ru/analytics-reports/banned-
    products).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/introduction/Rate-Limits\">Request limit</a> per one seller
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 10 s | 1 request | 10 s | 6 requests |
    | Service | 10 s | 1 request | 10 s | 6 requests |
    | Base with secret | 10 s | 1 request | 10 s | 6 requests |
    | Base | 1 h | 1 request | 1 h | 1 request |
    </div>

    Args:
        sort (GetApiV1AnalyticsBannedProductsBlockedSort):  Example: nmId.
        order (GetApiV1AnalyticsBannedProductsBlockedOrder):  Example: asc.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, GetApiV1AnalyticsBannedProductsBlockedResponse200, GetApiV1AnalyticsBannedProductsBlockedResponse400]]
    """

    kwargs = _get_kwargs(
        sort=sort,
        order=order,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    sort: GetApiV1AnalyticsBannedProductsBlockedSort,
    order: GetApiV1AnalyticsBannedProductsBlockedOrder,
) -> Optional[
    Union[
        Any,
        GetApiV1AnalyticsBannedProductsBlockedResponse200,
        GetApiV1AnalyticsBannedProductsBlockedResponse400,
    ]
]:
    r"""Get Report

     Returns the list of [blocked listings](https://seller.wildberries.ru/analytics-reports/banned-
    products).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/introduction/Rate-Limits\">Request limit</a> per one seller
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 10 s | 1 request | 10 s | 6 requests |
    | Service | 10 s | 1 request | 10 s | 6 requests |
    | Base with secret | 10 s | 1 request | 10 s | 6 requests |
    | Base | 1 h | 1 request | 1 h | 1 request |
    </div>

    Args:
        sort (GetApiV1AnalyticsBannedProductsBlockedSort):  Example: nmId.
        order (GetApiV1AnalyticsBannedProductsBlockedOrder):  Example: asc.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, GetApiV1AnalyticsBannedProductsBlockedResponse200, GetApiV1AnalyticsBannedProductsBlockedResponse400]
    """

    return sync_detailed(
        client=client,
        sort=sort,
        order=order,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    sort: GetApiV1AnalyticsBannedProductsBlockedSort,
    order: GetApiV1AnalyticsBannedProductsBlockedOrder,
) -> Response[
    Union[
        Any,
        GetApiV1AnalyticsBannedProductsBlockedResponse200,
        GetApiV1AnalyticsBannedProductsBlockedResponse400,
    ]
]:
    r"""Get Report

     Returns the list of [blocked listings](https://seller.wildberries.ru/analytics-reports/banned-
    products).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/introduction/Rate-Limits\">Request limit</a> per one seller
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 10 s | 1 request | 10 s | 6 requests |
    | Service | 10 s | 1 request | 10 s | 6 requests |
    | Base with secret | 10 s | 1 request | 10 s | 6 requests |
    | Base | 1 h | 1 request | 1 h | 1 request |
    </div>

    Args:
        sort (GetApiV1AnalyticsBannedProductsBlockedSort):  Example: nmId.
        order (GetApiV1AnalyticsBannedProductsBlockedOrder):  Example: asc.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, GetApiV1AnalyticsBannedProductsBlockedResponse200, GetApiV1AnalyticsBannedProductsBlockedResponse400]]
    """

    kwargs = _get_kwargs(
        sort=sort,
        order=order,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    sort: GetApiV1AnalyticsBannedProductsBlockedSort,
    order: GetApiV1AnalyticsBannedProductsBlockedOrder,
) -> Optional[
    Union[
        Any,
        GetApiV1AnalyticsBannedProductsBlockedResponse200,
        GetApiV1AnalyticsBannedProductsBlockedResponse400,
    ]
]:
    r"""Get Report

     Returns the list of [blocked listings](https://seller.wildberries.ru/analytics-reports/banned-
    products).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/introduction/Rate-Limits\">Request limit</a> per one seller
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 10 s | 1 request | 10 s | 6 requests |
    | Service | 10 s | 1 request | 10 s | 6 requests |
    | Base with secret | 10 s | 1 request | 10 s | 6 requests |
    | Base | 1 h | 1 request | 1 h | 1 request |
    </div>

    Args:
        sort (GetApiV1AnalyticsBannedProductsBlockedSort):  Example: nmId.
        order (GetApiV1AnalyticsBannedProductsBlockedOrder):  Example: asc.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, GetApiV1AnalyticsBannedProductsBlockedResponse200, GetApiV1AnalyticsBannedProductsBlockedResponse400]
    """

    return (
        await asyncio_detailed(
            client=client,
            sort=sort,
            order=order,
        )
    ).parsed
