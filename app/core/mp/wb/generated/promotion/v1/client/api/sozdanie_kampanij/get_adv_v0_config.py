from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_adv_v0_config_response_200 import GetAdvV0ConfigResponse200
from ...models.get_adv_v0_config_response_401 import GetAdvV0ConfigResponse401
from ...models.get_adv_v0_config_response_429 import GetAdvV0ConfigResponse429
from ...types import Response


def _get_kwargs() -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/adv/v0/config",
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[
        GetAdvV0ConfigResponse200, GetAdvV0ConfigResponse401, GetAdvV0ConfigResponse429
    ]
]:
    if response.status_code == 200:
        response_200 = GetAdvV0ConfigResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = GetAdvV0ConfigResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = GetAdvV0ConfigResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[
    Union[
        GetAdvV0ConfigResponse200, GetAdvV0ConfigResponse401, GetAdvV0ConfigResponse429
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
) -> Response[
    Union[
        GetAdvV0ConfigResponse200, GetAdvV0ConfigResponse401, GetAdvV0ConfigResponse429
    ]
]:
    r"""Konfiguratsionnye znachenija Prodvizhenija

     Metod vozvraschaet dopustimye znachenija osnovnyh parametrov konfiguratsii
    [kampanij](/openapi/promotion#tag/Kampanii/paths/~1adv~1v1~1promotion~1adverts/post): naprimer,
    minimal'nye stavki, dostupnye kategorii i maksimal'noe kolichestvo tovarov, kotorye mozhno dobavit'
    v kampaniju.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 1 zapros | 1 minuta | 1 zapros |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[GetAdvV0ConfigResponse200, GetAdvV0ConfigResponse401, GetAdvV0ConfigResponse429]]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
) -> Optional[
    Union[
        GetAdvV0ConfigResponse200, GetAdvV0ConfigResponse401, GetAdvV0ConfigResponse429
    ]
]:
    r"""Konfiguratsionnye znachenija Prodvizhenija

     Metod vozvraschaet dopustimye znachenija osnovnyh parametrov konfiguratsii
    [kampanij](/openapi/promotion#tag/Kampanii/paths/~1adv~1v1~1promotion~1adverts/post): naprimer,
    minimal'nye stavki, dostupnye kategorii i maksimal'noe kolichestvo tovarov, kotorye mozhno dobavit'
    v kampaniju.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 1 zapros | 1 minuta | 1 zapros |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[GetAdvV0ConfigResponse200, GetAdvV0ConfigResponse401, GetAdvV0ConfigResponse429]
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
) -> Response[
    Union[
        GetAdvV0ConfigResponse200, GetAdvV0ConfigResponse401, GetAdvV0ConfigResponse429
    ]
]:
    r"""Konfiguratsionnye znachenija Prodvizhenija

     Metod vozvraschaet dopustimye znachenija osnovnyh parametrov konfiguratsii
    [kampanij](/openapi/promotion#tag/Kampanii/paths/~1adv~1v1~1promotion~1adverts/post): naprimer,
    minimal'nye stavki, dostupnye kategorii i maksimal'noe kolichestvo tovarov, kotorye mozhno dobavit'
    v kampaniju.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 1 zapros | 1 minuta | 1 zapros |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[GetAdvV0ConfigResponse200, GetAdvV0ConfigResponse401, GetAdvV0ConfigResponse429]]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
) -> Optional[
    Union[
        GetAdvV0ConfigResponse200, GetAdvV0ConfigResponse401, GetAdvV0ConfigResponse429
    ]
]:
    r"""Konfiguratsionnye znachenija Prodvizhenija

     Metod vozvraschaet dopustimye znachenija osnovnyh parametrov konfiguratsii
    [kampanij](/openapi/promotion#tag/Kampanii/paths/~1adv~1v1~1promotion~1adverts/post): naprimer,
    minimal'nye stavki, dostupnye kategorii i maksimal'noe kolichestvo tovarov, kotorye mozhno dobavit'
    v kampaniju.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 1 zapros | 1 minuta | 1 zapros |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[GetAdvV0ConfigResponse200, GetAdvV0ConfigResponse401, GetAdvV0ConfigResponse429]
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
