from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_adv_v2_auto_stat_words_response_200 import (
    GetAdvV2AutoStatWordsResponse200,
)
from ...models.get_adv_v2_auto_stat_words_response_401 import (
    GetAdvV2AutoStatWordsResponse401,
)
from ...models.get_adv_v2_auto_stat_words_response_429 import (
    GetAdvV2AutoStatWordsResponse429,
)
from ...models.response_adv_error_1 import ResponseAdvError1
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
        "url": "/adv/v2/auto/stat-words",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    Any
    | GetAdvV2AutoStatWordsResponse200
    | GetAdvV2AutoStatWordsResponse401
    | GetAdvV2AutoStatWordsResponse429
    | ResponseAdvError1
    | None
):
    if response.status_code == 200:
        response_200 = GetAdvV2AutoStatWordsResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 204:
        response_204 = cast(Any, None)
        return response_204

    if response.status_code == 400:
        response_400 = ResponseAdvError1.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = GetAdvV2AutoStatWordsResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = GetAdvV2AutoStatWordsResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    Any
    | GetAdvV2AutoStatWordsResponse200
    | GetAdvV2AutoStatWordsResponse401
    | GetAdvV2AutoStatWordsResponse429
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
    id: int,
) -> Response[
    Any
    | GetAdvV2AutoStatWordsResponse200
    | GetAdvV2AutoStatWordsResponse401
    | GetAdvV2AutoStatWordsResponse429
    | ResponseAdvError1
]:
    """Statistika kampanii s edinoj stavkoj po klasteram fraz

     Dannyj metod ustarel. On budet udalen [2 fevralja](https://dev.wildberries.ru/release-notes?id=429)

    Args:
        id (int):  Example: 1234.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | GetAdvV2AutoStatWordsResponse200 | GetAdvV2AutoStatWordsResponse401 | GetAdvV2AutoStatWordsResponse429 | ResponseAdvError1]
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
    | GetAdvV2AutoStatWordsResponse200
    | GetAdvV2AutoStatWordsResponse401
    | GetAdvV2AutoStatWordsResponse429
    | ResponseAdvError1
    | None
):
    """Statistika kampanii s edinoj stavkoj po klasteram fraz

     Dannyj metod ustarel. On budet udalen [2 fevralja](https://dev.wildberries.ru/release-notes?id=429)

    Args:
        id (int):  Example: 1234.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | GetAdvV2AutoStatWordsResponse200 | GetAdvV2AutoStatWordsResponse401 | GetAdvV2AutoStatWordsResponse429 | ResponseAdvError1
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
    | GetAdvV2AutoStatWordsResponse200
    | GetAdvV2AutoStatWordsResponse401
    | GetAdvV2AutoStatWordsResponse429
    | ResponseAdvError1
]:
    """Statistika kampanii s edinoj stavkoj po klasteram fraz

     Dannyj metod ustarel. On budet udalen [2 fevralja](https://dev.wildberries.ru/release-notes?id=429)

    Args:
        id (int):  Example: 1234.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | GetAdvV2AutoStatWordsResponse200 | GetAdvV2AutoStatWordsResponse401 | GetAdvV2AutoStatWordsResponse429 | ResponseAdvError1]
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
    | GetAdvV2AutoStatWordsResponse200
    | GetAdvV2AutoStatWordsResponse401
    | GetAdvV2AutoStatWordsResponse429
    | ResponseAdvError1
    | None
):
    """Statistika kampanii s edinoj stavkoj po klasteram fraz

     Dannyj metod ustarel. On budet udalen [2 fevralja](https://dev.wildberries.ru/release-notes?id=429)

    Args:
        id (int):  Example: 1234.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | GetAdvV2AutoStatWordsResponse200 | GetAdvV2AutoStatWordsResponse401 | GetAdvV2AutoStatWordsResponse429 | ResponseAdvError1
    """

    return (
        await asyncio_detailed(
            client=client,
            id=id,
        )
    ).parsed
