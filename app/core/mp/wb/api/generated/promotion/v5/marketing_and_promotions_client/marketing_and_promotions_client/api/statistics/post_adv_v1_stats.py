from http import HTTPStatus
from typing import Any, Dict, List, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
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
    body: List[
        Union["RequestWithCampaignID", "RequestWithDate", "RequestWithInterval"]
    ],
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": "/adv/v1/stats",
    }

    _body = []
    for body_item_data in body:
        body_item: Dict[str, Any]
        if isinstance(body_item_data, RequestWithDate):
            body_item = body_item_data.to_dict()
        elif isinstance(body_item_data, RequestWithInterval):
            body_item = body_item_data.to_dict()
        else:
            body_item = body_item_data.to_dict()

        _body.append(body_item)

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[Any, List[Union["Stat", "StatDate", "StatInterval"]], ResponseAdvError1]
]:
    if response.status_code == HTTPStatus.OK:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:

            def _parse_response_200_item(
                data: object,
            ) -> Union["Stat", "StatDate", "StatInterval"]:
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    response_200_item_type_0 = StatInterval.from_dict(data)

                    return response_200_item_type_0
                except:  # noqa: E722
                    pass
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    response_200_item_type_1 = StatDate.from_dict(data)

                    return response_200_item_type_1
                except:  # noqa: E722
                    pass
                if not isinstance(data, dict):
                    raise TypeError()
                response_200_item_type_2 = Stat.from_dict(data)

                return response_200_item_type_2

            response_200_item = _parse_response_200_item(response_200_item_data)

            response_200.append(response_200_item)

        return response_200
    if response.status_code == HTTPStatus.BAD_REQUEST:
        response_400 = ResponseAdvError1.from_dict(response.json())

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
) -> Response[
    Union[Any, List[Union["Stat", "StatDate", "StatInterval"]], ResponseAdvError1]
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
    body: List[
        Union["RequestWithCampaignID", "RequestWithDate", "RequestWithInterval"]
    ],
) -> Response[
    Union[Any, List[Union["Stat", "StatDate", "StatInterval"]], ResponseAdvError1]
]:
    r"""Media Campaign Statistics

     The method allows to get statistics of [WB Media](https://cmp.wildberries.ru/cmpf/statistics)
    campaigns

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 s | 10 requests | 100 ms | 10 requests |
    | Service | 1 s | 10 requests | 100 ms | 10 requests |
    | Base | 1 h | 1 request | 1 h | 1 request |
    </div>

    Args:
        body (List[Union['RequestWithCampaignID', 'RequestWithDate', 'RequestWithInterval']]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, List[Union['Stat', 'StatDate', 'StatInterval']], ResponseAdvError1]]
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
    body: List[
        Union["RequestWithCampaignID", "RequestWithDate", "RequestWithInterval"]
    ],
) -> Optional[
    Union[Any, List[Union["Stat", "StatDate", "StatInterval"]], ResponseAdvError1]
]:
    r"""Media Campaign Statistics

     The method allows to get statistics of [WB Media](https://cmp.wildberries.ru/cmpf/statistics)
    campaigns

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 s | 10 requests | 100 ms | 10 requests |
    | Service | 1 s | 10 requests | 100 ms | 10 requests |
    | Base | 1 h | 1 request | 1 h | 1 request |
    </div>

    Args:
        body (List[Union['RequestWithCampaignID', 'RequestWithDate', 'RequestWithInterval']]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, List[Union['Stat', 'StatDate', 'StatInterval']], ResponseAdvError1]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: List[
        Union["RequestWithCampaignID", "RequestWithDate", "RequestWithInterval"]
    ],
) -> Response[
    Union[Any, List[Union["Stat", "StatDate", "StatInterval"]], ResponseAdvError1]
]:
    r"""Media Campaign Statistics

     The method allows to get statistics of [WB Media](https://cmp.wildberries.ru/cmpf/statistics)
    campaigns

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 s | 10 requests | 100 ms | 10 requests |
    | Service | 1 s | 10 requests | 100 ms | 10 requests |
    | Base | 1 h | 1 request | 1 h | 1 request |
    </div>

    Args:
        body (List[Union['RequestWithCampaignID', 'RequestWithDate', 'RequestWithInterval']]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, List[Union['Stat', 'StatDate', 'StatInterval']], ResponseAdvError1]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: List[
        Union["RequestWithCampaignID", "RequestWithDate", "RequestWithInterval"]
    ],
) -> Optional[
    Union[Any, List[Union["Stat", "StatDate", "StatInterval"]], ResponseAdvError1]
]:
    r"""Media Campaign Statistics

     The method allows to get statistics of [WB Media](https://cmp.wildberries.ru/cmpf/statistics)
    campaigns

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 s | 10 requests | 100 ms | 10 requests |
    | Service | 1 s | 10 requests | 100 ms | 10 requests |
    | Base | 1 h | 1 request | 1 h | 1 request |
    </div>

    Args:
        body (List[Union['RequestWithCampaignID', 'RequestWithDate', 'RequestWithInterval']]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, List[Union['Stat', 'StatDate', 'StatInterval']], ResponseAdvError1]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
