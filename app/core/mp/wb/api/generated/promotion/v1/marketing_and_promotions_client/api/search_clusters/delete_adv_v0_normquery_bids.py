from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.delete_adv_v0_normquery_bids_response_401 import (
    DeleteAdvV0NormqueryBidsResponse401,
)
from ...models.delete_adv_v0_normquery_bids_response_429 import (
    DeleteAdvV0NormqueryBidsResponse429,
)
from ...models.response_400 import Response400
from ...models.standardized_batch_error import StandardizedBatchError
from ...models.v0_set_norm_query_bids_request import V0SetNormQueryBidsRequest
from ...types import Response


def _get_kwargs(
    *,
    body: V0SetNormQueryBidsRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": "/adv/v0/normquery/bids",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    Any
    | DeleteAdvV0NormqueryBidsResponse401
    | DeleteAdvV0NormqueryBidsResponse429
    | Response400
    | StandardizedBatchError
    | None
):
    if response.status_code == 200:
        response_200 = cast(Any, None)
        return response_200

    if response.status_code == 400:
        response_400 = Response400.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = DeleteAdvV0NormqueryBidsResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = StandardizedBatchError.from_dict(response.json())

        return response_403

    if response.status_code == 429:
        response_429 = DeleteAdvV0NormqueryBidsResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    Any
    | DeleteAdvV0NormqueryBidsResponse401
    | DeleteAdvV0NormqueryBidsResponse429
    | Response400
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
    body: V0SetNormQueryBidsRequest,
) -> Response[
    Any
    | DeleteAdvV0NormqueryBidsResponse401
    | DeleteAdvV0NormqueryBidsResponse429
    | Response400
    | StandardizedBatchError
]:
    r"""Delete Bids from Search Clusters

     The method deletes the bids from search clusters.<br>
    You can use this method only for campaigns with:
      - custom bid
      - a `cpm` payment model — per displays


    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 5 requests | 200 milliseconds | 10 requests |
    </div>

    Args:
        body (V0SetNormQueryBidsRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | DeleteAdvV0NormqueryBidsResponse401 | DeleteAdvV0NormqueryBidsResponse429 | Response400 | StandardizedBatchError]
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
    body: V0SetNormQueryBidsRequest,
) -> (
    Any
    | DeleteAdvV0NormqueryBidsResponse401
    | DeleteAdvV0NormqueryBidsResponse429
    | Response400
    | StandardizedBatchError
    | None
):
    r"""Delete Bids from Search Clusters

     The method deletes the bids from search clusters.<br>
    You can use this method only for campaigns with:
      - custom bid
      - a `cpm` payment model — per displays


    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 5 requests | 200 milliseconds | 10 requests |
    </div>

    Args:
        body (V0SetNormQueryBidsRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | DeleteAdvV0NormqueryBidsResponse401 | DeleteAdvV0NormqueryBidsResponse429 | Response400 | StandardizedBatchError
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: V0SetNormQueryBidsRequest,
) -> Response[
    Any
    | DeleteAdvV0NormqueryBidsResponse401
    | DeleteAdvV0NormqueryBidsResponse429
    | Response400
    | StandardizedBatchError
]:
    r"""Delete Bids from Search Clusters

     The method deletes the bids from search clusters.<br>
    You can use this method only for campaigns with:
      - custom bid
      - a `cpm` payment model — per displays


    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 5 requests | 200 milliseconds | 10 requests |
    </div>

    Args:
        body (V0SetNormQueryBidsRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | DeleteAdvV0NormqueryBidsResponse401 | DeleteAdvV0NormqueryBidsResponse429 | Response400 | StandardizedBatchError]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: V0SetNormQueryBidsRequest,
) -> (
    Any
    | DeleteAdvV0NormqueryBidsResponse401
    | DeleteAdvV0NormqueryBidsResponse429
    | Response400
    | StandardizedBatchError
    | None
):
    r"""Delete Bids from Search Clusters

     The method deletes the bids from search clusters.<br>
    You can use this method only for campaigns with:
      - custom bid
      - a `cpm` payment model — per displays


    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 5 requests | 200 milliseconds | 10 requests |
    </div>

    Args:
        body (V0SetNormQueryBidsRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | DeleteAdvV0NormqueryBidsResponse401 | DeleteAdvV0NormqueryBidsResponse429 | Response400 | StandardizedBatchError
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
