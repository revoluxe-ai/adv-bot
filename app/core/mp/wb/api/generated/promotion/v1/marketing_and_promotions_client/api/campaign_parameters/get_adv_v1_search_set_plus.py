from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_adv_v1_search_set_plus_response_401 import (
    GetAdvV1SearchSetPlusResponse401,
)
from ...models.get_adv_v1_search_set_plus_response_429 import (
    GetAdvV1SearchSetPlusResponse429,
)
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    id: int,
    fixed: bool | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["id"] = id

    params["fixed"] = fixed

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/adv/v1/search/set-plus",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    Any
    | GetAdvV1SearchSetPlusResponse401
    | GetAdvV1SearchSetPlusResponse429
    | str
    | None
):
    if response.status_code == 200:
        response_200 = cast(Any, None)
        return response_200

    if response.status_code == 400:
        response_400 = cast(str, response.json())
        return response_400

    if response.status_code == 401:
        response_401 = GetAdvV1SearchSetPlusResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = GetAdvV1SearchSetPlusResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    Any | GetAdvV1SearchSetPlusResponse401 | GetAdvV1SearchSetPlusResponse429 | str
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
    fixed: bool | Unset = UNSET,
) -> Response[
    Any | GetAdvV1SearchSetPlusResponse401 | GetAdvV1SearchSetPlusResponse429 | str
]:
    r"""Managing the Activity of Fixed Phrases

     The method allows to change the activity of fixed phrases. Only for campaigns with custom bid.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 500 milliseconds | 1 request | 500 milliseconds | 5 requests |
    </div>

    Args:
        id (int):  Example: 1234567.
        fixed (bool | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | GetAdvV1SearchSetPlusResponse401 | GetAdvV1SearchSetPlusResponse429 | str]
    """

    kwargs = _get_kwargs(
        id=id,
        fixed=fixed,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    id: int,
    fixed: bool | Unset = UNSET,
) -> (
    Any
    | GetAdvV1SearchSetPlusResponse401
    | GetAdvV1SearchSetPlusResponse429
    | str
    | None
):
    r"""Managing the Activity of Fixed Phrases

     The method allows to change the activity of fixed phrases. Only for campaigns with custom bid.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 500 milliseconds | 1 request | 500 milliseconds | 5 requests |
    </div>

    Args:
        id (int):  Example: 1234567.
        fixed (bool | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | GetAdvV1SearchSetPlusResponse401 | GetAdvV1SearchSetPlusResponse429 | str
    """

    return sync_detailed(
        client=client,
        id=id,
        fixed=fixed,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    id: int,
    fixed: bool | Unset = UNSET,
) -> Response[
    Any | GetAdvV1SearchSetPlusResponse401 | GetAdvV1SearchSetPlusResponse429 | str
]:
    r"""Managing the Activity of Fixed Phrases

     The method allows to change the activity of fixed phrases. Only for campaigns with custom bid.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 500 milliseconds | 1 request | 500 milliseconds | 5 requests |
    </div>

    Args:
        id (int):  Example: 1234567.
        fixed (bool | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | GetAdvV1SearchSetPlusResponse401 | GetAdvV1SearchSetPlusResponse429 | str]
    """

    kwargs = _get_kwargs(
        id=id,
        fixed=fixed,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    id: int,
    fixed: bool | Unset = UNSET,
) -> (
    Any
    | GetAdvV1SearchSetPlusResponse401
    | GetAdvV1SearchSetPlusResponse429
    | str
    | None
):
    r"""Managing the Activity of Fixed Phrases

     The method allows to change the activity of fixed phrases. Only for campaigns with custom bid.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 500 milliseconds | 1 request | 500 milliseconds | 5 requests |
    </div>

    Args:
        id (int):  Example: 1234567.
        fixed (bool | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | GetAdvV1SearchSetPlusResponse401 | GetAdvV1SearchSetPlusResponse429 | str
    """

    return (
        await asyncio_detailed(
            client=client,
            id=id,
            fixed=fixed,
        )
    ).parsed
