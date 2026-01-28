from http import HTTPStatus
from typing import Any, cast

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
    status: int | Unset = UNSET,
    type_: int | Unset = UNSET,
    limit: int | Unset = UNSET,
    offset: int | Unset = UNSET,
    order: str | Unset = UNSET,
    direction: str | Unset = UNSET,
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
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    Any
    | GetAdvV1AdvertsResponse401
    | GetAdvV1AdvertsResponse429
    | list[GetAdvV1AdvertsResponse200Item]
    | None
):
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = GetAdvV1AdvertsResponse200Item.from_dict(
                response_200_item_data
            )

            response_200.append(response_200_item)

        return response_200

    if response.status_code == 204:
        response_204 = cast(Any, None)
        return response_204

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
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    Any
    | GetAdvV1AdvertsResponse401
    | GetAdvV1AdvertsResponse429
    | list[GetAdvV1AdvertsResponse200Item]
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
    status: int | Unset = UNSET,
    type_: int | Unset = UNSET,
    limit: int | Unset = UNSET,
    offset: int | Unset = UNSET,
    order: str | Unset = UNSET,
    direction: str | Unset = UNSET,
) -> Response[
    Any
    | GetAdvV1AdvertsResponse401
    | GetAdvV1AdvertsResponse429
    | list[GetAdvV1AdvertsResponse200Item]
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
        status (int | Unset):  Example: 1.
        type_ (int | Unset):  Example: 1.
        limit (int | Unset):  Example: 1.
        offset (int | Unset):  Example: 1.
        order (str | Unset):  Example: id.
        direction (str | Unset):  Example: desc.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | GetAdvV1AdvertsResponse401 | GetAdvV1AdvertsResponse429 | list[GetAdvV1AdvertsResponse200Item]]
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
    status: int | Unset = UNSET,
    type_: int | Unset = UNSET,
    limit: int | Unset = UNSET,
    offset: int | Unset = UNSET,
    order: str | Unset = UNSET,
    direction: str | Unset = UNSET,
) -> (
    Any
    | GetAdvV1AdvertsResponse401
    | GetAdvV1AdvertsResponse429
    | list[GetAdvV1AdvertsResponse200Item]
    | None
):
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
        status (int | Unset):  Example: 1.
        type_ (int | Unset):  Example: 1.
        limit (int | Unset):  Example: 1.
        offset (int | Unset):  Example: 1.
        order (str | Unset):  Example: id.
        direction (str | Unset):  Example: desc.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | GetAdvV1AdvertsResponse401 | GetAdvV1AdvertsResponse429 | list[GetAdvV1AdvertsResponse200Item]
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
    status: int | Unset = UNSET,
    type_: int | Unset = UNSET,
    limit: int | Unset = UNSET,
    offset: int | Unset = UNSET,
    order: str | Unset = UNSET,
    direction: str | Unset = UNSET,
) -> Response[
    Any
    | GetAdvV1AdvertsResponse401
    | GetAdvV1AdvertsResponse429
    | list[GetAdvV1AdvertsResponse200Item]
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
        status (int | Unset):  Example: 1.
        type_ (int | Unset):  Example: 1.
        limit (int | Unset):  Example: 1.
        offset (int | Unset):  Example: 1.
        order (str | Unset):  Example: id.
        direction (str | Unset):  Example: desc.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | GetAdvV1AdvertsResponse401 | GetAdvV1AdvertsResponse429 | list[GetAdvV1AdvertsResponse200Item]]
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
    status: int | Unset = UNSET,
    type_: int | Unset = UNSET,
    limit: int | Unset = UNSET,
    offset: int | Unset = UNSET,
    order: str | Unset = UNSET,
    direction: str | Unset = UNSET,
) -> (
    Any
    | GetAdvV1AdvertsResponse401
    | GetAdvV1AdvertsResponse429
    | list[GetAdvV1AdvertsResponse200Item]
    | None
):
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
        status (int | Unset):  Example: 1.
        type_ (int | Unset):  Example: 1.
        limit (int | Unset):  Example: 1.
        offset (int | Unset):  Example: 1.
        order (str | Unset):  Example: id.
        direction (str | Unset):  Example: desc.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | GetAdvV1AdvertsResponse401 | GetAdvV1AdvertsResponse429 | list[GetAdvV1AdvertsResponse200Item]
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
