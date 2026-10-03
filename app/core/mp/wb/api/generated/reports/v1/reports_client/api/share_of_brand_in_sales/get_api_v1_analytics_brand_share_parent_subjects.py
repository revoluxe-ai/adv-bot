from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.field_4_xx_response import Field4XxResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    locale: Union[Unset, str] = "ru",
    brand: str,
    date_from: str,
    date_to: str,
) -> Dict[str, Any]:

    params: Dict[str, Any] = {}

    params["locale"] = locale

    params["brand"] = brand

    params["dateFrom"] = date_from

    params["dateTo"] = date_to

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/analytics/brand-share/parent-subjects",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, Field4XxResponse]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = cast(Any, None)
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
) -> Response[Union[Any, Field4XxResponse]]:
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
    brand: str,
    date_from: str,
    date_to: str,
) -> Response[Union[Any, Field4XxResponse]]:
    r"""Parent Categories of the Brand

     Returns parent categories of the brand.

    Data can be obtained starting from 1 November 2022, for up to 365 days.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/introduction/Rate-Limits\">Request limit</a> per one seller
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 5 s | 1 request | 5 s | 20 requests |
    | Service | 5 s | 1 request | 5 s | 20 requests |
    | Base with secret | 5 s | 1 request | 5 s | 20 requests |
    | Base | 1 h | 1 request | 1 h | 1 request |
    </div>

    Args:
        locale (Union[Unset, str]):  Default: 'ru'. Example: ru.
        brand (str):  Example: H%26M.
        date_from (str):
        date_to (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, Field4XxResponse]]
    """

    kwargs = _get_kwargs(
        locale=locale,
        brand=brand,
        date_from=date_from,
        date_to=date_to,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    locale: Union[Unset, str] = "ru",
    brand: str,
    date_from: str,
    date_to: str,
) -> Optional[Union[Any, Field4XxResponse]]:
    r"""Parent Categories of the Brand

     Returns parent categories of the brand.

    Data can be obtained starting from 1 November 2022, for up to 365 days.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/introduction/Rate-Limits\">Request limit</a> per one seller
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 5 s | 1 request | 5 s | 20 requests |
    | Service | 5 s | 1 request | 5 s | 20 requests |
    | Base with secret | 5 s | 1 request | 5 s | 20 requests |
    | Base | 1 h | 1 request | 1 h | 1 request |
    </div>

    Args:
        locale (Union[Unset, str]):  Default: 'ru'. Example: ru.
        brand (str):  Example: H%26M.
        date_from (str):
        date_to (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, Field4XxResponse]
    """

    return sync_detailed(
        client=client,
        locale=locale,
        brand=brand,
        date_from=date_from,
        date_to=date_to,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    locale: Union[Unset, str] = "ru",
    brand: str,
    date_from: str,
    date_to: str,
) -> Response[Union[Any, Field4XxResponse]]:
    r"""Parent Categories of the Brand

     Returns parent categories of the brand.

    Data can be obtained starting from 1 November 2022, for up to 365 days.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/introduction/Rate-Limits\">Request limit</a> per one seller
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 5 s | 1 request | 5 s | 20 requests |
    | Service | 5 s | 1 request | 5 s | 20 requests |
    | Base with secret | 5 s | 1 request | 5 s | 20 requests |
    | Base | 1 h | 1 request | 1 h | 1 request |
    </div>

    Args:
        locale (Union[Unset, str]):  Default: 'ru'. Example: ru.
        brand (str):  Example: H%26M.
        date_from (str):
        date_to (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, Field4XxResponse]]
    """

    kwargs = _get_kwargs(
        locale=locale,
        brand=brand,
        date_from=date_from,
        date_to=date_to,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    locale: Union[Unset, str] = "ru",
    brand: str,
    date_from: str,
    date_to: str,
) -> Optional[Union[Any, Field4XxResponse]]:
    r"""Parent Categories of the Brand

     Returns parent categories of the brand.

    Data can be obtained starting from 1 November 2022, for up to 365 days.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/introduction/Rate-Limits\">Request limit</a> per one seller
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 5 s | 1 request | 5 s | 20 requests |
    | Service | 5 s | 1 request | 5 s | 20 requests |
    | Base with secret | 5 s | 1 request | 5 s | 20 requests |
    | Base | 1 h | 1 request | 1 h | 1 request |
    </div>

    Args:
        locale (Union[Unset, str]):  Default: 'ru'. Example: ru.
        brand (str):  Example: H%26M.
        date_from (str):
        date_to (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, Field4XxResponse]
    """

    return (
        await asyncio_detailed(
            client=client,
            locale=locale,
            brand=brand,
            date_from=date_from,
            date_to=date_to,
        )
    ).parsed
