import datetime
from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_response import ErrorResponse
from ...models.get_adv_v0_stats_keywords_response_401 import (
    GetAdvV0StatsKeywordsResponse401,
)
from ...models.get_adv_v0_stats_keywords_response_429 import (
    GetAdvV0StatsKeywordsResponse429,
)
from ...models.v0_keywords_statistics_response import V0KeywordsStatisticsResponse
from ...types import UNSET, Response


def _get_kwargs(
    *,
    advert_id: int,
    from_: datetime.date,
    to: datetime.date,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["advert_id"] = advert_id

    json_from_ = from_.isoformat()
    params["from"] = json_from_

    json_to = to.isoformat()
    params["to"] = json_to

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/adv/v0/stats/keywords",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    ErrorResponse
    | GetAdvV0StatsKeywordsResponse401
    | GetAdvV0StatsKeywordsResponse429
    | V0KeywordsStatisticsResponse
    | None
):
    if response.status_code == 200:
        response_200 = V0KeywordsStatisticsResponse.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = ErrorResponse.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = GetAdvV0StatsKeywordsResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 404:
        response_404 = ErrorResponse.from_dict(response.json())

        return response_404

    if response.status_code == 429:
        response_429 = GetAdvV0StatsKeywordsResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    ErrorResponse
    | GetAdvV0StatsKeywordsResponse401
    | GetAdvV0StatsKeywordsResponse429
    | V0KeywordsStatisticsResponse
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
    advert_id: int,
    from_: datetime.date,
    to: datetime.date,
) -> Response[
    ErrorResponse
    | GetAdvV0StatsKeywordsResponse401
    | GetAdvV0StatsKeywordsResponse429
    | V0KeywordsStatisticsResponse
]:
    """Statistika po kljuchevym frazam

     Dannyj metod ustarel. On budet udalen [15 janvarja](https://dev.wildberries.ru/release-notes?id=385)

    Args:
        advert_id (int):
        from_ (datetime.date):
        to (datetime.date):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | GetAdvV0StatsKeywordsResponse401 | GetAdvV0StatsKeywordsResponse429 | V0KeywordsStatisticsResponse]
    """

    kwargs = _get_kwargs(
        advert_id=advert_id,
        from_=from_,
        to=to,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    advert_id: int,
    from_: datetime.date,
    to: datetime.date,
) -> (
    ErrorResponse
    | GetAdvV0StatsKeywordsResponse401
    | GetAdvV0StatsKeywordsResponse429
    | V0KeywordsStatisticsResponse
    | None
):
    """Statistika po kljuchevym frazam

     Dannyj metod ustarel. On budet udalen [15 janvarja](https://dev.wildberries.ru/release-notes?id=385)

    Args:
        advert_id (int):
        from_ (datetime.date):
        to (datetime.date):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | GetAdvV0StatsKeywordsResponse401 | GetAdvV0StatsKeywordsResponse429 | V0KeywordsStatisticsResponse
    """

    return sync_detailed(
        client=client,
        advert_id=advert_id,
        from_=from_,
        to=to,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    advert_id: int,
    from_: datetime.date,
    to: datetime.date,
) -> Response[
    ErrorResponse
    | GetAdvV0StatsKeywordsResponse401
    | GetAdvV0StatsKeywordsResponse429
    | V0KeywordsStatisticsResponse
]:
    """Statistika po kljuchevym frazam

     Dannyj metod ustarel. On budet udalen [15 janvarja](https://dev.wildberries.ru/release-notes?id=385)

    Args:
        advert_id (int):
        from_ (datetime.date):
        to (datetime.date):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | GetAdvV0StatsKeywordsResponse401 | GetAdvV0StatsKeywordsResponse429 | V0KeywordsStatisticsResponse]
    """

    kwargs = _get_kwargs(
        advert_id=advert_id,
        from_=from_,
        to=to,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    advert_id: int,
    from_: datetime.date,
    to: datetime.date,
) -> (
    ErrorResponse
    | GetAdvV0StatsKeywordsResponse401
    | GetAdvV0StatsKeywordsResponse429
    | V0KeywordsStatisticsResponse
    | None
):
    """Statistika po kljuchevym frazam

     Dannyj metod ustarel. On budet udalen [15 janvarja](https://dev.wildberries.ru/release-notes?id=385)

    Args:
        advert_id (int):
        from_ (datetime.date):
        to (datetime.date):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | GetAdvV0StatsKeywordsResponse401 | GetAdvV0StatsKeywordsResponse429 | V0KeywordsStatisticsResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            advert_id=advert_id,
            from_=from_,
            to=to,
        )
    ).parsed
