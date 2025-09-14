from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_adv_v1_advert_response_200 import GetAdvV1AdvertResponse200
from ...models.get_adv_v1_advert_response_401 import GetAdvV1AdvertResponse401
from ...models.get_adv_v1_advert_response_429 import GetAdvV1AdvertResponse429
from ...types import UNSET, Response


def _get_kwargs(
    *,
    id: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["id"] = id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/adv/v1/advert",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[
        GetAdvV1AdvertResponse200, GetAdvV1AdvertResponse401, GetAdvV1AdvertResponse429
    ]
]:
    if response.status_code == 200:
        response_200 = GetAdvV1AdvertResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = GetAdvV1AdvertResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = GetAdvV1AdvertResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[
    Union[
        GetAdvV1AdvertResponse200, GetAdvV1AdvertResponse401, GetAdvV1AdvertResponse429
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
    id: int,
) -> Response[
    Union[
        GetAdvV1AdvertResponse200, GetAdvV1AdvertResponse401, GetAdvV1AdvertResponse429
    ]
]:
    r"""Informatsija o mediakampanii

     Metod vozvraschaet informatsiju o kampanii [WB Media](https://cmp.wildberries.ru/cmpf/list). Vmesto
    kartochek tovarov v mediakampanijah prodvigajutsja reklamnye bannery prodavtsa na sajte i v
    prilozhenii WB.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 10 zaprosov | 100 millisekund | 10 zaprosov |
    </div>

    Args:
        id (int):  Example: 23569.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[GetAdvV1AdvertResponse200, GetAdvV1AdvertResponse401, GetAdvV1AdvertResponse429]]
    """

    kwargs = _get_kwargs(
        id=id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    id: int,
) -> Optional[
    Union[
        GetAdvV1AdvertResponse200, GetAdvV1AdvertResponse401, GetAdvV1AdvertResponse429
    ]
]:
    r"""Informatsija o mediakampanii

     Metod vozvraschaet informatsiju o kampanii [WB Media](https://cmp.wildberries.ru/cmpf/list). Vmesto
    kartochek tovarov v mediakampanijah prodvigajutsja reklamnye bannery prodavtsa na sajte i v
    prilozhenii WB.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 10 zaprosov | 100 millisekund | 10 zaprosov |
    </div>

    Args:
        id (int):  Example: 23569.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[GetAdvV1AdvertResponse200, GetAdvV1AdvertResponse401, GetAdvV1AdvertResponse429]
    """

    return sync_detailed(
        client=client,
        id=id,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    id: int,
) -> Response[
    Union[
        GetAdvV1AdvertResponse200, GetAdvV1AdvertResponse401, GetAdvV1AdvertResponse429
    ]
]:
    r"""Informatsija o mediakampanii

     Metod vozvraschaet informatsiju o kampanii [WB Media](https://cmp.wildberries.ru/cmpf/list). Vmesto
    kartochek tovarov v mediakampanijah prodvigajutsja reklamnye bannery prodavtsa na sajte i v
    prilozhenii WB.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 10 zaprosov | 100 millisekund | 10 zaprosov |
    </div>

    Args:
        id (int):  Example: 23569.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[GetAdvV1AdvertResponse200, GetAdvV1AdvertResponse401, GetAdvV1AdvertResponse429]]
    """

    kwargs = _get_kwargs(
        id=id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    id: int,
) -> Optional[
    Union[
        GetAdvV1AdvertResponse200, GetAdvV1AdvertResponse401, GetAdvV1AdvertResponse429
    ]
]:
    r"""Informatsija o mediakampanii

     Metod vozvraschaet informatsiju o kampanii [WB Media](https://cmp.wildberries.ru/cmpf/list). Vmesto
    kartochek tovarov v mediakampanijah prodvigajutsja reklamnye bannery prodavtsa na sajte i v
    prilozhenii WB.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 10 zaprosov | 100 millisekund | 10 zaprosov |
    </div>

    Args:
        id (int):  Example: 23569.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[GetAdvV1AdvertResponse200, GetAdvV1AdvertResponse401, GetAdvV1AdvertResponse429]
    """

    return (
        await asyncio_detailed(
            client=client,
            id=id,
        )
    ).parsed
