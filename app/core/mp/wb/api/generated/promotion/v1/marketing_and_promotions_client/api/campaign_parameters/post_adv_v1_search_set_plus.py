from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_adv_v1_search_set_plus_body import PostAdvV1SearchSetPlusBody
from ...models.post_adv_v1_search_set_plus_response_400 import (
    PostAdvV1SearchSetPlusResponse400,
)
from ...models.post_adv_v1_search_set_plus_response_401 import (
    PostAdvV1SearchSetPlusResponse401,
)
from ...models.post_adv_v1_search_set_plus_response_429 import (
    PostAdvV1SearchSetPlusResponse429,
)
from ...types import UNSET, Response


def _get_kwargs(
    *,
    body: PostAdvV1SearchSetPlusBody,
    id: int,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    params["id"] = id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/adv/v1/search/set-plus",
        "params": params,
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    PostAdvV1SearchSetPlusResponse400
    | PostAdvV1SearchSetPlusResponse401
    | PostAdvV1SearchSetPlusResponse429
    | list[str]
    | None
):
    if response.status_code == 200:
        response_200 = cast(list[str], response.json())

        return response_200

    if response.status_code == 400:
        response_400 = PostAdvV1SearchSetPlusResponse400.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostAdvV1SearchSetPlusResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = PostAdvV1SearchSetPlusResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    PostAdvV1SearchSetPlusResponse400
    | PostAdvV1SearchSetPlusResponse401
    | PostAdvV1SearchSetPlusResponse429
    | list[str]
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
    body: PostAdvV1SearchSetPlusBody,
    id: int,
) -> Response[
    PostAdvV1SearchSetPlusResponse400
    | PostAdvV1SearchSetPlusResponse401
    | PostAdvV1SearchSetPlusResponse429
    | list[str]
]:
    r"""Setting/Deleting Fixed Phrases

     The method allows to set and delete fixed phrases.Only for campaigns with custom bid.

    Sending an empty array removes all fixed phrases and disables fixed phrase activity in the campaign.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 500 milliseconds | 1 request | 500 milliseconds | 5 requests |
    </div>

    Args:
        id (int):  Example: 1234567.
        body (PostAdvV1SearchSetPlusBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostAdvV1SearchSetPlusResponse400 | PostAdvV1SearchSetPlusResponse401 | PostAdvV1SearchSetPlusResponse429 | list[str]]
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
    body: PostAdvV1SearchSetPlusBody,
    id: int,
) -> (
    PostAdvV1SearchSetPlusResponse400
    | PostAdvV1SearchSetPlusResponse401
    | PostAdvV1SearchSetPlusResponse429
    | list[str]
    | None
):
    r"""Setting/Deleting Fixed Phrases

     The method allows to set and delete fixed phrases.Only for campaigns with custom bid.

    Sending an empty array removes all fixed phrases and disables fixed phrase activity in the campaign.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 500 milliseconds | 1 request | 500 milliseconds | 5 requests |
    </div>

    Args:
        id (int):  Example: 1234567.
        body (PostAdvV1SearchSetPlusBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostAdvV1SearchSetPlusResponse400 | PostAdvV1SearchSetPlusResponse401 | PostAdvV1SearchSetPlusResponse429 | list[str]
    """

    return sync_detailed(
        client=client,
        body=body,
        id=id,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PostAdvV1SearchSetPlusBody,
    id: int,
) -> Response[
    PostAdvV1SearchSetPlusResponse400
    | PostAdvV1SearchSetPlusResponse401
    | PostAdvV1SearchSetPlusResponse429
    | list[str]
]:
    r"""Setting/Deleting Fixed Phrases

     The method allows to set and delete fixed phrases.Only for campaigns with custom bid.

    Sending an empty array removes all fixed phrases and disables fixed phrase activity in the campaign.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 500 milliseconds | 1 request | 500 milliseconds | 5 requests |
    </div>

    Args:
        id (int):  Example: 1234567.
        body (PostAdvV1SearchSetPlusBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostAdvV1SearchSetPlusResponse400 | PostAdvV1SearchSetPlusResponse401 | PostAdvV1SearchSetPlusResponse429 | list[str]]
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
    body: PostAdvV1SearchSetPlusBody,
    id: int,
) -> (
    PostAdvV1SearchSetPlusResponse400
    | PostAdvV1SearchSetPlusResponse401
    | PostAdvV1SearchSetPlusResponse429
    | list[str]
    | None
):
    r"""Setting/Deleting Fixed Phrases

     The method allows to set and delete fixed phrases.Only for campaigns with custom bid.

    Sending an empty array removes all fixed phrases and disables fixed phrase activity in the campaign.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 500 milliseconds | 1 request | 500 milliseconds | 5 requests |
    </div>

    Args:
        id (int):  Example: 1234567.
        body (PostAdvV1SearchSetPlusBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostAdvV1SearchSetPlusResponse400 | PostAdvV1SearchSetPlusResponse401 | PostAdvV1SearchSetPlusResponse429 | list[str]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            id=id,
        )
    ).parsed
