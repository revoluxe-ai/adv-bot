from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_adv_v1_auto_updatenm_body import PostAdvV1AutoUpdatenmBody
from ...models.post_adv_v1_auto_updatenm_response_401 import (
    PostAdvV1AutoUpdatenmResponse401,
)
from ...models.post_adv_v1_auto_updatenm_response_429 import (
    PostAdvV1AutoUpdatenmResponse429,
)
from ...models.response_adv_error_1 import ResponseAdvError1
from ...types import UNSET, Response


def _get_kwargs(
    *,
    body: PostAdvV1AutoUpdatenmBody,
    id: int,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    params["id"] = id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/adv/v1/auto/updatenm",
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
    | PostAdvV1AutoUpdatenmResponse401
    | PostAdvV1AutoUpdatenmResponse429
    | ResponseAdvError1
    | None
):
    if response.status_code == 200:
        response_200 = cast(Any, None)
        return response_200

    if response.status_code == 400:
        response_400 = ResponseAdvError1.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostAdvV1AutoUpdatenmResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = PostAdvV1AutoUpdatenmResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    Any
    | PostAdvV1AutoUpdatenmResponse401
    | PostAdvV1AutoUpdatenmResponse429
    | ResponseAdvError1
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
    body: PostAdvV1AutoUpdatenmBody,
    id: int,
) -> Response[
    Any
    | PostAdvV1AutoUpdatenmResponse401
    | PostAdvV1AutoUpdatenmResponse429
    | ResponseAdvError1
]:
    r"""Changing the List of Product Cards in a Campaign with Standard Bid

     The method allows you to add and remove product cards.

    <div class=\"description_important\">
      It is possible to add only those product cards that will be returned in the method response <a
    href=\"/openapi/promotion#tag/Campaign-Parameters/paths/~1adv~1v1~1auto~1getnmtoadd/get\">List of
    product cards in an campaign with standard bid</a>.<br>You cannot delete a one single product card
    from a campaign.
    </div>

    There is no validation by the `delete` parameter.

    If you receive a response with a status code of 200 and no change has occurred, check the request
    for documentation compliance

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 minute | 60 requests | 1 second | 5 requests |
    </div>

    Args:
        id (int):  Example: 1.
        body (PostAdvV1AutoUpdatenmBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | PostAdvV1AutoUpdatenmResponse401 | PostAdvV1AutoUpdatenmResponse429 | ResponseAdvError1]
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
    body: PostAdvV1AutoUpdatenmBody,
    id: int,
) -> (
    Any
    | PostAdvV1AutoUpdatenmResponse401
    | PostAdvV1AutoUpdatenmResponse429
    | ResponseAdvError1
    | None
):
    r"""Changing the List of Product Cards in a Campaign with Standard Bid

     The method allows you to add and remove product cards.

    <div class=\"description_important\">
      It is possible to add only those product cards that will be returned in the method response <a
    href=\"/openapi/promotion#tag/Campaign-Parameters/paths/~1adv~1v1~1auto~1getnmtoadd/get\">List of
    product cards in an campaign with standard bid</a>.<br>You cannot delete a one single product card
    from a campaign.
    </div>

    There is no validation by the `delete` parameter.

    If you receive a response with a status code of 200 and no change has occurred, check the request
    for documentation compliance

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 minute | 60 requests | 1 second | 5 requests |
    </div>

    Args:
        id (int):  Example: 1.
        body (PostAdvV1AutoUpdatenmBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | PostAdvV1AutoUpdatenmResponse401 | PostAdvV1AutoUpdatenmResponse429 | ResponseAdvError1
    """

    return sync_detailed(
        client=client,
        body=body,
        id=id,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PostAdvV1AutoUpdatenmBody,
    id: int,
) -> Response[
    Any
    | PostAdvV1AutoUpdatenmResponse401
    | PostAdvV1AutoUpdatenmResponse429
    | ResponseAdvError1
]:
    r"""Changing the List of Product Cards in a Campaign with Standard Bid

     The method allows you to add and remove product cards.

    <div class=\"description_important\">
      It is possible to add only those product cards that will be returned in the method response <a
    href=\"/openapi/promotion#tag/Campaign-Parameters/paths/~1adv~1v1~1auto~1getnmtoadd/get\">List of
    product cards in an campaign with standard bid</a>.<br>You cannot delete a one single product card
    from a campaign.
    </div>

    There is no validation by the `delete` parameter.

    If you receive a response with a status code of 200 and no change has occurred, check the request
    for documentation compliance

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 minute | 60 requests | 1 second | 5 requests |
    </div>

    Args:
        id (int):  Example: 1.
        body (PostAdvV1AutoUpdatenmBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | PostAdvV1AutoUpdatenmResponse401 | PostAdvV1AutoUpdatenmResponse429 | ResponseAdvError1]
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
    body: PostAdvV1AutoUpdatenmBody,
    id: int,
) -> (
    Any
    | PostAdvV1AutoUpdatenmResponse401
    | PostAdvV1AutoUpdatenmResponse429
    | ResponseAdvError1
    | None
):
    r"""Changing the List of Product Cards in a Campaign with Standard Bid

     The method allows you to add and remove product cards.

    <div class=\"description_important\">
      It is possible to add only those product cards that will be returned in the method response <a
    href=\"/openapi/promotion#tag/Campaign-Parameters/paths/~1adv~1v1~1auto~1getnmtoadd/get\">List of
    product cards in an campaign with standard bid</a>.<br>You cannot delete a one single product card
    from a campaign.
    </div>

    There is no validation by the `delete` parameter.

    If you receive a response with a status code of 200 and no change has occurred, check the request
    for documentation compliance

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 minute | 60 requests | 1 second | 5 requests |
    </div>

    Args:
        id (int):  Example: 1.
        body (PostAdvV1AutoUpdatenmBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | PostAdvV1AutoUpdatenmResponse401 | PostAdvV1AutoUpdatenmResponse429 | ResponseAdvError1
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            id=id,
        )
    ).parsed
