from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_adv_v1_balance_response_200 import GetAdvV1BalanceResponse200
from ...models.get_adv_v1_balance_response_401 import GetAdvV1BalanceResponse401
from ...models.get_adv_v1_balance_response_429 import GetAdvV1BalanceResponse429
from ...types import Response


def _get_kwargs() -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/adv/v1/balance",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    GetAdvV1BalanceResponse200
    | GetAdvV1BalanceResponse401
    | GetAdvV1BalanceResponse429
    | str
    | None
):
    if response.status_code == 200:
        response_200 = GetAdvV1BalanceResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = cast(str, response.json())
        return response_400

    if response.status_code == 401:
        response_401 = GetAdvV1BalanceResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = GetAdvV1BalanceResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    GetAdvV1BalanceResponse200
    | GetAdvV1BalanceResponse401
    | GetAdvV1BalanceResponse429
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
) -> Response[
    GetAdvV1BalanceResponse200
    | GetAdvV1BalanceResponse401
    | GetAdvV1BalanceResponse429
    | str
]:
    r"""Balance

     The method allows to get information about the seller's net, balance and bonuses<br>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 1 request | 1 second | 5 requests |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetAdvV1BalanceResponse200 | GetAdvV1BalanceResponse401 | GetAdvV1BalanceResponse429 | str]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
) -> (
    GetAdvV1BalanceResponse200
    | GetAdvV1BalanceResponse401
    | GetAdvV1BalanceResponse429
    | str
    | None
):
    r"""Balance

     The method allows to get information about the seller's net, balance and bonuses<br>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 1 request | 1 second | 5 requests |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetAdvV1BalanceResponse200 | GetAdvV1BalanceResponse401 | GetAdvV1BalanceResponse429 | str
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
) -> Response[
    GetAdvV1BalanceResponse200
    | GetAdvV1BalanceResponse401
    | GetAdvV1BalanceResponse429
    | str
]:
    r"""Balance

     The method allows to get information about the seller's net, balance and bonuses<br>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 1 request | 1 second | 5 requests |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetAdvV1BalanceResponse200 | GetAdvV1BalanceResponse401 | GetAdvV1BalanceResponse429 | str]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
) -> (
    GetAdvV1BalanceResponse200
    | GetAdvV1BalanceResponse401
    | GetAdvV1BalanceResponse429
    | str
    | None
):
    r"""Balance

     The method allows to get information about the seller's net, balance and bonuses<br>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 1 request | 1 second | 5 requests |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetAdvV1BalanceResponse200 | GetAdvV1BalanceResponse401 | GetAdvV1BalanceResponse429 | str
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
