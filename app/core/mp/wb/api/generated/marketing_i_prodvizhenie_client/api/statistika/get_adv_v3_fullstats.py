import datetime
from http import HTTPStatus
from typing import Any, Dict, List, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.full_stats_error import FullStatsError
from ...models.full_stats_item import FullStatsItem
from ...types import UNSET, Response


def _get_kwargs(
    *,
    ids: str,
    begin_date: datetime.date,
    end_date: datetime.date,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    params["ids"] = ids

    json_begin_date = begin_date.isoformat()
    params["beginDate"] = json_begin_date

    json_end_date = end_date.isoformat()
    params["endDate"] = json_end_date

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": "/adv/v3/fullstats",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, FullStatsError, List["FullStatsItem"]]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = []
        _response_200 = response.json()
        for componentsschemas_response_full_stats_item_data in _response_200:
            componentsschemas_response_full_stats_item = FullStatsItem.from_dict(
                componentsschemas_response_full_stats_item_data
            )

            response_200.append(componentsschemas_response_full_stats_item)

        return response_200
    if response.status_code == HTTPStatus.BAD_REQUEST:
        response_400 = FullStatsError.from_dict(response.json())

        return response_400
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        response_401 = cast(Any, None)
        return response_401
    if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
        response_429 = cast(Any, None)
        return response_429
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[Any, FullStatsError, List["FullStatsItem"]]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    ids: str,
    begin_date: datetime.date,
    end_date: datetime.date,
) -> Response[Union[Any, FullStatsError, List["FullStatsItem"]]]:
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
    | 1 minuta | 3 zaprosa | 20 sekund | 1 zapros |
    </div>

    Args:
        ids (str):  Example: 22161678,28449281,28155229.
        begin_date (datetime.date):
        end_date (datetime.date):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, FullStatsError, List['FullStatsItem']]]
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
    ids: str,
    begin_date: datetime.date,
    end_date: datetime.date,
) -> Optional[Union[Any, FullStatsError, List["FullStatsItem"]]]:
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
    | 1 minuta | 3 zaprosa | 20 sekund | 1 zapros |
    </div>

    Args:
        ids (str):  Example: 22161678,28449281,28155229.
        begin_date (datetime.date):
        end_date (datetime.date):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, FullStatsError, List['FullStatsItem']]
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
    ids: str,
    begin_date: datetime.date,
    end_date: datetime.date,
) -> Response[Union[Any, FullStatsError, List["FullStatsItem"]]]:
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
    | 1 minuta | 3 zaprosa | 20 sekund | 1 zapros |
    </div>

    Args:
        ids (str):  Example: 22161678,28449281,28155229.
        begin_date (datetime.date):
        end_date (datetime.date):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, FullStatsError, List['FullStatsItem']]]
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
    ids: str,
    begin_date: datetime.date,
    end_date: datetime.date,
) -> Optional[Union[Any, FullStatsError, List["FullStatsItem"]]]:
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
    | 1 minuta | 3 zaprosa | 20 sekund | 1 zapros |
    </div>

    Args:
        ids (str):  Example: 22161678,28449281,28155229.
        begin_date (datetime.date):
        end_date (datetime.date):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, FullStatsError, List['FullStatsItem']]
    """

    return (
        await asyncio_detailed(
            client=client,
            ids=ids,
            begin_date=begin_date,
            end_date=end_date,
        )
    ).parsed
