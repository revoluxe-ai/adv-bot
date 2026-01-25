from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_adv_v1_search_set_excluded_body import (
    PostAdvV1SearchSetExcludedBody,
)
from ...models.post_adv_v1_search_set_excluded_response_401 import (
    PostAdvV1SearchSetExcludedResponse401,
)
from ...models.post_adv_v1_search_set_excluded_response_429 import (
    PostAdvV1SearchSetExcludedResponse429,
)
from ...types import UNSET, Response


def _get_kwargs(
    *,
    body: PostAdvV1SearchSetExcludedBody,
    id: int,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    params["id"] = id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/adv/v1/search/set-excluded",
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
    | PostAdvV1SearchSetExcludedResponse401
    | PostAdvV1SearchSetExcludedResponse429
    | str
    | None
):
    if response.status_code == 200:
        response_200 = cast(Any, None)
        return response_200

    if response.status_code == 400:
        response_400 = response.text
        return response_400

    if response.status_code == 401:
        response_401 = PostAdvV1SearchSetExcludedResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = PostAdvV1SearchSetExcludedResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    Any
    | PostAdvV1SearchSetExcludedResponse401
    | PostAdvV1SearchSetExcludedResponse429
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
    body: PostAdvV1SearchSetExcludedBody,
    id: int,
) -> Response[
    Any
    | PostAdvV1SearchSetExcludedResponse401
    | PostAdvV1SearchSetExcludedResponse429
    | str
]:
    """Ustanovka/udalenie minus-fraz v poiske

     Dannyj metod ustarel. On budet udalen [2 fevralja](https://dev.wildberries.ru/release-notes?id=388)

    Args:
        id (int):  Example: 1234567.
        body (PostAdvV1SearchSetExcludedBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | PostAdvV1SearchSetExcludedResponse401 | PostAdvV1SearchSetExcludedResponse429 | str]
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
    body: PostAdvV1SearchSetExcludedBody,
    id: int,
) -> (
    Any
    | PostAdvV1SearchSetExcludedResponse401
    | PostAdvV1SearchSetExcludedResponse429
    | str
    | None
):
    """Ustanovka/udalenie minus-fraz v poiske

     Dannyj metod ustarel. On budet udalen [2 fevralja](https://dev.wildberries.ru/release-notes?id=388)

    Args:
        id (int):  Example: 1234567.
        body (PostAdvV1SearchSetExcludedBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | PostAdvV1SearchSetExcludedResponse401 | PostAdvV1SearchSetExcludedResponse429 | str
    """

    return sync_detailed(
        client=client,
        body=body,
        id=id,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PostAdvV1SearchSetExcludedBody,
    id: int,
) -> Response[
    Any
    | PostAdvV1SearchSetExcludedResponse401
    | PostAdvV1SearchSetExcludedResponse429
    | str
]:
    """Ustanovka/udalenie minus-fraz v poiske

     Dannyj metod ustarel. On budet udalen [2 fevralja](https://dev.wildberries.ru/release-notes?id=388)

    Args:
        id (int):  Example: 1234567.
        body (PostAdvV1SearchSetExcludedBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | PostAdvV1SearchSetExcludedResponse401 | PostAdvV1SearchSetExcludedResponse429 | str]
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
    body: PostAdvV1SearchSetExcludedBody,
    id: int,
) -> (
    Any
    | PostAdvV1SearchSetExcludedResponse401
    | PostAdvV1SearchSetExcludedResponse429
    | str
    | None
):
    """Ustanovka/udalenie minus-fraz v poiske

     Dannyj metod ustarel. On budet udalen [2 fevralja](https://dev.wildberries.ru/release-notes?id=388)

    Args:
        id (int):  Example: 1234567.
        body (PostAdvV1SearchSetExcludedBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | PostAdvV1SearchSetExcludedResponse401 | PostAdvV1SearchSetExcludedResponse429 | str
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            id=id,
        )
    ).parsed
