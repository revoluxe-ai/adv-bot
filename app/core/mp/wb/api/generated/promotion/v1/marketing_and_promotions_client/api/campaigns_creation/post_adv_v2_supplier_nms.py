from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_adv_v2_supplier_nms_response_200_item import (
    PostAdvV2SupplierNmsResponse200Item,
)
from ...models.post_adv_v2_supplier_nms_response_401 import (
    PostAdvV2SupplierNmsResponse401,
)
from ...models.post_adv_v2_supplier_nms_response_429 import (
    PostAdvV2SupplierNmsResponse429,
)
from ...types import Response


def _get_kwargs(
    *,
    body: list[int],
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/adv/v2/supplier/nms",
    }

    _kwargs["json"] = body

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    PostAdvV2SupplierNmsResponse401
    | PostAdvV2SupplierNmsResponse429
    | list[PostAdvV2SupplierNmsResponse200Item]
    | str
    | None
):
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = PostAdvV2SupplierNmsResponse200Item.from_dict(
                response_200_item_data
            )

            response_200.append(response_200_item)

        return response_200

    if response.status_code == 400:
        response_400 = response.text
        return response_400

    if response.status_code == 401:
        response_401 = PostAdvV2SupplierNmsResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = PostAdvV2SupplierNmsResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    PostAdvV2SupplierNmsResponse401
    | PostAdvV2SupplierNmsResponse429
    | list[PostAdvV2SupplierNmsResponse200Item]
    | str
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
    body: list[int],
) -> Response[
    PostAdvV2SupplierNmsResponse401
    | PostAdvV2SupplierNmsResponse429
    | list[PostAdvV2SupplierNmsResponse200Item]
    | str
]:
    r"""Product Cards for Campaigns

     Returns product cards that are available for all campaigns.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 minute | 5 requests | 12 seconds | 5 requests |
    </div>

    Args:
        body (list[int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostAdvV2SupplierNmsResponse401 | PostAdvV2SupplierNmsResponse429 | list[PostAdvV2SupplierNmsResponse200Item] | str]
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
    body: list[int],
) -> (
    PostAdvV2SupplierNmsResponse401
    | PostAdvV2SupplierNmsResponse429
    | list[PostAdvV2SupplierNmsResponse200Item]
    | str
    | None
):
    r"""Product Cards for Campaigns

     Returns product cards that are available for all campaigns.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 minute | 5 requests | 12 seconds | 5 requests |
    </div>

    Args:
        body (list[int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostAdvV2SupplierNmsResponse401 | PostAdvV2SupplierNmsResponse429 | list[PostAdvV2SupplierNmsResponse200Item] | str
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: list[int],
) -> Response[
    PostAdvV2SupplierNmsResponse401
    | PostAdvV2SupplierNmsResponse429
    | list[PostAdvV2SupplierNmsResponse200Item]
    | str
]:
    r"""Product Cards for Campaigns

     Returns product cards that are available for all campaigns.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 minute | 5 requests | 12 seconds | 5 requests |
    </div>

    Args:
        body (list[int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostAdvV2SupplierNmsResponse401 | PostAdvV2SupplierNmsResponse429 | list[PostAdvV2SupplierNmsResponse200Item] | str]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: list[int],
) -> (
    PostAdvV2SupplierNmsResponse401
    | PostAdvV2SupplierNmsResponse429
    | list[PostAdvV2SupplierNmsResponse200Item]
    | str
    | None
):
    r"""Product Cards for Campaigns

     Returns product cards that are available for all campaigns.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 minute | 5 requests | 12 seconds | 5 requests |
    </div>

    Args:
        body (list[int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostAdvV2SupplierNmsResponse401 | PostAdvV2SupplierNmsResponse429 | list[PostAdvV2SupplierNmsResponse200Item] | str
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
