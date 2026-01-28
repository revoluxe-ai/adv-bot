from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_adv_v2_seacat_save_ad_body import PostAdvV2SeacatSaveAdBody
from ...models.post_adv_v2_seacat_save_ad_response_401 import (
    PostAdvV2SeacatSaveAdResponse401,
)
from ...models.post_adv_v2_seacat_save_ad_response_429 import (
    PostAdvV2SeacatSaveAdResponse429,
)
from ...types import Response


def _get_kwargs(
    *,
    body: PostAdvV2SeacatSaveAdBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/adv/v2/seacat/save-ad",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    PostAdvV2SeacatSaveAdResponse401
    | PostAdvV2SeacatSaveAdResponse429
    | int
    | str
    | None
):
    if response.status_code == 200:
        response_200 = cast(int, response.json())
        return response_200

    if response.status_code == 400:
        response_400 = cast(str, response.json())
        return response_400

    if response.status_code == 401:
        response_401 = PostAdvV2SeacatSaveAdResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = PostAdvV2SeacatSaveAdResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    PostAdvV2SeacatSaveAdResponse401 | PostAdvV2SeacatSaveAdResponse429 | int | str
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
    body: PostAdvV2SeacatSaveAdBody,
) -> Response[
    PostAdvV2SeacatSaveAdResponse401 | PostAdvV2SeacatSaveAdResponse429 | int | str
]:
    r"""Create Campaign

     The method creates campaign:
      - with custom bid for promotion products in search and/or recommendations
      - with standard bid for promotion products both in search and recommendations

    The type of all campaigns created via this method is `9`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 minute | 5 requests | 12 seconds | 5 requests |
    </div>

    Args:
        body (PostAdvV2SeacatSaveAdBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostAdvV2SeacatSaveAdResponse401 | PostAdvV2SeacatSaveAdResponse429 | int | str]
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
    body: PostAdvV2SeacatSaveAdBody,
) -> (
    PostAdvV2SeacatSaveAdResponse401
    | PostAdvV2SeacatSaveAdResponse429
    | int
    | str
    | None
):
    r"""Create Campaign

     The method creates campaign:
      - with custom bid for promotion products in search and/or recommendations
      - with standard bid for promotion products both in search and recommendations

    The type of all campaigns created via this method is `9`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 minute | 5 requests | 12 seconds | 5 requests |
    </div>

    Args:
        body (PostAdvV2SeacatSaveAdBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostAdvV2SeacatSaveAdResponse401 | PostAdvV2SeacatSaveAdResponse429 | int | str
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PostAdvV2SeacatSaveAdBody,
) -> Response[
    PostAdvV2SeacatSaveAdResponse401 | PostAdvV2SeacatSaveAdResponse429 | int | str
]:
    r"""Create Campaign

     The method creates campaign:
      - with custom bid for promotion products in search and/or recommendations
      - with standard bid for promotion products both in search and recommendations

    The type of all campaigns created via this method is `9`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 minute | 5 requests | 12 seconds | 5 requests |
    </div>

    Args:
        body (PostAdvV2SeacatSaveAdBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostAdvV2SeacatSaveAdResponse401 | PostAdvV2SeacatSaveAdResponse429 | int | str]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: PostAdvV2SeacatSaveAdBody,
) -> (
    PostAdvV2SeacatSaveAdResponse401
    | PostAdvV2SeacatSaveAdResponse429
    | int
    | str
    | None
):
    r"""Create Campaign

     The method creates campaign:
      - with custom bid for promotion products in search and/or recommendations
      - with standard bid for promotion products both in search and recommendations

    The type of all campaigns created via this method is `9`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 minute | 5 requests | 12 seconds | 5 requests |
    </div>

    Args:
        body (PostAdvV2SeacatSaveAdBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostAdvV2SeacatSaveAdResponse401 | PostAdvV2SeacatSaveAdResponse429 | int | str
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
