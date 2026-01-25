from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_adv_v1_count_response_200 import GetAdvV1CountResponse200
from ...models.get_adv_v1_count_response_401 import GetAdvV1CountResponse401
from ...models.get_adv_v1_count_response_429 import GetAdvV1CountResponse429
from ...types import Response


def _get_kwargs() -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/adv/v1/count",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    GetAdvV1CountResponse200
    | GetAdvV1CountResponse401
    | GetAdvV1CountResponse429
    | None
):
    if response.status_code == 200:
        response_200 = GetAdvV1CountResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = GetAdvV1CountResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = GetAdvV1CountResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    GetAdvV1CountResponse200 | GetAdvV1CountResponse401 | GetAdvV1CountResponse429
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
) -> Response[
    GetAdvV1CountResponse200 | GetAdvV1CountResponse401 | GetAdvV1CountResponse429
]:
    r"""Kolichestvo mediakampanij

     Metod vozvraschaet kolichestvo
    [mediakampanij](/openapi/promotion#tag/Media/paths/~1adv~1v1~1advert/get) prodavtsa s gruppirovkoj
    po statusam.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 10 zaprosov | 100 millisekund | 10 zaprosov |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetAdvV1CountResponse200 | GetAdvV1CountResponse401 | GetAdvV1CountResponse429]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
) -> (
    GetAdvV1CountResponse200
    | GetAdvV1CountResponse401
    | GetAdvV1CountResponse429
    | None
):
    r"""Kolichestvo mediakampanij

     Metod vozvraschaet kolichestvo
    [mediakampanij](/openapi/promotion#tag/Media/paths/~1adv~1v1~1advert/get) prodavtsa s gruppirovkoj
    po statusam.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 10 zaprosov | 100 millisekund | 10 zaprosov |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetAdvV1CountResponse200 | GetAdvV1CountResponse401 | GetAdvV1CountResponse429
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
) -> Response[
    GetAdvV1CountResponse200 | GetAdvV1CountResponse401 | GetAdvV1CountResponse429
]:
    r"""Kolichestvo mediakampanij

     Metod vozvraschaet kolichestvo
    [mediakampanij](/openapi/promotion#tag/Media/paths/~1adv~1v1~1advert/get) prodavtsa s gruppirovkoj
    po statusam.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 10 zaprosov | 100 millisekund | 10 zaprosov |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetAdvV1CountResponse200 | GetAdvV1CountResponse401 | GetAdvV1CountResponse429]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
) -> (
    GetAdvV1CountResponse200
    | GetAdvV1CountResponse401
    | GetAdvV1CountResponse429
    | None
):
    r"""Kolichestvo mediakampanij

     Metod vozvraschaet kolichestvo
    [mediakampanij](/openapi/promotion#tag/Media/paths/~1adv~1v1~1advert/get) prodavtsa s gruppirovkoj
    po statusam.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 10 zaprosov | 100 millisekund | 10 zaprosov |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetAdvV1CountResponse200 | GetAdvV1CountResponse401 | GetAdvV1CountResponse429
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
