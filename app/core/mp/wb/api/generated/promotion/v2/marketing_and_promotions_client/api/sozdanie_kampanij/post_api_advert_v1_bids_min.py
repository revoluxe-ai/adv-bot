from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_api_advert_v1_bids_min_body import PostApiAdvertV1BidsMinBody
from ...models.post_api_advert_v1_bids_min_response_200 import (
    PostApiAdvertV1BidsMinResponse200,
)
from ...models.post_api_advert_v1_bids_min_response_401 import (
    PostApiAdvertV1BidsMinResponse401,
)
from ...models.post_api_advert_v1_bids_min_response_429 import (
    PostApiAdvertV1BidsMinResponse429,
)
from ...models.standardized_batch_error import StandardizedBatchError
from ...types import Response


def _get_kwargs(
    *,
    body: PostApiAdvertV1BidsMinBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/advert/v1/bids/min",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    PostApiAdvertV1BidsMinResponse200
    | PostApiAdvertV1BidsMinResponse401
    | PostApiAdvertV1BidsMinResponse429
    | StandardizedBatchError
    | None
):
    if response.status_code == 200:
        response_200 = PostApiAdvertV1BidsMinResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = StandardizedBatchError.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostApiAdvertV1BidsMinResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = PostApiAdvertV1BidsMinResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    PostApiAdvertV1BidsMinResponse200
    | PostApiAdvertV1BidsMinResponse401
    | PostApiAdvertV1BidsMinResponse429
    | StandardizedBatchError
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
    body: PostApiAdvertV1BidsMinBody,
) -> Response[
    PostApiAdvertV1BidsMinResponse200
    | PostApiAdvertV1BidsMinResponse401
    | PostApiAdvertV1BidsMinResponse429
    | StandardizedBatchError
]:
    r"""Minimal'nye stavki dlja kartochek tovarov

     Metod vozvraschaet minimal'nye stavki dlja kartochek tovarov v kopejkah po tipu oplaty i mestam
    razmeschenija.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 20 zaprosov | 3 sekundy | 5 zaprosov |
    </div>

    Args:
        body (PostApiAdvertV1BidsMinBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostApiAdvertV1BidsMinResponse200 | PostApiAdvertV1BidsMinResponse401 | PostApiAdvertV1BidsMinResponse429 | StandardizedBatchError]
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
    body: PostApiAdvertV1BidsMinBody,
) -> (
    PostApiAdvertV1BidsMinResponse200
    | PostApiAdvertV1BidsMinResponse401
    | PostApiAdvertV1BidsMinResponse429
    | StandardizedBatchError
    | None
):
    r"""Minimal'nye stavki dlja kartochek tovarov

     Metod vozvraschaet minimal'nye stavki dlja kartochek tovarov v kopejkah po tipu oplaty i mestam
    razmeschenija.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 20 zaprosov | 3 sekundy | 5 zaprosov |
    </div>

    Args:
        body (PostApiAdvertV1BidsMinBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostApiAdvertV1BidsMinResponse200 | PostApiAdvertV1BidsMinResponse401 | PostApiAdvertV1BidsMinResponse429 | StandardizedBatchError
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: PostApiAdvertV1BidsMinBody,
) -> Response[
    PostApiAdvertV1BidsMinResponse200
    | PostApiAdvertV1BidsMinResponse401
    | PostApiAdvertV1BidsMinResponse429
    | StandardizedBatchError
]:
    r"""Minimal'nye stavki dlja kartochek tovarov

     Metod vozvraschaet minimal'nye stavki dlja kartochek tovarov v kopejkah po tipu oplaty i mestam
    razmeschenija.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 20 zaprosov | 3 sekundy | 5 zaprosov |
    </div>

    Args:
        body (PostApiAdvertV1BidsMinBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostApiAdvertV1BidsMinResponse200 | PostApiAdvertV1BidsMinResponse401 | PostApiAdvertV1BidsMinResponse429 | StandardizedBatchError]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: PostApiAdvertV1BidsMinBody,
) -> (
    PostApiAdvertV1BidsMinResponse200
    | PostApiAdvertV1BidsMinResponse401
    | PostApiAdvertV1BidsMinResponse429
    | StandardizedBatchError
    | None
):
    r"""Minimal'nye stavki dlja kartochek tovarov

     Metod vozvraschaet minimal'nye stavki dlja kartochek tovarov v kopejkah po tipu oplaty i mestam
    razmeschenija.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 20 zaprosov | 3 sekundy | 5 zaprosov |
    </div>

    Args:
        body (PostApiAdvertV1BidsMinBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostApiAdvertV1BidsMinResponse200 | PostApiAdvertV1BidsMinResponse401 | PostApiAdvertV1BidsMinResponse429 | StandardizedBatchError
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
