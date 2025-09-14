from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_adv_v1_adverts_response_200_item import (
    GetAdvV1AdvertsResponse200Item,
)
from ...models.get_adv_v1_adverts_response_401 import GetAdvV1AdvertsResponse401
from ...models.get_adv_v1_adverts_response_429 import GetAdvV1AdvertsResponse429
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    status: Union[Unset, int] = UNSET,
    type_: Union[Unset, int] = UNSET,
    limit: Union[Unset, int] = UNSET,
    offset: Union[Unset, int] = UNSET,
    order: Union[Unset, str] = UNSET,
    direction: Union[Unset, str] = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["status"] = status

    params["type"] = type_

    params["limit"] = limit

    params["offset"] = offset

    params["order"] = order

    params["direction"] = direction

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/adv/v1/adverts",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[
        GetAdvV1AdvertsResponse401,
        GetAdvV1AdvertsResponse429,
        list["GetAdvV1AdvertsResponse200Item"],
    ]
]:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = GetAdvV1AdvertsResponse200Item.from_dict(
                response_200_item_data
            )

            response_200.append(response_200_item)

        return response_200

    if response.status_code == 401:
        response_401 = GetAdvV1AdvertsResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = GetAdvV1AdvertsResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[
    Union[
        GetAdvV1AdvertsResponse401,
        GetAdvV1AdvertsResponse429,
        list["GetAdvV1AdvertsResponse200Item"],
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
    status: Union[Unset, int] = UNSET,
    type_: Union[Unset, int] = UNSET,
    limit: Union[Unset, int] = UNSET,
    offset: Union[Unset, int] = UNSET,
    order: Union[Unset, str] = UNSET,
    direction: Union[Unset, str] = UNSET,
) -> Response[
    Union[
        GetAdvV1AdvertsResponse401,
        GetAdvV1AdvertsResponse429,
        list["GetAdvV1AdvertsResponse200Item"],
    ]
]:
    r"""Spisok mediakampanij

     Metod vozvraschaet spisok vseh
    [mediakampanij](/openapi/promotion#tag/Media/paths/~1adv~1v1~1advert/get) prodavtsa po ih tipam i
    statusam.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 10 zaprosov | 100 millisekund | 10 zaprosov |
    </div>

    Args:
        status (Union[Unset, int]):  Example: 1.
        type_ (Union[Unset, int]):  Example: 1.
        limit (Union[Unset, int]):  Example: 1.
        offset (Union[Unset, int]):  Example: 1.
        order (Union[Unset, str]):  Example: id.
        direction (Union[Unset, str]):  Example: desc.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[GetAdvV1AdvertsResponse401, GetAdvV1AdvertsResponse429, list['GetAdvV1AdvertsResponse200Item']]]
    """

    kwargs = _get_kwargs(
        status=status,
        type_=type_,
        limit=limit,
        offset=offset,
        order=order,
        direction=direction,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    status: Union[Unset, int] = UNSET,
    type_: Union[Unset, int] = UNSET,
    limit: Union[Unset, int] = UNSET,
    offset: Union[Unset, int] = UNSET,
    order: Union[Unset, str] = UNSET,
    direction: Union[Unset, str] = UNSET,
) -> Optional[
    Union[
        GetAdvV1AdvertsResponse401,
        GetAdvV1AdvertsResponse429,
        list["GetAdvV1AdvertsResponse200Item"],
    ]
]:
    r"""Spisok mediakampanij

     Metod vozvraschaet spisok vseh
    [mediakampanij](/openapi/promotion#tag/Media/paths/~1adv~1v1~1advert/get) prodavtsa po ih tipam i
    statusam.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 10 zaprosov | 100 millisekund | 10 zaprosov |
    </div>

    Args:
        status (Union[Unset, int]):  Example: 1.
        type_ (Union[Unset, int]):  Example: 1.
        limit (Union[Unset, int]):  Example: 1.
        offset (Union[Unset, int]):  Example: 1.
        order (Union[Unset, str]):  Example: id.
        direction (Union[Unset, str]):  Example: desc.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[GetAdvV1AdvertsResponse401, GetAdvV1AdvertsResponse429, list['GetAdvV1AdvertsResponse200Item']]
    """

    return sync_detailed(
        client=client,
        status=status,
        type_=type_,
        limit=limit,
        offset=offset,
        order=order,
        direction=direction,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    status: Union[Unset, int] = UNSET,
    type_: Union[Unset, int] = UNSET,
    limit: Union[Unset, int] = UNSET,
    offset: Union[Unset, int] = UNSET,
    order: Union[Unset, str] = UNSET,
    direction: Union[Unset, str] = UNSET,
) -> Response[
    Union[
        GetAdvV1AdvertsResponse401,
        GetAdvV1AdvertsResponse429,
        list["GetAdvV1AdvertsResponse200Item"],
    ]
]:
    r"""Spisok mediakampanij

     Metod vozvraschaet spisok vseh
    [mediakampanij](/openapi/promotion#tag/Media/paths/~1adv~1v1~1advert/get) prodavtsa po ih tipam i
    statusam.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 10 zaprosov | 100 millisekund | 10 zaprosov |
    </div>

    Args:
        status (Union[Unset, int]):  Example: 1.
        type_ (Union[Unset, int]):  Example: 1.
        limit (Union[Unset, int]):  Example: 1.
        offset (Union[Unset, int]):  Example: 1.
        order (Union[Unset, str]):  Example: id.
        direction (Union[Unset, str]):  Example: desc.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[GetAdvV1AdvertsResponse401, GetAdvV1AdvertsResponse429, list['GetAdvV1AdvertsResponse200Item']]]
    """

    kwargs = _get_kwargs(
        status=status,
        type_=type_,
        limit=limit,
        offset=offset,
        order=order,
        direction=direction,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    status: Union[Unset, int] = UNSET,
    type_: Union[Unset, int] = UNSET,
    limit: Union[Unset, int] = UNSET,
    offset: Union[Unset, int] = UNSET,
    order: Union[Unset, str] = UNSET,
    direction: Union[Unset, str] = UNSET,
) -> Optional[
    Union[
        GetAdvV1AdvertsResponse401,
        GetAdvV1AdvertsResponse429,
        list["GetAdvV1AdvertsResponse200Item"],
    ]
]:
    r"""Spisok mediakampanij

     Metod vozvraschaet spisok vseh
    [mediakampanij](/openapi/promotion#tag/Media/paths/~1adv~1v1~1advert/get) prodavtsa po ih tipam i
    statusam.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 10 zaprosov | 100 millisekund | 10 zaprosov |
    </div>

    Args:
        status (Union[Unset, int]):  Example: 1.
        type_ (Union[Unset, int]):  Example: 1.
        limit (Union[Unset, int]):  Example: 1.
        offset (Union[Unset, int]):  Example: 1.
        order (Union[Unset, str]):  Example: id.
        direction (Union[Unset, str]):  Example: desc.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[GetAdvV1AdvertsResponse401, GetAdvV1AdvertsResponse429, list['GetAdvV1AdvertsResponse200Item']]
    """

    return (
        await asyncio_detailed(
            client=client,
            status=status,
            type_=type_,
            limit=limit,
            offset=offset,
            order=order,
            direction=direction,
        )
    ).parsed
