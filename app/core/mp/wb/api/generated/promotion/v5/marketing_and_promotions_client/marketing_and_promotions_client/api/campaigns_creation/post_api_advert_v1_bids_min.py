from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_api_advert_v1_bids_min_body import PostApiAdvertV1BidsMinBody
from ...models.post_api_advert_v1_bids_min_response_200 import (
    PostApiAdvertV1BidsMinResponse200,
)
from ...models.standardized_batch_error import StandardizedBatchError
from ...types import Response


def _get_kwargs(
    *,
    body: PostApiAdvertV1BidsMinBody,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": "/api/advert/v1/bids/min",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, PostApiAdvertV1BidsMinResponse200, StandardizedBatchError]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = PostApiAdvertV1BidsMinResponse200.from_dict(response.json())

        return response_200
    if response.status_code == HTTPStatus.BAD_REQUEST:
        response_400 = StandardizedBatchError.from_dict(response.json())

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
) -> Response[Union[Any, PostApiAdvertV1BidsMinResponse200, StandardizedBatchError]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: PostApiAdvertV1BidsMinBody,
) -> Response[Union[Any, PostApiAdvertV1BidsMinResponse200, StandardizedBatchError]]:
    r"""Minimum Bids for Product Cards

     Method allows minimum bids for product cards in kopecks depending on the payment type and
    placements.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 20 requests | 3 s | 5 requests |
    | Service | 1 min | 20 requests | 3 s | 5 requests |
    | Base | 1 h | 5 requests | 12 min | 1 request |
    </div>

    Args:
        body (PostApiAdvertV1BidsMinBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, PostApiAdvertV1BidsMinResponse200, StandardizedBatchError]]
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
    client: Union[AuthenticatedClient, Client],
    body: PostApiAdvertV1BidsMinBody,
) -> Optional[Union[Any, PostApiAdvertV1BidsMinResponse200, StandardizedBatchError]]:
    r"""Minimum Bids for Product Cards

     Method allows minimum bids for product cards in kopecks depending on the payment type and
    placements.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 20 requests | 3 s | 5 requests |
    | Service | 1 min | 20 requests | 3 s | 5 requests |
    | Base | 1 h | 5 requests | 12 min | 1 request |
    </div>

    Args:
        body (PostApiAdvertV1BidsMinBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, PostApiAdvertV1BidsMinResponse200, StandardizedBatchError]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: PostApiAdvertV1BidsMinBody,
) -> Response[Union[Any, PostApiAdvertV1BidsMinResponse200, StandardizedBatchError]]:
    r"""Minimum Bids for Product Cards

     Method allows minimum bids for product cards in kopecks depending on the payment type and
    placements.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 20 requests | 3 s | 5 requests |
    | Service | 1 min | 20 requests | 3 s | 5 requests |
    | Base | 1 h | 5 requests | 12 min | 1 request |
    </div>

    Args:
        body (PostApiAdvertV1BidsMinBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, PostApiAdvertV1BidsMinResponse200, StandardizedBatchError]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: PostApiAdvertV1BidsMinBody,
) -> Optional[Union[Any, PostApiAdvertV1BidsMinResponse200, StandardizedBatchError]]:
    r"""Minimum Bids for Product Cards

     Method allows minimum bids for product cards in kopecks depending on the payment type and
    placements.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 20 requests | 3 s | 5 requests |
    | Service | 1 min | 20 requests | 3 s | 5 requests |
    | Base | 1 h | 5 requests | 12 min | 1 request |
    </div>

    Args:
        body (PostApiAdvertV1BidsMinBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, PostApiAdvertV1BidsMinResponse200, StandardizedBatchError]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
