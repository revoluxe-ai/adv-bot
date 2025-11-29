from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_adv_v1_auto_getnmtoadd_response_401 import (
    GetAdvV1AutoGetnmtoaddResponse401,
)
from ...models.get_adv_v1_auto_getnmtoadd_response_429 import (
    GetAdvV1AutoGetnmtoaddResponse429,
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
        "url": "/adv/v1/auto/getnmtoadd",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    GetAdvV1AutoGetnmtoaddResponse401
    | GetAdvV1AutoGetnmtoaddResponse429
    | ResponseAdvError1
    | list[int]
    | None
):
    if response.status_code == 200:
        response_200 = cast(list[int], response.json())

        return response_200

    if response.status_code == 400:
        response_400 = ResponseAdvError1.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = GetAdvV1AutoGetnmtoaddResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = GetAdvV1AutoGetnmtoaddResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    GetAdvV1AutoGetnmtoaddResponse401
    | GetAdvV1AutoGetnmtoaddResponse429
    | ResponseAdvError1
    | list[int]
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
    GetAdvV1AutoGetnmtoaddResponse401
    | GetAdvV1AutoGetnmtoaddResponse429
    | ResponseAdvError1
    | list[int]
]:
    r"""List of Product Cards for Campaign with Standard Bid

     The method allows to get the list of product cards available for adding to the campaign. <br>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 1 request | 1 second | 5 requests |
    </div>

    Args:
        id (int):  Example: 1.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetAdvV1AutoGetnmtoaddResponse401 | GetAdvV1AutoGetnmtoaddResponse429 | ResponseAdvError1 | list[int]]
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
    GetAdvV1AutoGetnmtoaddResponse401
    | GetAdvV1AutoGetnmtoaddResponse429
    | ResponseAdvError1
    | list[int]
    | None
):
    r"""List of Product Cards for Campaign with Standard Bid

     The method allows to get the list of product cards available for adding to the campaign. <br>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 1 request | 1 second | 5 requests |
    </div>

    Args:
        id (int):  Example: 1.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetAdvV1AutoGetnmtoaddResponse401 | GetAdvV1AutoGetnmtoaddResponse429 | ResponseAdvError1 | list[int]
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
    GetAdvV1AutoGetnmtoaddResponse401
    | GetAdvV1AutoGetnmtoaddResponse429
    | ResponseAdvError1
    | list[int]
]:
    r"""List of Product Cards for Campaign with Standard Bid

     The method allows to get the list of product cards available for adding to the campaign. <br>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 1 request | 1 second | 5 requests |
    </div>

    Args:
        id (int):  Example: 1.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetAdvV1AutoGetnmtoaddResponse401 | GetAdvV1AutoGetnmtoaddResponse429 | ResponseAdvError1 | list[int]]
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
    GetAdvV1AutoGetnmtoaddResponse401
    | GetAdvV1AutoGetnmtoaddResponse429
    | ResponseAdvError1
    | list[int]
    | None
):
    r"""List of Product Cards for Campaign with Standard Bid

     The method allows to get the list of product cards available for adding to the campaign. <br>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 1 request | 1 second | 5 requests |
    </div>

    Args:
        id (int):  Example: 1.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetAdvV1AutoGetnmtoaddResponse401 | GetAdvV1AutoGetnmtoaddResponse429 | ResponseAdvError1 | list[int]
    """

    return (
        await asyncio_detailed(
            client=client,
            id=id,
        )
    ).parsed
