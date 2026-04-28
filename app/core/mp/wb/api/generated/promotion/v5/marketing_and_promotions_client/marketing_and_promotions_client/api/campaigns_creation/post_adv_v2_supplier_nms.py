from http import HTTPStatus
from typing import Any, Dict, List, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_adv_v2_supplier_nms_response_200_item import (
    PostAdvV2SupplierNmsResponse200Item,
)
from ...types import Response


def _get_kwargs(
    *,
    body: List[int],
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": "/adv/v2/supplier/nms",
    }

    _body = body

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, List["PostAdvV2SupplierNmsResponse200Item"], str]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = PostAdvV2SupplierNmsResponse200Item.from_dict(
                response_200_item_data
            )

            response_200.append(response_200_item)

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
) -> Response[Union[Any, List["PostAdvV2SupplierNmsResponse200Item"], str]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: List[int],
) -> Response[Union[Any, List["PostAdvV2SupplierNmsResponse200Item"], str]]:
    r"""Product Cards for Campaigns

     Returns product cards that are available for all campaigns.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 5 requests | 12 s | 5 requests |
    | Service | 1 min | 5 requests | 12 s | 5 requests |
    | Base | 1 h | 2 requests | 30 min | 1 request |
    </div>

    Args:
        body (List[int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, List['PostAdvV2SupplierNmsResponse200Item'], str]]
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
    body: List[int],
) -> Optional[Union[Any, List["PostAdvV2SupplierNmsResponse200Item"], str]]:
    r"""Product Cards for Campaigns

     Returns product cards that are available for all campaigns.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 5 requests | 12 s | 5 requests |
    | Service | 1 min | 5 requests | 12 s | 5 requests |
    | Base | 1 h | 2 requests | 30 min | 1 request |
    </div>

    Args:
        body (List[int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, List['PostAdvV2SupplierNmsResponse200Item'], str]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: List[int],
) -> Response[Union[Any, List["PostAdvV2SupplierNmsResponse200Item"], str]]:
    r"""Product Cards for Campaigns

     Returns product cards that are available for all campaigns.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 5 requests | 12 s | 5 requests |
    | Service | 1 min | 5 requests | 12 s | 5 requests |
    | Base | 1 h | 2 requests | 30 min | 1 request |
    </div>

    Args:
        body (List[int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, List['PostAdvV2SupplierNmsResponse200Item'], str]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: List[int],
) -> Optional[Union[Any, List["PostAdvV2SupplierNmsResponse200Item"], str]]:
    r"""Product Cards for Campaigns

     Returns product cards that are available for all campaigns.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 5 requests | 12 s | 5 requests |
    | Service | 1 min | 5 requests | 12 s | 5 requests |
    | Base | 1 h | 2 requests | 30 min | 1 request |
    </div>

    Args:
        body (List[int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, List['PostAdvV2SupplierNmsResponse200Item'], str]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
