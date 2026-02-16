from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.patch_api_advert_v1_bids_body import PatchApiAdvertV1BidsBody
from ...models.patch_api_advert_v1_bids_response_200 import (
    PatchApiAdvertV1BidsResponse200,
)
from ...models.response_400 import Response400
from ...types import Response


def _get_kwargs(
    *,
    body: PatchApiAdvertV1BidsBody,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "patch",
        "url": "/api/advert/v1/bids",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, PatchApiAdvertV1BidsResponse200, Response400]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = PatchApiAdvertV1BidsResponse200.from_dict(response.json())

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
) -> Response[Union[Any, PatchApiAdvertV1BidsResponse200, Response400]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: PatchApiAdvertV1BidsBody,
) -> Response[Union[Any, PatchApiAdvertV1BidsResponse200, Response400]]:
    r"""Changing Campaigns Bids

     The method changes the bids of product cards by WB articles in campaigns with standard bid or custom
    bid.
    <br><br>
    For campaigns in statuses `4`, `9` and `11`.
    <br><br>
    Specify the placement in the request parameter `placement`:
      - `combined` —  in search and recommendations for campaigns with standard bid
      - `search `or `recommendations` — in search or recommendations for campaigns with custom bid

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 s | 5 requests | 200 ms | 5 requests |
    </div>

    Args:
        body (PatchApiAdvertV1BidsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, PatchApiAdvertV1BidsResponse200, Response400]]
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
    body: PatchApiAdvertV1BidsBody,
) -> Optional[Union[Any, PatchApiAdvertV1BidsResponse200, Response400]]:
    r"""Changing Campaigns Bids

     The method changes the bids of product cards by WB articles in campaigns with standard bid or custom
    bid.
    <br><br>
    For campaigns in statuses `4`, `9` and `11`.
    <br><br>
    Specify the placement in the request parameter `placement`:
      - `combined` —  in search and recommendations for campaigns with standard bid
      - `search `or `recommendations` — in search or recommendations for campaigns with custom bid

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 s | 5 requests | 200 ms | 5 requests |
    </div>

    Args:
        body (PatchApiAdvertV1BidsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, PatchApiAdvertV1BidsResponse200, Response400]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PatchApiAdvertV1BidsBody,
) -> Response[Union[Any, PatchApiAdvertV1BidsResponse200, Response400]]:
    r"""Changing Campaigns Bids

     The method changes the bids of product cards by WB articles in campaigns with standard bid or custom
    bid.
    <br><br>
    For campaigns in statuses `4`, `9` and `11`.
    <br><br>
    Specify the placement in the request parameter `placement`:
      - `combined` —  in search and recommendations for campaigns with standard bid
      - `search `or `recommendations` — in search or recommendations for campaigns with custom bid

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 s | 5 requests | 200 ms | 5 requests |
    </div>

    Args:
        body (PatchApiAdvertV1BidsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, PatchApiAdvertV1BidsResponse200, Response400]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: PatchApiAdvertV1BidsBody,
) -> Optional[Union[Any, PatchApiAdvertV1BidsResponse200, Response400]]:
    r"""Changing Campaigns Bids

     The method changes the bids of product cards by WB articles in campaigns with standard bid or custom
    bid.
    <br><br>
    For campaigns in statuses `4`, `9` and `11`.
    <br><br>
    Specify the placement in the request parameter `placement`:
      - `combined` —  in search and recommendations for campaigns with standard bid
      - `search `or `recommendations` — in search or recommendations for campaigns with custom bid

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 s | 5 requests | 200 ms | 5 requests |
    </div>

    Args:
        body (PatchApiAdvertV1BidsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, PatchApiAdvertV1BidsResponse200, Response400]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
