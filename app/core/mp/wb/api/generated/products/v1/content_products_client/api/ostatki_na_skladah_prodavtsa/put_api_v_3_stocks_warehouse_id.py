from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.put_api_v3_stocks_warehouse_id_body import PutApiV3StocksWarehouseIdBody
from ...models.put_api_v3_stocks_warehouse_id_response_401 import (
    PutApiV3StocksWarehouseIdResponse401,
)
from ...models.put_api_v3_stocks_warehouse_id_response_406 import (
    PutApiV3StocksWarehouseIdResponse406,
)
from ...models.put_api_v3_stocks_warehouse_id_response_429 import (
    PutApiV3StocksWarehouseIdResponse429,
)
from ...models.stocks_warehouse_error_item import StocksWarehouseErrorItem
from ...types import Response


def _get_kwargs(
    warehouse_id: int,
    *,
    body: PutApiV3StocksWarehouseIdBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "put",
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
    Any
    | Error
    | PutApiV3StocksWarehouseIdResponse401
    | PutApiV3StocksWarehouseIdResponse406
    | PutApiV3StocksWarehouseIdResponse429
    | list[StocksWarehouseErrorItem]
    | None
):
    if response.status_code == 204:
        response_204 = cast(Any, None)
        return response_204

    if response.status_code == 400:
        response_400 = Error.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PutApiV3StocksWarehouseIdResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = Error.from_dict(response.json())

        return response_403

    if response.status_code == 404:
        response_404 = Error.from_dict(response.json())

        return response_404

    if response.status_code == 406:
        response_406 = PutApiV3StocksWarehouseIdResponse406.from_dict(response.json())

        return response_406

    if response.status_code == 409:
        response_409 = []
        _response_409 = response.json()
        for componentsschemas_stocks_warehouse_error_item_data in _response_409:
            componentsschemas_stocks_warehouse_error_item = (
                StocksWarehouseErrorItem.from_dict(
                    componentsschemas_stocks_warehouse_error_item_data
                )
            )

            response_409.append(componentsschemas_stocks_warehouse_error_item)

        return response_409

    if response.status_code == 429:
        response_429 = PutApiV3StocksWarehouseIdResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    Any
    | Error
    | PutApiV3StocksWarehouseIdResponse401
    | PutApiV3StocksWarehouseIdResponse406
    | PutApiV3StocksWarehouseIdResponse429
    | list[StocksWarehouseErrorItem]
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
    body: PutApiV3StocksWarehouseIdBody,
) -> Response[
    Any
    | Error
    | PutApiV3StocksWarehouseIdResponse401
    | PutApiV3StocksWarehouseIdResponse406
    | PutApiV3StocksWarehouseIdResponse429
    | list[StocksWarehouseErrorItem]
]:
    r"""Obnovit' ostatki tovarov

     Metod obnovljaet kolichestvo ostatkov tovarov prodavtsa [v spiske](/openapi/work-with-
    products#tag/Ostatki-na-skladah-prodavca/paths/~1api~1v3~1stocks~1%7BwarehouseId%7D/post).

    <div class=\"description_important\">
      Nazvanija parametrov zaprosa ne validirujutsja. Pri otpravke nekorrektnyh nazvanij vy poluchite
    uspeshnyj otvet (<code>204</code>), no ostatki ne obnovjatsja.
    </div>

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
        body (PutApiV3StocksWarehouseIdBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | Error | PutApiV3StocksWarehouseIdResponse401 | PutApiV3StocksWarehouseIdResponse406 | PutApiV3StocksWarehouseIdResponse429 | list[StocksWarehouseErrorItem]]
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
    body: PutApiV3StocksWarehouseIdBody,
) -> (
    Any
    | Error
    | PutApiV3StocksWarehouseIdResponse401
    | PutApiV3StocksWarehouseIdResponse406
    | PutApiV3StocksWarehouseIdResponse429
    | list[StocksWarehouseErrorItem]
    | None
):
    r"""Obnovit' ostatki tovarov

     Metod obnovljaet kolichestvo ostatkov tovarov prodavtsa [v spiske](/openapi/work-with-
    products#tag/Ostatki-na-skladah-prodavca/paths/~1api~1v3~1stocks~1%7BwarehouseId%7D/post).

    <div class=\"description_important\">
      Nazvanija parametrov zaprosa ne validirujutsja. Pri otpravke nekorrektnyh nazvanij vy poluchite
    uspeshnyj otvet (<code>204</code>), no ostatki ne obnovjatsja.
    </div>

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
        body (PutApiV3StocksWarehouseIdBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | Error | PutApiV3StocksWarehouseIdResponse401 | PutApiV3StocksWarehouseIdResponse406 | PutApiV3StocksWarehouseIdResponse429 | list[StocksWarehouseErrorItem]
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
    body: PutApiV3StocksWarehouseIdBody,
) -> Response[
    Any
    | Error
    | PutApiV3StocksWarehouseIdResponse401
    | PutApiV3StocksWarehouseIdResponse406
    | PutApiV3StocksWarehouseIdResponse429
    | list[StocksWarehouseErrorItem]
]:
    r"""Obnovit' ostatki tovarov

     Metod obnovljaet kolichestvo ostatkov tovarov prodavtsa [v spiske](/openapi/work-with-
    products#tag/Ostatki-na-skladah-prodavca/paths/~1api~1v3~1stocks~1%7BwarehouseId%7D/post).

    <div class=\"description_important\">
      Nazvanija parametrov zaprosa ne validirujutsja. Pri otpravke nekorrektnyh nazvanij vy poluchite
    uspeshnyj otvet (<code>204</code>), no ostatki ne obnovjatsja.
    </div>

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
        body (PutApiV3StocksWarehouseIdBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | Error | PutApiV3StocksWarehouseIdResponse401 | PutApiV3StocksWarehouseIdResponse406 | PutApiV3StocksWarehouseIdResponse429 | list[StocksWarehouseErrorItem]]
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
    body: PutApiV3StocksWarehouseIdBody,
) -> (
    Any
    | Error
    | PutApiV3StocksWarehouseIdResponse401
    | PutApiV3StocksWarehouseIdResponse406
    | PutApiV3StocksWarehouseIdResponse429
    | list[StocksWarehouseErrorItem]
    | None
):
    r"""Obnovit' ostatki tovarov

     Metod obnovljaet kolichestvo ostatkov tovarov prodavtsa [v spiske](/openapi/work-with-
    products#tag/Ostatki-na-skladah-prodavca/paths/~1api~1v3~1stocks~1%7BwarehouseId%7D/post).

    <div class=\"description_important\">
      Nazvanija parametrov zaprosa ne validirujutsja. Pri otpravke nekorrektnyh nazvanij vy poluchite
    uspeshnyj otvet (<code>204</code>), no ostatki ne obnovjatsja.
    </div>

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
        body (PutApiV3StocksWarehouseIdBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | Error | PutApiV3StocksWarehouseIdResponse401 | PutApiV3StocksWarehouseIdResponse406 | PutApiV3StocksWarehouseIdResponse429 | list[StocksWarehouseErrorItem]
    """

    return (
        await asyncio_detailed(
            warehouse_id=warehouse_id,
            client=client,
            body=body,
        )
    ).parsed
