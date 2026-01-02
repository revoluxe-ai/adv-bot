from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.field_400_response import Field400Response
from ...models.post_adv_v1_auto_set_excluded_body import PostAdvV1AutoSetExcludedBody
from ...models.post_adv_v1_auto_set_excluded_response_401 import (
    PostAdvV1AutoSetExcludedResponse401,
)
from ...models.post_adv_v1_auto_set_excluded_response_429 import (
    PostAdvV1AutoSetExcludedResponse429,
)
from ...types import UNSET, Response


def _get_kwargs(
    *,
    body: PostAdvV1AutoSetExcludedBody,
    id: int,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    params["id"] = id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/adv/v1/auto/set-excluded",
        "params": params,
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    Any
    | Field400Response
    | PostAdvV1AutoSetExcludedResponse401
    | PostAdvV1AutoSetExcludedResponse429
    | None
):
    if response.status_code == 200:
        response_200 = cast(Any, None)
        return response_200

    if response.status_code == 400:
        response_400 = Field400Response.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostAdvV1AutoSetExcludedResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = PostAdvV1AutoSetExcludedResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    Any
    | Field400Response
    | PostAdvV1AutoSetExcludedResponse401
    | PostAdvV1AutoSetExcludedResponse429
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
    body: PostAdvV1AutoSetExcludedBody,
    id: int,
) -> Response[
    Any
    | Field400Response
    | PostAdvV1AutoSetExcludedResponse401
    | PostAdvV1AutoSetExcludedResponse429
]:
    r"""Setting/Removing Minus-phrases for Campaigns with Standard Bid

     The method allows to set or remove minus phrases for campaigns with [standard
    bid](/openapi/promotion#tag/Sozdanie-kampanij/paths/~1adv~1v2~1seacat~1save-ad/post).<br>
    To get the list of phrases used by buyers to find your product, use the [Statistics on
    keywords](/openapi/promotion#tag/Statistics/paths/~1adv~1v0~1stats~1keywords/get) method. <br>
    Sending an empty array removes all minus phrases from the campaign.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 6 seconds | 1 request | 6 seconds | 5 requests |
    </div>

    Args:
        id (int):  Example: 1234567.
        body (PostAdvV1AutoSetExcludedBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | Field400Response | PostAdvV1AutoSetExcludedResponse401 | PostAdvV1AutoSetExcludedResponse429]
    """

    kwargs = _get_kwargs(
        body=body,
        id=id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    body: PostAdvV1AutoSetExcludedBody,
    id: int,
) -> (
    Any
    | Field400Response
    | PostAdvV1AutoSetExcludedResponse401
    | PostAdvV1AutoSetExcludedResponse429
    | None
):
    r"""Setting/Removing Minus-phrases for Campaigns with Standard Bid

     The method allows to set or remove minus phrases for campaigns with [standard
    bid](/openapi/promotion#tag/Sozdanie-kampanij/paths/~1adv~1v2~1seacat~1save-ad/post).<br>
    To get the list of phrases used by buyers to find your product, use the [Statistics on
    keywords](/openapi/promotion#tag/Statistics/paths/~1adv~1v0~1stats~1keywords/get) method. <br>
    Sending an empty array removes all minus phrases from the campaign.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 6 seconds | 1 request | 6 seconds | 5 requests |
    </div>

    Args:
        id (int):  Example: 1234567.
        body (PostAdvV1AutoSetExcludedBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | Field400Response | PostAdvV1AutoSetExcludedResponse401 | PostAdvV1AutoSetExcludedResponse429
    """

    return sync_detailed(
        client=client,
        body=body,
        id=id,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PostAdvV1AutoSetExcludedBody,
    id: int,
) -> Response[
    Any
    | Field400Response
    | PostAdvV1AutoSetExcludedResponse401
    | PostAdvV1AutoSetExcludedResponse429
]:
    r"""Setting/Removing Minus-phrases for Campaigns with Standard Bid

     The method allows to set or remove minus phrases for campaigns with [standard
    bid](/openapi/promotion#tag/Sozdanie-kampanij/paths/~1adv~1v2~1seacat~1save-ad/post).<br>
    To get the list of phrases used by buyers to find your product, use the [Statistics on
    keywords](/openapi/promotion#tag/Statistics/paths/~1adv~1v0~1stats~1keywords/get) method. <br>
    Sending an empty array removes all minus phrases from the campaign.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 6 seconds | 1 request | 6 seconds | 5 requests |
    </div>

    Args:
        id (int):  Example: 1234567.
        body (PostAdvV1AutoSetExcludedBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | Field400Response | PostAdvV1AutoSetExcludedResponse401 | PostAdvV1AutoSetExcludedResponse429]
    """

    kwargs = _get_kwargs(
        body=body,
        id=id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: PostAdvV1AutoSetExcludedBody,
    id: int,
) -> (
    Any
    | Field400Response
    | PostAdvV1AutoSetExcludedResponse401
    | PostAdvV1AutoSetExcludedResponse429
    | None
):
    r"""Setting/Removing Minus-phrases for Campaigns with Standard Bid

     The method allows to set or remove minus phrases for campaigns with [standard
    bid](/openapi/promotion#tag/Sozdanie-kampanij/paths/~1adv~1v2~1seacat~1save-ad/post).<br>
    To get the list of phrases used by buyers to find your product, use the [Statistics on
    keywords](/openapi/promotion#tag/Statistics/paths/~1adv~1v0~1stats~1keywords/get) method. <br>
    Sending an empty array removes all minus phrases from the campaign.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 6 seconds | 1 request | 6 seconds | 5 requests |
    </div>

    Args:
        id (int):  Example: 1234567.
        body (PostAdvV1AutoSetExcludedBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | Field400Response | PostAdvV1AutoSetExcludedResponse401 | PostAdvV1AutoSetExcludedResponse429
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            id=id,
        )
    ).parsed
