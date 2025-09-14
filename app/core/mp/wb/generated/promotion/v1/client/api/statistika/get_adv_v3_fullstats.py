import datetime
from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.full_stats_error import FullStatsError
from ...models.full_stats_item import FullStatsItem
from ...models.get_adv_v3_fullstats_response_401 import GetAdvV3FullstatsResponse401
from ...models.get_adv_v3_fullstats_response_429 import GetAdvV3FullstatsResponse429
from ...types import UNSET, Response


def _get_kwargs(
    *,
    ids: Any,
    begin_date: datetime.date,
    end_date: datetime.date,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["ids"] = ids

    json_begin_date = begin_date.isoformat()
    params["beginDate"] = json_begin_date

    json_end_date = end_date.isoformat()
    params["endDate"] = json_end_date

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/adv/v3/fullstats",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[
        FullStatsError,
        GetAdvV3FullstatsResponse401,
        GetAdvV3FullstatsResponse429,
        list["FullStatsItem"],
    ]
]:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for componentsschemas_response_full_stats_item_data in _response_200:
            componentsschemas_response_full_stats_item = FullStatsItem.from_dict(
                componentsschemas_response_full_stats_item_data
            )

            response_200.append(componentsschemas_response_full_stats_item)

        return response_200

    if response.status_code == 400:
        response_400 = FullStatsError.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = GetAdvV3FullstatsResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = GetAdvV3FullstatsResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[
    Union[
        FullStatsError,
        GetAdvV3FullstatsResponse401,
        GetAdvV3FullstatsResponse429,
        list["FullStatsItem"],
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
    ids: Any,
    begin_date: datetime.date,
    end_date: datetime.date,
) -> Response[
    Union[
        FullStatsError,
        GetAdvV3FullstatsResponse401,
        GetAdvV3FullstatsResponse429,
        list["FullStatsItem"],
    ]
]:
    r"""Statistika kampanij

     Metod formiruet statistiku dlja kampanij nezavisimo ot tipa.
    <br><br>
    Maksimal'nyj period v zaprose — 31 den'.
    <br><br>
    Dlja kampanij v statusah `7`, `9` i `11`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 1 zapros | 1 minuta | 1 zapros |
    </div>

    Args:
        ids (Any):  Example: 22161678,28449281,28155229.
        begin_date (datetime.date):
        end_date (datetime.date):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[FullStatsError, GetAdvV3FullstatsResponse401, GetAdvV3FullstatsResponse429, list['FullStatsItem']]]
    """

    kwargs = _get_kwargs(
        ids=ids,
        begin_date=begin_date,
        end_date=end_date,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    ids: Any,
    begin_date: datetime.date,
    end_date: datetime.date,
) -> Optional[
    Union[
        FullStatsError,
        GetAdvV3FullstatsResponse401,
        GetAdvV3FullstatsResponse429,
        list["FullStatsItem"],
    ]
]:
    r"""Statistika kampanij

     Metod formiruet statistiku dlja kampanij nezavisimo ot tipa.
    <br><br>
    Maksimal'nyj period v zaprose — 31 den'.
    <br><br>
    Dlja kampanij v statusah `7`, `9` i `11`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 1 zapros | 1 minuta | 1 zapros |
    </div>

    Args:
        ids (Any):  Example: 22161678,28449281,28155229.
        begin_date (datetime.date):
        end_date (datetime.date):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[FullStatsError, GetAdvV3FullstatsResponse401, GetAdvV3FullstatsResponse429, list['FullStatsItem']]
    """

    return sync_detailed(
        client=client,
        ids=ids,
        begin_date=begin_date,
        end_date=end_date,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    ids: Any,
    begin_date: datetime.date,
    end_date: datetime.date,
) -> Response[
    Union[
        FullStatsError,
        GetAdvV3FullstatsResponse401,
        GetAdvV3FullstatsResponse429,
        list["FullStatsItem"],
    ]
]:
    r"""Statistika kampanij

     Metod formiruet statistiku dlja kampanij nezavisimo ot tipa.
    <br><br>
    Maksimal'nyj period v zaprose — 31 den'.
    <br><br>
    Dlja kampanij v statusah `7`, `9` i `11`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 1 zapros | 1 minuta | 1 zapros |
    </div>

    Args:
        ids (Any):  Example: 22161678,28449281,28155229.
        begin_date (datetime.date):
        end_date (datetime.date):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[FullStatsError, GetAdvV3FullstatsResponse401, GetAdvV3FullstatsResponse429, list['FullStatsItem']]]
    """

    kwargs = _get_kwargs(
        ids=ids,
        begin_date=begin_date,
        end_date=end_date,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    ids: Any,
    begin_date: datetime.date,
    end_date: datetime.date,
) -> Optional[
    Union[
        FullStatsError,
        GetAdvV3FullstatsResponse401,
        GetAdvV3FullstatsResponse429,
        list["FullStatsItem"],
    ]
]:
    r"""Statistika kampanij

     Metod formiruet statistiku dlja kampanij nezavisimo ot tipa.
    <br><br>
    Maksimal'nyj period v zaprose — 31 den'.
    <br><br>
    Dlja kampanij v statusah `7`, `9` i `11`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 1 zapros | 1 minuta | 1 zapros |
    </div>

    Args:
        ids (Any):  Example: 22161678,28449281,28155229.
        begin_date (datetime.date):
        end_date (datetime.date):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[FullStatsError, GetAdvV3FullstatsResponse401, GetAdvV3FullstatsResponse429, list['FullStatsItem']]
    """

    return (
        await asyncio_detailed(
            client=client,
            ids=ids,
            begin_date=begin_date,
            end_date=end_date,
        )
    ).parsed
