import datetime
from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    start_date_time: datetime.datetime,
    end_date_time: datetime.datetime,
    all_promo: bool = False,
    limit: Union[Unset, int] = UNSET,
    offset: Union[Unset, int] = UNSET,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    json_start_date_time = start_date_time.isoformat()
    params["startDateTime"] = json_start_date_time

    json_end_date_time = end_date_time.isoformat()
    params["endDateTime"] = json_end_date_time

    params["allPromo"] = all_promo

    params["limit"] = limit

    params["offset"] = offset

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/calendar/promotions",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Any]:
    if response.status_code == HTTPStatus.OK:
        return None
    if response.status_code == HTTPStatus.BAD_REQUEST:
        return None
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        return None
    if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
        return None
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Any]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    start_date_time: datetime.datetime,
    end_date_time: datetime.datetime,
    all_promo: bool = False,
    limit: Union[Unset, int] = UNSET,
    offset: Union[Unset, int] = UNSET,
) -> Response[Any]:
    r"""Promotions List

     Returns a promotions list with dates and times of occurrence

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account for all methods in the <strong>Promotions Calendar</strong> category:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 6 s | 10 requests | 600 ms | 5 requests |

    </div>

    Args:
        start_date_time (datetime.datetime):  Example: 2023-09-01T00:00:00Z.
        end_date_time (datetime.datetime):  Example: 2024-08-01T23:59:59Z.
        all_promo (bool):  Default: False.
        limit (Union[Unset, int]):  Example: 10.
        offset (Union[Unset, int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any]
    """

    kwargs = _get_kwargs(
        start_date_time=start_date_time,
        end_date_time=end_date_time,
        all_promo=all_promo,
        limit=limit,
        offset=offset,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    start_date_time: datetime.datetime,
    end_date_time: datetime.datetime,
    all_promo: bool = False,
    limit: Union[Unset, int] = UNSET,
    offset: Union[Unset, int] = UNSET,
) -> Response[Any]:
    r"""Promotions List

     Returns a promotions list with dates and times of occurrence

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account for all methods in the <strong>Promotions Calendar</strong> category:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 6 s | 10 requests | 600 ms | 5 requests |

    </div>

    Args:
        start_date_time (datetime.datetime):  Example: 2023-09-01T00:00:00Z.
        end_date_time (datetime.datetime):  Example: 2024-08-01T23:59:59Z.
        all_promo (bool):  Default: False.
        limit (Union[Unset, int]):  Example: 10.
        offset (Union[Unset, int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any]
    """

    kwargs = _get_kwargs(
        start_date_time=start_date_time,
        end_date_time=end_date_time,
        all_promo=all_promo,
        limit=limit,
        offset=offset,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)
