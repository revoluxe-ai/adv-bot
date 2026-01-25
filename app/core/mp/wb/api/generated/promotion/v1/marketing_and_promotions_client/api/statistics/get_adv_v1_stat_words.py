from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_adv_v1_stat_words_response_200 import GetAdvV1StatWordsResponse200
from ...models.get_adv_v1_stat_words_response_401 import GetAdvV1StatWordsResponse401
from ...models.get_adv_v1_stat_words_response_429 import GetAdvV1StatWordsResponse429
from ...types import UNSET, Response


def _get_kwargs(
    *,
    id: int,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["id"] = id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/adv/v1/stat/words",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    Any
    | GetAdvV1StatWordsResponse200
    | GetAdvV1StatWordsResponse401
    | GetAdvV1StatWordsResponse429
    | None
):
    if response.status_code == 200:
        response_200 = GetAdvV1StatWordsResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = cast(Any, None)
        return response_400

    if response.status_code == 401:
        response_401 = GetAdvV1StatWordsResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = GetAdvV1StatWordsResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    Any
    | GetAdvV1StatWordsResponse200
    | GetAdvV1StatWordsResponse401
    | GetAdvV1StatWordsResponse429
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
    id: int,
) -> Response[
    Any
    | GetAdvV1StatWordsResponse200
    | GetAdvV1StatWordsResponse401
    | GetAdvV1StatWordsResponse429
]:
    r"""Statistics on Keywords for Campaign with Custom Bid

     The method allows to get statistics on keywords for campaign with custom bid.<br>
    The information updates approximately every half hour.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 4 requests | 250 milliseconds | 4 requests |
    </div>

    Args:
        id (int):  Example: 1.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | GetAdvV1StatWordsResponse200 | GetAdvV1StatWordsResponse401 | GetAdvV1StatWordsResponse429]
    """

    kwargs = _get_kwargs(
        id=id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    id: int,
) -> (
    Any
    | GetAdvV1StatWordsResponse200
    | GetAdvV1StatWordsResponse401
    | GetAdvV1StatWordsResponse429
    | None
):
    r"""Statistics on Keywords for Campaign with Custom Bid

     The method allows to get statistics on keywords for campaign with custom bid.<br>
    The information updates approximately every half hour.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 4 requests | 250 milliseconds | 4 requests |
    </div>

    Args:
        id (int):  Example: 1.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | GetAdvV1StatWordsResponse200 | GetAdvV1StatWordsResponse401 | GetAdvV1StatWordsResponse429
    """

    return sync_detailed(
        client=client,
        id=id,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    id: int,
) -> Response[
    Any
    | GetAdvV1StatWordsResponse200
    | GetAdvV1StatWordsResponse401
    | GetAdvV1StatWordsResponse429
]:
    r"""Statistics on Keywords for Campaign with Custom Bid

     The method allows to get statistics on keywords for campaign with custom bid.<br>
    The information updates approximately every half hour.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 4 requests | 250 milliseconds | 4 requests |
    </div>

    Args:
        id (int):  Example: 1.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | GetAdvV1StatWordsResponse200 | GetAdvV1StatWordsResponse401 | GetAdvV1StatWordsResponse429]
    """

    kwargs = _get_kwargs(
        id=id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    id: int,
) -> (
    Any
    | GetAdvV1StatWordsResponse200
    | GetAdvV1StatWordsResponse401
    | GetAdvV1StatWordsResponse429
    | None
):
    r"""Statistics on Keywords for Campaign with Custom Bid

     The method allows to get statistics on keywords for campaign with custom bid.<br>
    The information updates approximately every half hour.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 4 requests | 250 milliseconds | 4 requests |
    </div>

    Args:
        id (int):  Example: 1.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | GetAdvV1StatWordsResponse200 | GetAdvV1StatWordsResponse401 | GetAdvV1StatWordsResponse429
    """

    return (
        await asyncio_detailed(
            client=client,
            id=id,
        )
    ).parsed
