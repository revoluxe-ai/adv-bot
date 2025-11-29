from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.patch_adv_v0_bids_body import PatchAdvV0BidsBody
from ...models.patch_adv_v0_bids_response_400 import PatchAdvV0BidsResponse400
from ...models.patch_adv_v0_bids_response_401 import PatchAdvV0BidsResponse401
from ...models.patch_adv_v0_bids_response_429 import PatchAdvV0BidsResponse429
from ...types import Response


def _get_kwargs(
    *,
    body: PatchAdvV0BidsBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/adv/v0/bids",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    Any
    | PatchAdvV0BidsResponse400
    | PatchAdvV0BidsResponse401
    | PatchAdvV0BidsResponse429
    | None
):
    if response.status_code == 204:
        response_204 = cast(Any, None)
        return response_204

    if response.status_code == 400:
        response_400 = PatchAdvV0BidsResponse400.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PatchAdvV0BidsResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = PatchAdvV0BidsResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    Any
    | PatchAdvV0BidsResponse400
    | PatchAdvV0BidsResponse401
    | PatchAdvV0BidsResponse429
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
    body: PatchAdvV0BidsBody,
) -> Response[
    Any
    | PatchAdvV0BidsResponse400
    | PatchAdvV0BidsResponse401
    | PatchAdvV0BidsResponse429
]:
    r"""Changing Bids

     The method changes the bids of product cards by WB articles in campaigns with standard bid.
    <br><br>
    For campaigns in statuses `4`, `9` and `11`.
    <br><br>
    Use [the separate method](/openapi/promotion#tag/Campaigns-
    Management/paths/~1adv~1v0~1auction~1bids/patch) to change bids in the campaigns with custom bid.
    <br><br>
    Minimum allowable bids can be found in the response of the method for getting [minimum bids for
    product cards](/openapi/promotion#tag/Campaigns-Creation/paths/~1adv~1v0~1bids~1min/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 5 requests | 200 milliseconds | 5 requests |
    </div>

    Args:
        body (PatchAdvV0BidsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | PatchAdvV0BidsResponse400 | PatchAdvV0BidsResponse401 | PatchAdvV0BidsResponse429]
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
    body: PatchAdvV0BidsBody,
) -> (
    Any
    | PatchAdvV0BidsResponse400
    | PatchAdvV0BidsResponse401
    | PatchAdvV0BidsResponse429
    | None
):
    r"""Changing Bids

     The method changes the bids of product cards by WB articles in campaigns with standard bid.
    <br><br>
    For campaigns in statuses `4`, `9` and `11`.
    <br><br>
    Use [the separate method](/openapi/promotion#tag/Campaigns-
    Management/paths/~1adv~1v0~1auction~1bids/patch) to change bids in the campaigns with custom bid.
    <br><br>
    Minimum allowable bids can be found in the response of the method for getting [minimum bids for
    product cards](/openapi/promotion#tag/Campaigns-Creation/paths/~1adv~1v0~1bids~1min/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 5 requests | 200 milliseconds | 5 requests |
    </div>

    Args:
        body (PatchAdvV0BidsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | PatchAdvV0BidsResponse400 | PatchAdvV0BidsResponse401 | PatchAdvV0BidsResponse429
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: PatchAdvV0BidsBody,
) -> Response[
    Any
    | PatchAdvV0BidsResponse400
    | PatchAdvV0BidsResponse401
    | PatchAdvV0BidsResponse429
]:
    r"""Changing Bids

     The method changes the bids of product cards by WB articles in campaigns with standard bid.
    <br><br>
    For campaigns in statuses `4`, `9` and `11`.
    <br><br>
    Use [the separate method](/openapi/promotion#tag/Campaigns-
    Management/paths/~1adv~1v0~1auction~1bids/patch) to change bids in the campaigns with custom bid.
    <br><br>
    Minimum allowable bids can be found in the response of the method for getting [minimum bids for
    product cards](/openapi/promotion#tag/Campaigns-Creation/paths/~1adv~1v0~1bids~1min/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 5 requests | 200 milliseconds | 5 requests |
    </div>

    Args:
        body (PatchAdvV0BidsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | PatchAdvV0BidsResponse400 | PatchAdvV0BidsResponse401 | PatchAdvV0BidsResponse429]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: PatchAdvV0BidsBody,
) -> (
    Any
    | PatchAdvV0BidsResponse400
    | PatchAdvV0BidsResponse401
    | PatchAdvV0BidsResponse429
    | None
):
    r"""Changing Bids

     The method changes the bids of product cards by WB articles in campaigns with standard bid.
    <br><br>
    For campaigns in statuses `4`, `9` and `11`.
    <br><br>
    Use [the separate method](/openapi/promotion#tag/Campaigns-
    Management/paths/~1adv~1v0~1auction~1bids/patch) to change bids in the campaigns with custom bid.
    <br><br>
    Minimum allowable bids can be found in the response of the method for getting [minimum bids for
    product cards](/openapi/promotion#tag/Campaigns-Creation/paths/~1adv~1v0~1bids~1min/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 5 requests | 200 milliseconds | 5 requests |
    </div>

    Args:
        body (PatchAdvV0BidsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | PatchAdvV0BidsResponse400 | PatchAdvV0BidsResponse401 | PatchAdvV0BidsResponse429
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
