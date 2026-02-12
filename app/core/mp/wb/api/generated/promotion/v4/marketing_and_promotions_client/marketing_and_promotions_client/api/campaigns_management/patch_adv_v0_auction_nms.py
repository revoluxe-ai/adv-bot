from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.patch_adv_v0_auction_nms_body import PatchAdvV0AuctionNmsBody
from ...models.patch_adv_v0_auction_nms_response_200 import (
    PatchAdvV0AuctionNmsResponse200,
)
from ...models.response_400 import Response400
from ...types import Response


def _get_kwargs(
    *,
    body: PatchAdvV0AuctionNmsBody,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "patch",
        "url": "/adv/v0/auction/nms",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, PatchAdvV0AuctionNmsResponse200, Response400]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = PatchAdvV0AuctionNmsResponse200.from_dict(response.json())

        return response_200
    if response.status_code == HTTPStatus.BAD_REQUEST:
        response_400 = Response400.from_dict(response.json())

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
) -> Response[Union[Any, PatchAdvV0AuctionNmsResponse200, Response400]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: PatchAdvV0AuctionNmsBody,
) -> Response[Union[Any, PatchAdvV0AuctionNmsResponse200, Response400]]:
    r"""Changing the List of Product Cards in Campaigns

     The method allows you to add and remove product cards in campaigns.
    <br><br>
    For campaigns in statuses `4`, `9` and `11`.
    <br><br>
    The current minimum bid is set for the added products.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 s | 1 request | 1 s | 1 request |
    </div>

    Args:
        body (PatchAdvV0AuctionNmsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, PatchAdvV0AuctionNmsResponse200, Response400]]
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
    body: PatchAdvV0AuctionNmsBody,
) -> Optional[Union[Any, PatchAdvV0AuctionNmsResponse200, Response400]]:
    r"""Changing the List of Product Cards in Campaigns

     The method allows you to add and remove product cards in campaigns.
    <br><br>
    For campaigns in statuses `4`, `9` and `11`.
    <br><br>
    The current minimum bid is set for the added products.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 s | 1 request | 1 s | 1 request |
    </div>

    Args:
        body (PatchAdvV0AuctionNmsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, PatchAdvV0AuctionNmsResponse200, Response400]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PatchAdvV0AuctionNmsBody,
) -> Response[Union[Any, PatchAdvV0AuctionNmsResponse200, Response400]]:
    r"""Changing the List of Product Cards in Campaigns

     The method allows you to add and remove product cards in campaigns.
    <br><br>
    For campaigns in statuses `4`, `9` and `11`.
    <br><br>
    The current minimum bid is set for the added products.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 s | 1 request | 1 s | 1 request |
    </div>

    Args:
        body (PatchAdvV0AuctionNmsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, PatchAdvV0AuctionNmsResponse200, Response400]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: PatchAdvV0AuctionNmsBody,
) -> Optional[Union[Any, PatchAdvV0AuctionNmsResponse200, Response400]]:
    r"""Changing the List of Product Cards in Campaigns

     The method allows you to add and remove product cards in campaigns.
    <br><br>
    For campaigns in statuses `4`, `9` and `11`.
    <br><br>
    The current minimum bid is set for the added products.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 s | 1 request | 1 s | 1 request |
    </div>

    Args:
        body (PatchAdvV0AuctionNmsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, PatchAdvV0AuctionNmsResponse200, Response400]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
