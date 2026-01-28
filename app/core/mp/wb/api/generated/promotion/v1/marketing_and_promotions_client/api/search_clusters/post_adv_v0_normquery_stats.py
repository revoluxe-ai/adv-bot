from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_adv_v0_normquery_stats_response_401 import (
    PostAdvV0NormqueryStatsResponse401,
)
from ...models.post_adv_v0_normquery_stats_response_429 import (
    PostAdvV0NormqueryStatsResponse429,
)
from ...models.response_400 import Response400
from ...models.standardized_batch_error import StandardizedBatchError
from ...models.v0_get_norm_query_stats_request import V0GetNormQueryStatsRequest
from ...models.v0_get_norm_query_stats_response import V0GetNormQueryStatsResponse
from ...types import Response


def _get_kwargs(
    *,
    body: V0GetNormQueryStatsRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/adv/v0/normquery/stats",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    PostAdvV0NormqueryStatsResponse401
    | PostAdvV0NormqueryStatsResponse429
    | Response400
    | StandardizedBatchError
    | V0GetNormQueryStatsResponse
    | None
):
    if response.status_code == 200:
        response_200 = V0GetNormQueryStatsResponse.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = Response400.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostAdvV0NormqueryStatsResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = StandardizedBatchError.from_dict(response.json())

        return response_403

    if response.status_code == 429:
        response_429 = PostAdvV0NormqueryStatsResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    PostAdvV0NormqueryStatsResponse401
    | PostAdvV0NormqueryStatsResponse429
    | Response400
    | StandardizedBatchError
    | V0GetNormQueryStatsResponse
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
    body: V0GetNormQueryStatsRequest,
) -> Response[
    PostAdvV0NormqueryStatsResponse401
    | PostAdvV0NormqueryStatsResponse429
    | Response400
    | StandardizedBatchError
    | V0GetNormQueryStatsResponse
]:
    r"""Search Clusters Statistics

     The method returns statistics for search clusters over a specified period.<br>
    You can use this method only for campaigns with a `cpm` payment model — for displays.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 minute | 10 requests | 6 seconds | 20 requests |
    </div>

    Args:
        body (V0GetNormQueryStatsRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostAdvV0NormqueryStatsResponse401 | PostAdvV0NormqueryStatsResponse429 | Response400 | StandardizedBatchError | V0GetNormQueryStatsResponse]
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
    body: V0GetNormQueryStatsRequest,
) -> (
    PostAdvV0NormqueryStatsResponse401
    | PostAdvV0NormqueryStatsResponse429
    | Response400
    | StandardizedBatchError
    | V0GetNormQueryStatsResponse
    | None
):
    r"""Search Clusters Statistics

     The method returns statistics for search clusters over a specified period.<br>
    You can use this method only for campaigns with a `cpm` payment model — for displays.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 minute | 10 requests | 6 seconds | 20 requests |
    </div>

    Args:
        body (V0GetNormQueryStatsRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostAdvV0NormqueryStatsResponse401 | PostAdvV0NormqueryStatsResponse429 | Response400 | StandardizedBatchError | V0GetNormQueryStatsResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: V0GetNormQueryStatsRequest,
) -> Response[
    PostAdvV0NormqueryStatsResponse401
    | PostAdvV0NormqueryStatsResponse429
    | Response400
    | StandardizedBatchError
    | V0GetNormQueryStatsResponse
]:
    r"""Search Clusters Statistics

     The method returns statistics for search clusters over a specified period.<br>
    You can use this method only for campaigns with a `cpm` payment model — for displays.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 minute | 10 requests | 6 seconds | 20 requests |
    </div>

    Args:
        body (V0GetNormQueryStatsRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostAdvV0NormqueryStatsResponse401 | PostAdvV0NormqueryStatsResponse429 | Response400 | StandardizedBatchError | V0GetNormQueryStatsResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: V0GetNormQueryStatsRequest,
) -> (
    PostAdvV0NormqueryStatsResponse401
    | PostAdvV0NormqueryStatsResponse429
    | Response400
    | StandardizedBatchError
    | V0GetNormQueryStatsResponse
    | None
):
    r"""Search Clusters Statistics

     The method returns statistics for search clusters over a specified period.<br>
    You can use this method only for campaigns with a `cpm` payment model — for displays.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 minute | 10 requests | 6 seconds | 20 requests |
    </div>

    Args:
        body (V0GetNormQueryStatsRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostAdvV0NormqueryStatsResponse401 | PostAdvV0NormqueryStatsResponse429 | Response400 | StandardizedBatchError | V0GetNormQueryStatsResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
