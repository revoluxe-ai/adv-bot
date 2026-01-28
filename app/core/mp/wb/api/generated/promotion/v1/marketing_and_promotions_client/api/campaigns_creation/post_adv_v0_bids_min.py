from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_adv_v0_bids_min_body import PostAdvV0BidsMinBody
from ...models.post_adv_v0_bids_min_response_200 import PostAdvV0BidsMinResponse200
from ...models.post_adv_v0_bids_min_response_401 import PostAdvV0BidsMinResponse401
from ...models.post_adv_v0_bids_min_response_429 import PostAdvV0BidsMinResponse429
from ...models.standardized_batch_error import StandardizedBatchError
from ...types import Response


def _get_kwargs(
    *,
    body: PostAdvV0BidsMinBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/adv/v0/bids/min",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    PostAdvV0BidsMinResponse200
    | PostAdvV0BidsMinResponse401
    | PostAdvV0BidsMinResponse429
    | StandardizedBatchError
    | None
):
    if response.status_code == 200:
        response_200 = PostAdvV0BidsMinResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = StandardizedBatchError.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostAdvV0BidsMinResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = PostAdvV0BidsMinResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    PostAdvV0BidsMinResponse200
    | PostAdvV0BidsMinResponse401
    | PostAdvV0BidsMinResponse429
    | StandardizedBatchError
]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: PostAdvV0BidsMinBody,
) -> Response[
    PostAdvV0BidsMinResponse200
    | PostAdvV0BidsMinResponse401
    | PostAdvV0BidsMinResponse429
    | StandardizedBatchError
]:
    r"""Minimum Bids for Product Cards

     Method allows minimum bids for product cards depending on the payment type and placements.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 minute | 20 requests | 3 seconds | 5 requests |
    </div>

    Args:
        body (PostAdvV0BidsMinBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostAdvV0BidsMinResponse200 | PostAdvV0BidsMinResponse401 | PostAdvV0BidsMinResponse429 | StandardizedBatchError]
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
    client: AuthenticatedClient | Client,
    body: PostAdvV0BidsMinBody,
) -> (
    PostAdvV0BidsMinResponse200
    | PostAdvV0BidsMinResponse401
    | PostAdvV0BidsMinResponse429
    | StandardizedBatchError
    | None
):
    r"""Minimum Bids for Product Cards

     Method allows minimum bids for product cards depending on the payment type and placements.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 minute | 20 requests | 3 seconds | 5 requests |
    </div>

    Args:
        body (PostAdvV0BidsMinBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostAdvV0BidsMinResponse200 | PostAdvV0BidsMinResponse401 | PostAdvV0BidsMinResponse429 | StandardizedBatchError
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: PostAdvV0BidsMinBody,
) -> Response[
    PostAdvV0BidsMinResponse200
    | PostAdvV0BidsMinResponse401
    | PostAdvV0BidsMinResponse429
    | StandardizedBatchError
]:
    r"""Minimum Bids for Product Cards

     Method allows minimum bids for product cards depending on the payment type and placements.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 minute | 20 requests | 3 seconds | 5 requests |
    </div>

    Args:
        body (PostAdvV0BidsMinBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostAdvV0BidsMinResponse200 | PostAdvV0BidsMinResponse401 | PostAdvV0BidsMinResponse429 | StandardizedBatchError]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: PostAdvV0BidsMinBody,
) -> (
    PostAdvV0BidsMinResponse200
    | PostAdvV0BidsMinResponse401
    | PostAdvV0BidsMinResponse429
    | StandardizedBatchError
    | None
):
    r"""Minimum Bids for Product Cards

     Method allows minimum bids for product cards depending on the payment type and placements.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 minute | 20 requests | 3 seconds | 5 requests |
    </div>

    Args:
        body (PostAdvV0BidsMinBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostAdvV0BidsMinResponse200 | PostAdvV0BidsMinResponse401 | PostAdvV0BidsMinResponse429 | StandardizedBatchError
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
