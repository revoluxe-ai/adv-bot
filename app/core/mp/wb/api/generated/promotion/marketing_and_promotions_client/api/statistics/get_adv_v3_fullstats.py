import datetime
from http import HTTPStatus
from typing import Any

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
    ids: str,
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
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    FullStatsError
    | GetAdvV3FullstatsResponse401
    | GetAdvV3FullstatsResponse429
    | list[FullStatsItem]
    | None
):
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
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    FullStatsError
    | GetAdvV3FullstatsResponse401
    | GetAdvV3FullstatsResponse429
    | list[FullStatsItem]
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
    ids: str,
    begin_date: datetime.date,
    end_date: datetime.date,
) -> Response[
    FullStatsError
    | GetAdvV3FullstatsResponse401
    | GetAdvV3FullstatsResponse429
    | list[FullStatsItem]
]:
    r"""Campaigns Statistics

     The method generates statistics for campaigns, regardless of their type.
    <br><br>
    The maximum period in a request is 31 days.
    <br><br>
    For campaigns in statuses `7`, `9` and `11`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 minute | 3 requests | 20 seconds | 1 request |
    </div>

    Args:
        ids (str):  Example: 22161678,28449281,28155229.
        begin_date (datetime.date):
        end_date (datetime.date):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[FullStatsError | GetAdvV3FullstatsResponse401 | GetAdvV3FullstatsResponse429 | list[FullStatsItem]]
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
) -> (
    FullStatsError
    | GetAdvV3FullstatsResponse401
    | GetAdvV3FullstatsResponse429
    | list[FullStatsItem]
    | None
):
    r"""Campaigns Statistics

     The method generates statistics for campaigns, regardless of their type.
    <br><br>
    The maximum period in a request is 31 days.
    <br><br>
    For campaigns in statuses `7`, `9` and `11`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 minute | 3 requests | 20 seconds | 1 request |
    </div>

    Args:
        ids (str):  Example: 22161678,28449281,28155229.
        begin_date (datetime.date):
        end_date (datetime.date):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        FullStatsError | GetAdvV3FullstatsResponse401 | GetAdvV3FullstatsResponse429 | list[FullStatsItem]
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
) -> Response[
    FullStatsError
    | GetAdvV3FullstatsResponse401
    | GetAdvV3FullstatsResponse429
    | list[FullStatsItem]
]:
    r"""Campaigns Statistics

     The method generates statistics for campaigns, regardless of their type.
    <br><br>
    The maximum period in a request is 31 days.
    <br><br>
    For campaigns in statuses `7`, `9` and `11`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 minute | 3 requests | 20 seconds | 1 request |
    </div>

    Args:
        ids (str):  Example: 22161678,28449281,28155229.
        begin_date (datetime.date):
        end_date (datetime.date):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[FullStatsError | GetAdvV3FullstatsResponse401 | GetAdvV3FullstatsResponse429 | list[FullStatsItem]]
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
) -> (
    FullStatsError
    | GetAdvV3FullstatsResponse401
    | GetAdvV3FullstatsResponse429
    | list[FullStatsItem]
    | None
):
    r"""Campaigns Statistics

     The method generates statistics for campaigns, regardless of their type.
    <br><br>
    The maximum period in a request is 31 days.
    <br><br>
    For campaigns in statuses `7`, `9` and `11`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 minute | 3 requests | 20 seconds | 1 request |
    </div>

    Args:
        ids (str):  Example: 22161678,28449281,28155229.
        begin_date (datetime.date):
        end_date (datetime.date):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        FullStatsError | GetAdvV3FullstatsResponse401 | GetAdvV3FullstatsResponse429 | list[FullStatsItem]
    """

    return (
        await asyncio_detailed(
            client=client,
            ids=ids,
            begin_date=begin_date,
            end_date=end_date,
        )
    ).parsed
