from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.post_api_v3_stocks_warehouse_id_body import (
    PostApiV3StocksWarehouseIdBody,
)
from ...models.post_api_v3_stocks_warehouse_id_response_200 import (
    PostApiV3StocksWarehouseIdResponse200,
)
from ...models.post_api_v3_stocks_warehouse_id_response_401 import (
    PostApiV3StocksWarehouseIdResponse401,
)
from ...models.post_api_v3_stocks_warehouse_id_response_429 import (
    PostApiV3StocksWarehouseIdResponse429,
)
from ...types import Response


def _get_kwargs(
    warehouse_id: int,
    *,
    body: PostApiV3StocksWarehouseIdBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v3/stocks/{warehouse_id}".format(
            warehouse_id=warehouse_id,
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    Error
    | PostApiV3StocksWarehouseIdResponse200
    | PostApiV3StocksWarehouseIdResponse401
    | PostApiV3StocksWarehouseIdResponse429
    | None
):
    if response.status_code == 200:
        response_200 = PostApiV3StocksWarehouseIdResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = Error.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostApiV3StocksWarehouseIdResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = Error.from_dict(response.json())

        return response_403

    if response.status_code == 404:
        response_404 = Error.from_dict(response.json())

        return response_404

    if response.status_code == 429:
        response_429 = PostApiV3StocksWarehouseIdResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    Error
    | PostApiV3StocksWarehouseIdResponse200
    | PostApiV3StocksWarehouseIdResponse401
    | PostApiV3StocksWarehouseIdResponse429
]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    warehouse_id: int,
    *,
    client: AuthenticatedClient,
    body: PostApiV3StocksWarehouseIdBody,
) -> Response[
    Error
    | PostApiV3StocksWarehouseIdResponse200
    | PostApiV3StocksWarehouseIdResponse401
    | PostApiV3StocksWarehouseIdResponse429
]:
    r"""Poluchit' ostatki tovarov

     Metod vozvraschaet dannye ob ostatkah tovarov na [skladah prodavtsa](/openapi/work-with-
    products#tag/Sklady-prodavca).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov <strong>ostatkov na skladah prodavtsa</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 300 zaprosov | 200 ms | 20 zaprosov |

    Odin zapros s kodom otveta <code>409</code> uchityvaetsja kak 10 zaprosov
    </div>

    Args:
        warehouse_id (int):  Example: 1.
        body (PostApiV3StocksWarehouseIdBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | PostApiV3StocksWarehouseIdResponse200 | PostApiV3StocksWarehouseIdResponse401 | PostApiV3StocksWarehouseIdResponse429]
    """

    kwargs = _get_kwargs(
        warehouse_id=warehouse_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    warehouse_id: int,
    *,
    client: AuthenticatedClient,
    body: PostApiV3StocksWarehouseIdBody,
) -> (
    Error
    | PostApiV3StocksWarehouseIdResponse200
    | PostApiV3StocksWarehouseIdResponse401
    | PostApiV3StocksWarehouseIdResponse429
    | None
):
    r"""Poluchit' ostatki tovarov

     Metod vozvraschaet dannye ob ostatkah tovarov na [skladah prodavtsa](/openapi/work-with-
    products#tag/Sklady-prodavca).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov <strong>ostatkov na skladah prodavtsa</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 300 zaprosov | 200 ms | 20 zaprosov |

    Odin zapros s kodom otveta <code>409</code> uchityvaetsja kak 10 zaprosov
    </div>

    Args:
        warehouse_id (int):  Example: 1.
        body (PostApiV3StocksWarehouseIdBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | PostApiV3StocksWarehouseIdResponse200 | PostApiV3StocksWarehouseIdResponse401 | PostApiV3StocksWarehouseIdResponse429
    """

    return sync_detailed(
        warehouse_id=warehouse_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    warehouse_id: int,
    *,
    client: AuthenticatedClient,
    body: PostApiV3StocksWarehouseIdBody,
) -> Response[
    Error
    | PostApiV3StocksWarehouseIdResponse200
    | PostApiV3StocksWarehouseIdResponse401
    | PostApiV3StocksWarehouseIdResponse429
]:
    r"""Poluchit' ostatki tovarov

     Metod vozvraschaet dannye ob ostatkah tovarov na [skladah prodavtsa](/openapi/work-with-
    products#tag/Sklady-prodavca).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov <strong>ostatkov na skladah prodavtsa</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 300 zaprosov | 200 ms | 20 zaprosov |

    Odin zapros s kodom otveta <code>409</code> uchityvaetsja kak 10 zaprosov
    </div>

    Args:
        warehouse_id (int):  Example: 1.
        body (PostApiV3StocksWarehouseIdBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | PostApiV3StocksWarehouseIdResponse200 | PostApiV3StocksWarehouseIdResponse401 | PostApiV3StocksWarehouseIdResponse429]
    """

    kwargs = _get_kwargs(
        warehouse_id=warehouse_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    warehouse_id: int,
    *,
    client: AuthenticatedClient,
    body: PostApiV3StocksWarehouseIdBody,
) -> (
    Error
    | PostApiV3StocksWarehouseIdResponse200
    | PostApiV3StocksWarehouseIdResponse401
    | PostApiV3StocksWarehouseIdResponse429
    | None
):
    r"""Poluchit' ostatki tovarov

     Metod vozvraschaet dannye ob ostatkah tovarov na [skladah prodavtsa](/openapi/work-with-
    products#tag/Sklady-prodavca).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov <strong>ostatkov na skladah prodavtsa</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 300 zaprosov | 200 ms | 20 zaprosov |

    Odin zapros s kodom otveta <code>409</code> uchityvaetsja kak 10 zaprosov
    </div>

    Args:
        warehouse_id (int):  Example: 1.
        body (PostApiV3StocksWarehouseIdBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | PostApiV3StocksWarehouseIdResponse200 | PostApiV3StocksWarehouseIdResponse401 | PostApiV3StocksWarehouseIdResponse429
    """

    return (
        await asyncio_detailed(
            warehouse_id=warehouse_id,
            client=client,
            body=body,
        )
    ).parsed
