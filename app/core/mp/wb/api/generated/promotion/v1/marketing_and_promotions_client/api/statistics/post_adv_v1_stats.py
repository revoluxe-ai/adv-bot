from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_adv_v1_stats_response_401 import PostAdvV1StatsResponse401
from ...models.post_adv_v1_stats_response_429 import PostAdvV1StatsResponse429
from ...models.request_with_campaign_id import RequestWithCampaignID
from ...models.request_with_date import RequestWithDate
from ...models.request_with_interval import RequestWithInterval
from ...models.response_adv_error_1 import ResponseAdvError1
from ...models.stat import Stat
from ...models.stat_date import StatDate
from ...models.stat_interval import StatInterval
from ...types import Response


def _get_kwargs(
    *,
    body: list[RequestWithCampaignID | RequestWithDate | RequestWithInterval],
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/adv/v1/stats",
    }

    _kwargs["json"] = []
    for body_item_data in body:
        body_item: dict[str, Any]
        if isinstance(body_item_data, RequestWithDate):
            body_item = body_item_data.to_dict()
        elif isinstance(body_item_data, RequestWithInterval):
            body_item = body_item_data.to_dict()
        else:
            body_item = body_item_data.to_dict()

        _kwargs["json"].append(body_item)

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    PostAdvV1StatsResponse401
    | PostAdvV1StatsResponse429
    | ResponseAdvError1
    | list[Stat | StatDate | StatInterval]
    | None
):
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:

            def _parse_response_200_item(
                data: object,
            ) -> Stat | StatDate | StatInterval:
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    response_200_item_type_0 = StatInterval.from_dict(data)

                    return response_200_item_type_0
                except (TypeError, ValueError, AttributeError, KeyError):
                    pass
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    response_200_item_type_1 = StatDate.from_dict(data)

                    return response_200_item_type_1
                except (TypeError, ValueError, AttributeError, KeyError):
                    pass
                if not isinstance(data, dict):
                    raise TypeError()
                response_200_item_type_2 = Stat.from_dict(data)

                return response_200_item_type_2

            response_200_item = _parse_response_200_item(response_200_item_data)

            response_200.append(response_200_item)

        return response_200

    if response.status_code == 400:
        response_400 = ResponseAdvError1.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostAdvV1StatsResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = PostAdvV1StatsResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    PostAdvV1StatsResponse401
    | PostAdvV1StatsResponse429
    | ResponseAdvError1
    | list[Stat | StatDate | StatInterval]
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
    body: list[RequestWithCampaignID | RequestWithDate | RequestWithInterval],
) -> Response[
    PostAdvV1StatsResponse401
    | PostAdvV1StatsResponse429
    | ResponseAdvError1
    | list[Stat | StatDate | StatInterval]
]:
    r"""Media Campaign Statistics

     The method allows to get statistics of [WB Media](https://cmp.wildberries.ru/cmpf/statistics)
    campaigns

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 10 requests | 100 milliseconds | 10 requests |
    </div>

    Args:
        body (list[RequestWithCampaignID | RequestWithDate | RequestWithInterval]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostAdvV1StatsResponse401 | PostAdvV1StatsResponse429 | ResponseAdvError1 | list[Stat | StatDate | StatInterval]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    body: list[RequestWithCampaignID | RequestWithDate | RequestWithInterval],
) -> (
    PostAdvV1StatsResponse401
    | PostAdvV1StatsResponse429
    | ResponseAdvError1
    | list[Stat | StatDate | StatInterval]
    | None
):
    r"""Media Campaign Statistics

     The method allows to get statistics of [WB Media](https://cmp.wildberries.ru/cmpf/statistics)
    campaigns

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 10 requests | 100 milliseconds | 10 requests |
    </div>

    Args:
        body (list[RequestWithCampaignID | RequestWithDate | RequestWithInterval]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostAdvV1StatsResponse401 | PostAdvV1StatsResponse429 | ResponseAdvError1 | list[Stat | StatDate | StatInterval]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: list[RequestWithCampaignID | RequestWithDate | RequestWithInterval],
) -> Response[
    PostAdvV1StatsResponse401
    | PostAdvV1StatsResponse429
    | ResponseAdvError1
    | list[Stat | StatDate | StatInterval]
]:
    r"""Media Campaign Statistics

     The method allows to get statistics of [WB Media](https://cmp.wildberries.ru/cmpf/statistics)
    campaigns

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 10 requests | 100 milliseconds | 10 requests |
    </div>

    Args:
        body (list[RequestWithCampaignID | RequestWithDate | RequestWithInterval]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostAdvV1StatsResponse401 | PostAdvV1StatsResponse429 | ResponseAdvError1 | list[Stat | StatDate | StatInterval]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: list[RequestWithCampaignID | RequestWithDate | RequestWithInterval],
) -> (
    PostAdvV1StatsResponse401
    | PostAdvV1StatsResponse429
    | ResponseAdvError1
    | list[Stat | StatDate | StatInterval]
    | None
):
    r"""Media Campaign Statistics

     The method allows to get statistics of [WB Media](https://cmp.wildberries.ru/cmpf/statistics)
    campaigns

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 10 requests | 100 milliseconds | 10 requests |
    </div>

    Args:
        body (list[RequestWithCampaignID | RequestWithDate | RequestWithInterval]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostAdvV1StatsResponse401 | PostAdvV1StatsResponse429 | ResponseAdvError1 | list[Stat | StatDate | StatInterval]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
