from http import HTTPStatus
from typing import Any, Dict, List, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.orders_item import OrdersItem
from ...models.response_error_statistics import ResponseErrorStatistics
from ...models.response_error_statistics_2 import ResponseErrorStatistics2
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    date_from: str,
    flag: Union[Unset, int] = 0,
) -> Dict[str, Any]:

    params: Dict[str, Any] = {}

    params["dateFrom"] = date_from

    params["flag"] = flag

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/supplier/orders",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[
        Any,
        List["OrdersItem"],
        Union["ResponseErrorStatistics", "ResponseErrorStatistics2"],
    ]
]:
    if response.status_code == HTTPStatus.OK:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = OrdersItem.from_dict(response_200_item_data)

            response_200.append(response_200_item)

        return response_200
    if response.status_code == HTTPStatus.BAD_REQUEST:

        def _parse_response_400(
            data: object,
        ) -> Union["ResponseErrorStatistics", "ResponseErrorStatistics2"]:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_400_type_0 = ResponseErrorStatistics.from_dict(data)

                return response_400_type_0
            except:  # noqa: E722
                pass
            if not isinstance(data, dict):
                raise TypeError()
            response_400_type_1 = ResponseErrorStatistics2.from_dict(data)

            return response_400_type_1

        response_400 = _parse_response_400(response.json())

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
        List["OrdersItem"],
        Union["ResponseErrorStatistics", "ResponseErrorStatistics2"],
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
    date_from: str,
    flag: Union[Unset, int] = 0,
) -> Response[
    Union[
        Any,
        List["OrdersItem"],
        Union["ResponseErrorStatistics", "ResponseErrorStatistics2"],
    ]
]:
    r"""Orders

     The method returns order information.<br>The data updated every 30 minutes.<br><br>

    1 line means 1 order and means 1 item.<br>The `srid` field should be used to identify the
    order.<br><br>

    Data storage is guaranteed for no more than 90 days from the date of sale.<br><br>

    The responses do not include orders for which payment was not confirmed. For example, it could be
    orders with delayed payments or installment payments. However, if there are sales for such orders,
    you can get it using [details for the realization reports](/openapi/financial-reports-and-
    accounting#tag/financialReports).<br>
    To receive all completed orders, use [Order Feed](https://seller.wildberries.ru/content-
    analytics/order-feed) in your personal account.

    <div class=\"description_important\">
      The data in this report is preliminary and is used for operational monitoring
    </div>

    For a single response to a request with `flag=0` or without `flag`, a conditional limit of 80,000
    rows is set. Therefore, more than one request may be necessary to retrieve all orders. In the second
    and subsequent requests, use the full value of the `lastChangeDate` field of the last row from the
    response of the previous request in the `dateFrom` parameter.<br> If the response returns an empty
    array `[]`, all orders have already been retrieved.<br><br>

    In the sandbox, the `dateFrom` and `dateTo` parameters can only be set to a range within the last 4
    months from the current date.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/introduction/Rate-Limits\">Request limit</a> per one seller
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 1 request | 1 min | 10 requests |
    | Service | 1 min | 1 request | 1 min | 10 requests |
    | Base with secret | 1 min | 1 request | 1 min | 10 requests |
    | Base | 3 h | 1 request | 3 h | 1 request |
    </div>

    Args:
        date_from (str):
        flag (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, List['OrdersItem'], Union['ResponseErrorStatistics', 'ResponseErrorStatistics2']]]
    """

    kwargs = _get_kwargs(
        date_from=date_from,
        flag=flag,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    date_from: str,
    flag: Union[Unset, int] = 0,
) -> Optional[
    Union[
        Any,
        List["OrdersItem"],
        Union["ResponseErrorStatistics", "ResponseErrorStatistics2"],
    ]
]:
    r"""Orders

     The method returns order information.<br>The data updated every 30 minutes.<br><br>

    1 line means 1 order and means 1 item.<br>The `srid` field should be used to identify the
    order.<br><br>

    Data storage is guaranteed for no more than 90 days from the date of sale.<br><br>

    The responses do not include orders for which payment was not confirmed. For example, it could be
    orders with delayed payments or installment payments. However, if there are sales for such orders,
    you can get it using [details for the realization reports](/openapi/financial-reports-and-
    accounting#tag/financialReports).<br>
    To receive all completed orders, use [Order Feed](https://seller.wildberries.ru/content-
    analytics/order-feed) in your personal account.

    <div class=\"description_important\">
      The data in this report is preliminary and is used for operational monitoring
    </div>

    For a single response to a request with `flag=0` or without `flag`, a conditional limit of 80,000
    rows is set. Therefore, more than one request may be necessary to retrieve all orders. In the second
    and subsequent requests, use the full value of the `lastChangeDate` field of the last row from the
    response of the previous request in the `dateFrom` parameter.<br> If the response returns an empty
    array `[]`, all orders have already been retrieved.<br><br>

    In the sandbox, the `dateFrom` and `dateTo` parameters can only be set to a range within the last 4
    months from the current date.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/introduction/Rate-Limits\">Request limit</a> per one seller
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 1 request | 1 min | 10 requests |
    | Service | 1 min | 1 request | 1 min | 10 requests |
    | Base with secret | 1 min | 1 request | 1 min | 10 requests |
    | Base | 3 h | 1 request | 3 h | 1 request |
    </div>

    Args:
        date_from (str):
        flag (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, List['OrdersItem'], Union['ResponseErrorStatistics', 'ResponseErrorStatistics2']]
    """

    return sync_detailed(
        client=client,
        date_from=date_from,
        flag=flag,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    date_from: str,
    flag: Union[Unset, int] = 0,
) -> Response[
    Union[
        Any,
        List["OrdersItem"],
        Union["ResponseErrorStatistics", "ResponseErrorStatistics2"],
    ]
]:
    r"""Orders

     The method returns order information.<br>The data updated every 30 minutes.<br><br>

    1 line means 1 order and means 1 item.<br>The `srid` field should be used to identify the
    order.<br><br>

    Data storage is guaranteed for no more than 90 days from the date of sale.<br><br>

    The responses do not include orders for which payment was not confirmed. For example, it could be
    orders with delayed payments or installment payments. However, if there are sales for such orders,
    you can get it using [details for the realization reports](/openapi/financial-reports-and-
    accounting#tag/financialReports).<br>
    To receive all completed orders, use [Order Feed](https://seller.wildberries.ru/content-
    analytics/order-feed) in your personal account.

    <div class=\"description_important\">
      The data in this report is preliminary and is used for operational monitoring
    </div>

    For a single response to a request with `flag=0` or without `flag`, a conditional limit of 80,000
    rows is set. Therefore, more than one request may be necessary to retrieve all orders. In the second
    and subsequent requests, use the full value of the `lastChangeDate` field of the last row from the
    response of the previous request in the `dateFrom` parameter.<br> If the response returns an empty
    array `[]`, all orders have already been retrieved.<br><br>

    In the sandbox, the `dateFrom` and `dateTo` parameters can only be set to a range within the last 4
    months from the current date.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/introduction/Rate-Limits\">Request limit</a> per one seller
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 1 request | 1 min | 10 requests |
    | Service | 1 min | 1 request | 1 min | 10 requests |
    | Base with secret | 1 min | 1 request | 1 min | 10 requests |
    | Base | 3 h | 1 request | 3 h | 1 request |
    </div>

    Args:
        date_from (str):
        flag (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, List['OrdersItem'], Union['ResponseErrorStatistics', 'ResponseErrorStatistics2']]]
    """

    kwargs = _get_kwargs(
        date_from=date_from,
        flag=flag,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    date_from: str,
    flag: Union[Unset, int] = 0,
) -> Optional[
    Union[
        Any,
        List["OrdersItem"],
        Union["ResponseErrorStatistics", "ResponseErrorStatistics2"],
    ]
]:
    r"""Orders

     The method returns order information.<br>The data updated every 30 minutes.<br><br>

    1 line means 1 order and means 1 item.<br>The `srid` field should be used to identify the
    order.<br><br>

    Data storage is guaranteed for no more than 90 days from the date of sale.<br><br>

    The responses do not include orders for which payment was not confirmed. For example, it could be
    orders with delayed payments or installment payments. However, if there are sales for such orders,
    you can get it using [details for the realization reports](/openapi/financial-reports-and-
    accounting#tag/financialReports).<br>
    To receive all completed orders, use [Order Feed](https://seller.wildberries.ru/content-
    analytics/order-feed) in your personal account.

    <div class=\"description_important\">
      The data in this report is preliminary and is used for operational monitoring
    </div>

    For a single response to a request with `flag=0` or without `flag`, a conditional limit of 80,000
    rows is set. Therefore, more than one request may be necessary to retrieve all orders. In the second
    and subsequent requests, use the full value of the `lastChangeDate` field of the last row from the
    response of the previous request in the `dateFrom` parameter.<br> If the response returns an empty
    array `[]`, all orders have already been retrieved.<br><br>

    In the sandbox, the `dateFrom` and `dateTo` parameters can only be set to a range within the last 4
    months from the current date.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/introduction/Rate-Limits\">Request limit</a> per one seller
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 1 request | 1 min | 10 requests |
    | Service | 1 min | 1 request | 1 min | 10 requests |
    | Base with secret | 1 min | 1 request | 1 min | 10 requests |
    | Base | 3 h | 1 request | 3 h | 1 request |
    </div>

    Args:
        date_from (str):
        flag (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, List['OrdersItem'], Union['ResponseErrorStatistics', 'ResponseErrorStatistics2']]
    """

    return (
        await asyncio_detailed(
            client=client,
            date_from=date_from,
            flag=flag,
        )
    ).parsed
