from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.create_task_response import CreateTaskResponse
from ...models.field_4_xx_response import Field4XxResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    locale: Union[Unset, str] = "ru",
    group_by_brand: Union[Unset, bool] = False,
    group_by_subject: Union[Unset, bool] = False,
    group_by_sa: Union[Unset, bool] = False,
    group_by_nm: Union[Unset, bool] = False,
    group_by_barcode: Union[Unset, bool] = False,
    group_by_size: Union[Unset, bool] = False,
    filter_pics: Union[Unset, int] = 0,
    filter_volume: Union[Unset, int] = 0,
) -> Dict[str, Any]:

    params: Dict[str, Any] = {}

    params["locale"] = locale

    params["groupByBrand"] = group_by_brand

    params["groupBySubject"] = group_by_subject

    params["groupBySa"] = group_by_sa

    params["groupByNm"] = group_by_nm

    params["groupByBarcode"] = group_by_barcode

    params["groupBySize"] = group_by_size

    params["filterPics"] = filter_pics

    params["filterVolume"] = filter_volume

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/warehouse_remains",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, CreateTaskResponse, Field4XxResponse]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = CreateTaskResponse.from_dict(response.json())

        return response_200
    if response.status_code == HTTPStatus.BAD_REQUEST:
        response_400 = Field4XxResponse.from_dict(response.json())

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
) -> Response[Union[Any, CreateTaskResponse, Field4XxResponse]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    locale: Union[Unset, str] = "ru",
    group_by_brand: Union[Unset, bool] = False,
    group_by_subject: Union[Unset, bool] = False,
    group_by_sa: Union[Unset, bool] = False,
    group_by_nm: Union[Unset, bool] = False,
    group_by_barcode: Union[Unset, bool] = False,
    group_by_size: Union[Unset, bool] = False,
    filter_pics: Union[Unset, int] = 0,
    filter_volume: Union[Unset, int] = 0,
) -> Response[Union[Any, CreateTaskResponse, Field4XxResponse]]:
    r"""Create the Report

     Creates a task for report generation. The parameters `groupBy` and `filter` can be set in any
    combination — similar to the [version](https://seller.wildberries.ru/analytics-reports/warehouse-
    remains) in the personal account.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/introduction/Rate-Limits\">Request limit</a> per one seller
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 1 request | 1 min | 5 requests |
    | Service | 1 min | 1 request | 1 min | 5 requests |
    | Base with secret | 1 min | 1 request | 1 min | 5 requests |
    | Base | 1 h | 4 requests | 15 min | 1 request |
    </div>

    Args:
        locale (Union[Unset, str]):  Default: 'ru'. Example: ru.
        group_by_brand (Union[Unset, bool]):  Default: False. Example: True.
        group_by_subject (Union[Unset, bool]):  Default: False. Example: True.
        group_by_sa (Union[Unset, bool]):  Default: False. Example: True.
        group_by_nm (Union[Unset, bool]):  Default: False. Example: True.
        group_by_barcode (Union[Unset, bool]):  Default: False. Example: True.
        group_by_size (Union[Unset, bool]):  Default: False. Example: True.
        filter_pics (Union[Unset, int]):  Default: 0. Example: 1.
        filter_volume (Union[Unset, int]):  Default: 0. Example: 3.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, CreateTaskResponse, Field4XxResponse]]
    """

    kwargs = _get_kwargs(
        locale=locale,
        group_by_brand=group_by_brand,
        group_by_subject=group_by_subject,
        group_by_sa=group_by_sa,
        group_by_nm=group_by_nm,
        group_by_barcode=group_by_barcode,
        group_by_size=group_by_size,
        filter_pics=filter_pics,
        filter_volume=filter_volume,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    locale: Union[Unset, str] = "ru",
    group_by_brand: Union[Unset, bool] = False,
    group_by_subject: Union[Unset, bool] = False,
    group_by_sa: Union[Unset, bool] = False,
    group_by_nm: Union[Unset, bool] = False,
    group_by_barcode: Union[Unset, bool] = False,
    group_by_size: Union[Unset, bool] = False,
    filter_pics: Union[Unset, int] = 0,
    filter_volume: Union[Unset, int] = 0,
) -> Optional[Union[Any, CreateTaskResponse, Field4XxResponse]]:
    r"""Create the Report

     Creates a task for report generation. The parameters `groupBy` and `filter` can be set in any
    combination — similar to the [version](https://seller.wildberries.ru/analytics-reports/warehouse-
    remains) in the personal account.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/introduction/Rate-Limits\">Request limit</a> per one seller
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 1 request | 1 min | 5 requests |
    | Service | 1 min | 1 request | 1 min | 5 requests |
    | Base with secret | 1 min | 1 request | 1 min | 5 requests |
    | Base | 1 h | 4 requests | 15 min | 1 request |
    </div>

    Args:
        locale (Union[Unset, str]):  Default: 'ru'. Example: ru.
        group_by_brand (Union[Unset, bool]):  Default: False. Example: True.
        group_by_subject (Union[Unset, bool]):  Default: False. Example: True.
        group_by_sa (Union[Unset, bool]):  Default: False. Example: True.
        group_by_nm (Union[Unset, bool]):  Default: False. Example: True.
        group_by_barcode (Union[Unset, bool]):  Default: False. Example: True.
        group_by_size (Union[Unset, bool]):  Default: False. Example: True.
        filter_pics (Union[Unset, int]):  Default: 0. Example: 1.
        filter_volume (Union[Unset, int]):  Default: 0. Example: 3.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, CreateTaskResponse, Field4XxResponse]
    """

    return sync_detailed(
        client=client,
        locale=locale,
        group_by_brand=group_by_brand,
        group_by_subject=group_by_subject,
        group_by_sa=group_by_sa,
        group_by_nm=group_by_nm,
        group_by_barcode=group_by_barcode,
        group_by_size=group_by_size,
        filter_pics=filter_pics,
        filter_volume=filter_volume,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    locale: Union[Unset, str] = "ru",
    group_by_brand: Union[Unset, bool] = False,
    group_by_subject: Union[Unset, bool] = False,
    group_by_sa: Union[Unset, bool] = False,
    group_by_nm: Union[Unset, bool] = False,
    group_by_barcode: Union[Unset, bool] = False,
    group_by_size: Union[Unset, bool] = False,
    filter_pics: Union[Unset, int] = 0,
    filter_volume: Union[Unset, int] = 0,
) -> Response[Union[Any, CreateTaskResponse, Field4XxResponse]]:
    r"""Create the Report

     Creates a task for report generation. The parameters `groupBy` and `filter` can be set in any
    combination — similar to the [version](https://seller.wildberries.ru/analytics-reports/warehouse-
    remains) in the personal account.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/introduction/Rate-Limits\">Request limit</a> per one seller
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 1 request | 1 min | 5 requests |
    | Service | 1 min | 1 request | 1 min | 5 requests |
    | Base with secret | 1 min | 1 request | 1 min | 5 requests |
    | Base | 1 h | 4 requests | 15 min | 1 request |
    </div>

    Args:
        locale (Union[Unset, str]):  Default: 'ru'. Example: ru.
        group_by_brand (Union[Unset, bool]):  Default: False. Example: True.
        group_by_subject (Union[Unset, bool]):  Default: False. Example: True.
        group_by_sa (Union[Unset, bool]):  Default: False. Example: True.
        group_by_nm (Union[Unset, bool]):  Default: False. Example: True.
        group_by_barcode (Union[Unset, bool]):  Default: False. Example: True.
        group_by_size (Union[Unset, bool]):  Default: False. Example: True.
        filter_pics (Union[Unset, int]):  Default: 0. Example: 1.
        filter_volume (Union[Unset, int]):  Default: 0. Example: 3.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, CreateTaskResponse, Field4XxResponse]]
    """

    kwargs = _get_kwargs(
        locale=locale,
        group_by_brand=group_by_brand,
        group_by_subject=group_by_subject,
        group_by_sa=group_by_sa,
        group_by_nm=group_by_nm,
        group_by_barcode=group_by_barcode,
        group_by_size=group_by_size,
        filter_pics=filter_pics,
        filter_volume=filter_volume,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    locale: Union[Unset, str] = "ru",
    group_by_brand: Union[Unset, bool] = False,
    group_by_subject: Union[Unset, bool] = False,
    group_by_sa: Union[Unset, bool] = False,
    group_by_nm: Union[Unset, bool] = False,
    group_by_barcode: Union[Unset, bool] = False,
    group_by_size: Union[Unset, bool] = False,
    filter_pics: Union[Unset, int] = 0,
    filter_volume: Union[Unset, int] = 0,
) -> Optional[Union[Any, CreateTaskResponse, Field4XxResponse]]:
    r"""Create the Report

     Creates a task for report generation. The parameters `groupBy` and `filter` can be set in any
    combination — similar to the [version](https://seller.wildberries.ru/analytics-reports/warehouse-
    remains) in the personal account.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/introduction/Rate-Limits\">Request limit</a> per one seller
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 1 request | 1 min | 5 requests |
    | Service | 1 min | 1 request | 1 min | 5 requests |
    | Base with secret | 1 min | 1 request | 1 min | 5 requests |
    | Base | 1 h | 4 requests | 15 min | 1 request |
    </div>

    Args:
        locale (Union[Unset, str]):  Default: 'ru'. Example: ru.
        group_by_brand (Union[Unset, bool]):  Default: False. Example: True.
        group_by_subject (Union[Unset, bool]):  Default: False. Example: True.
        group_by_sa (Union[Unset, bool]):  Default: False. Example: True.
        group_by_nm (Union[Unset, bool]):  Default: False. Example: True.
        group_by_barcode (Union[Unset, bool]):  Default: False. Example: True.
        group_by_size (Union[Unset, bool]):  Default: False. Example: True.
        filter_pics (Union[Unset, int]):  Default: 0. Example: 1.
        filter_volume (Union[Unset, int]):  Default: 0. Example: 3.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, CreateTaskResponse, Field4XxResponse]
    """

    return (
        await asyncio_detailed(
            client=client,
            locale=locale,
            group_by_brand=group_by_brand,
            group_by_subject=group_by_subject,
            group_by_sa=group_by_sa,
            group_by_nm=group_by_nm,
            group_by_barcode=group_by_barcode,
            group_by_size=group_by_size,
            filter_pics=filter_pics,
            filter_volume=filter_volume,
        )
    ).parsed
