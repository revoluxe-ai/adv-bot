import datetime
from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.measurement_penalties import MeasurementPenalties
from ...models.response_400_retentions import Response400Retentions
from ...models.response_403_retentions import Response403Retentions
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    date_from: Union[Unset, datetime.datetime] = UNSET,
    date_to: datetime.datetime,
    limit: int,
    offset: Union[Unset, int] = 0,
) -> Dict[str, Any]:

    params: Dict[str, Any] = {}

    json_date_from: Union[Unset, str] = UNSET
    if not isinstance(date_from, Unset):
        json_date_from = date_from.isoformat()
    params["dateFrom"] = json_date_from

    json_date_to = date_to.isoformat()
    params["dateTo"] = json_date_to

    params["limit"] = limit

    params["offset"] = offset

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": "/api/analytics/v1/measurement-penalties",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[Any, MeasurementPenalties, Response400Retentions, Response403Retentions]
]:
    if response.status_code == HTTPStatus.OK:
        response_200 = MeasurementPenalties.from_dict(response.json())

        return response_200
    if response.status_code == HTTPStatus.BAD_REQUEST:
        response_400 = Response400Retentions.from_dict(response.json())

        return response_400
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        response_401 = cast(Any, None)
        return response_401
    if response.status_code == HTTPStatus.PAYMENT_REQUIRED:
        response_402 = cast(Any, None)
        return response_402
    if response.status_code == HTTPStatus.FORBIDDEN:
        response_403 = Response403Retentions.from_dict(response.json())

        return response_403
    if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
        response_429 = cast(Any, None)
        return response_429
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[
    Union[Any, MeasurementPenalties, Response400Retentions, Response403Retentions]
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
    date_from: Union[Unset, datetime.datetime] = UNSET,
    date_to: datetime.datetime,
    limit: int,
    offset: Union[Unset, int] = 0,
) -> Response[
    Union[Any, MeasurementPenalties, Response400Retentions, Response403Retentions]
]:
    r"""Logistics and Storage Costs Multiplier

     The method returns a report with [logistics and storage costs
    multiplier](https://seller.wildberries.ru/analytics-reports/dimensions-penalties)

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/introduction/Rate-Limits\">Request limit</a> per one seller
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 1 request | 1 min | 1 request |
    | Service | 1 min | 1 request | 1 min | 1 request |
    | Base with secret | 1 min | 1 request | 1 min | 1 request |
    | Base | 6 h | 1 request | 6 h | 1 request |
    </div>

    Args:
        date_from (Union[Unset, datetime.datetime]):
        date_to (datetime.datetime):
        limit (int):  Example: 330.
        offset (Union[Unset, int]):  Default: 0. Example: 220.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, MeasurementPenalties, Response400Retentions, Response403Retentions]]
    """

    kwargs = _get_kwargs(
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    date_from: Union[Unset, datetime.datetime] = UNSET,
    date_to: datetime.datetime,
    limit: int,
    offset: Union[Unset, int] = 0,
) -> Optional[
    Union[Any, MeasurementPenalties, Response400Retentions, Response403Retentions]
]:
    r"""Logistics and Storage Costs Multiplier

     The method returns a report with [logistics and storage costs
    multiplier](https://seller.wildberries.ru/analytics-reports/dimensions-penalties)

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/introduction/Rate-Limits\">Request limit</a> per one seller
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 1 request | 1 min | 1 request |
    | Service | 1 min | 1 request | 1 min | 1 request |
    | Base with secret | 1 min | 1 request | 1 min | 1 request |
    | Base | 6 h | 1 request | 6 h | 1 request |
    </div>

    Args:
        date_from (Union[Unset, datetime.datetime]):
        date_to (datetime.datetime):
        limit (int):  Example: 330.
        offset (Union[Unset, int]):  Default: 0. Example: 220.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, MeasurementPenalties, Response400Retentions, Response403Retentions]
    """

    return sync_detailed(
        client=client,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    date_from: Union[Unset, datetime.datetime] = UNSET,
    date_to: datetime.datetime,
    limit: int,
    offset: Union[Unset, int] = 0,
) -> Response[
    Union[Any, MeasurementPenalties, Response400Retentions, Response403Retentions]
]:
    r"""Logistics and Storage Costs Multiplier

     The method returns a report with [logistics and storage costs
    multiplier](https://seller.wildberries.ru/analytics-reports/dimensions-penalties)

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/introduction/Rate-Limits\">Request limit</a> per one seller
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 1 request | 1 min | 1 request |
    | Service | 1 min | 1 request | 1 min | 1 request |
    | Base with secret | 1 min | 1 request | 1 min | 1 request |
    | Base | 6 h | 1 request | 6 h | 1 request |
    </div>

    Args:
        date_from (Union[Unset, datetime.datetime]):
        date_to (datetime.datetime):
        limit (int):  Example: 330.
        offset (Union[Unset, int]):  Default: 0. Example: 220.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, MeasurementPenalties, Response400Retentions, Response403Retentions]]
    """

    kwargs = _get_kwargs(
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    date_from: Union[Unset, datetime.datetime] = UNSET,
    date_to: datetime.datetime,
    limit: int,
    offset: Union[Unset, int] = 0,
) -> Optional[
    Union[Any, MeasurementPenalties, Response400Retentions, Response403Retentions]
]:
    r"""Logistics and Storage Costs Multiplier

     The method returns a report with [logistics and storage costs
    multiplier](https://seller.wildberries.ru/analytics-reports/dimensions-penalties)

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/introduction/Rate-Limits\">Request limit</a> per one seller
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 1 request | 1 min | 1 request |
    | Service | 1 min | 1 request | 1 min | 1 request |
    | Base with secret | 1 min | 1 request | 1 min | 1 request |
    | Base | 6 h | 1 request | 6 h | 1 request |
    </div>

    Args:
        date_from (Union[Unset, datetime.datetime]):
        date_to (datetime.datetime):
        limit (int):  Example: 330.
        offset (Union[Unset, int]):  Default: 0. Example: 220.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, MeasurementPenalties, Response400Retentions, Response403Retentions]
    """

    return (
        await asyncio_detailed(
            client=client,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )
    ).parsed
