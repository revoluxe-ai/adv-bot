from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.v0_bids_recommendations_response import V0BidsRecommendationsResponse
from ...types import UNSET, Response


def _get_kwargs(
    *,
    nm_id: int,
    advert_id: int,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    params["nmId"] = nm_id

    params["advertId"] = advert_id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": "/api/advert/v0/bids/recommendations",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, V0BidsRecommendationsResponse, str]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = V0BidsRecommendationsResponse.from_dict(response.json())

        return response_200
    if response.status_code == HTTPStatus.BAD_REQUEST:
        response_400 = response.text
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
) -> Response[Union[Any, V0BidsRecommendationsResponse, str]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    nm_id: int,
    advert_id: int,
) -> Response[Union[Any, V0BidsRecommendationsResponse, str]]:
    r"""Recommended bids for items and search clusters

     The method returns recommended bids for items and search clusters of the campaign.
    Only for campaigns with cpm payment type — cost per mille.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 5 requests | 12 s | 5 requests |
    | Service | 1 min | 5 requests | 12 s | 5 requests |
    | Base | 1 h | 20 requests | 3 min | 1 request |
    </div>

    Args:
        nm_id (int):
        advert_id (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, V0BidsRecommendationsResponse, str]]
    """

    kwargs = _get_kwargs(
        nm_id=nm_id,
        advert_id=advert_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    nm_id: int,
    advert_id: int,
) -> Optional[Union[Any, V0BidsRecommendationsResponse, str]]:
    r"""Recommended bids for items and search clusters

     The method returns recommended bids for items and search clusters of the campaign.
    Only for campaigns with cpm payment type — cost per mille.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 5 requests | 12 s | 5 requests |
    | Service | 1 min | 5 requests | 12 s | 5 requests |
    | Base | 1 h | 20 requests | 3 min | 1 request |
    </div>

    Args:
        nm_id (int):
        advert_id (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, V0BidsRecommendationsResponse, str]
    """

    return sync_detailed(
        client=client,
        nm_id=nm_id,
        advert_id=advert_id,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    nm_id: int,
    advert_id: int,
) -> Response[Union[Any, V0BidsRecommendationsResponse, str]]:
    r"""Recommended bids for items and search clusters

     The method returns recommended bids for items and search clusters of the campaign.
    Only for campaigns with cpm payment type — cost per mille.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 5 requests | 12 s | 5 requests |
    | Service | 1 min | 5 requests | 12 s | 5 requests |
    | Base | 1 h | 20 requests | 3 min | 1 request |
    </div>

    Args:
        nm_id (int):
        advert_id (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, V0BidsRecommendationsResponse, str]]
    """

    kwargs = _get_kwargs(
        nm_id=nm_id,
        advert_id=advert_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    nm_id: int,
    advert_id: int,
) -> Optional[Union[Any, V0BidsRecommendationsResponse, str]]:
    r"""Recommended bids for items and search clusters

     The method returns recommended bids for items and search clusters of the campaign.
    Only for campaigns with cpm payment type — cost per mille.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 5 requests | 12 s | 5 requests |
    | Service | 1 min | 5 requests | 12 s | 5 requests |
    | Base | 1 h | 20 requests | 3 min | 1 request |
    </div>

    Args:
        nm_id (int):
        advert_id (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, V0BidsRecommendationsResponse, str]
    """

    return (
        await asyncio_detailed(
            client=client,
            nm_id=nm_id,
            advert_id=advert_id,
        )
    ).parsed
