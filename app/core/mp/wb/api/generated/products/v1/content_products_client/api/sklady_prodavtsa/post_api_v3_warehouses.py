from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.post_api_v3_warehouses_body import PostApiV3WarehousesBody
from ...models.post_api_v3_warehouses_response_201 import PostApiV3WarehousesResponse201
from ...models.post_api_v3_warehouses_response_401 import PostApiV3WarehousesResponse401
from ...models.post_api_v3_warehouses_response_429 import PostApiV3WarehousesResponse429
from ...types import Response


def _get_kwargs(
    *,
    body: PostApiV3WarehousesBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v3/warehouses",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    Error
    | PostApiV3WarehousesResponse201
    | PostApiV3WarehousesResponse401
    | PostApiV3WarehousesResponse429
    | None
):
    if response.status_code == 201:
        response_201 = PostApiV3WarehousesResponse201.from_dict(response.json())

        return response_201

    if response.status_code == 400:
        response_400 = Error.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostApiV3WarehousesResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = Error.from_dict(response.json())

        return response_403

    if response.status_code == 404:
        response_404 = Error.from_dict(response.json())

        return response_404

    if response.status_code == 409:
        response_409 = Error.from_dict(response.json())

        return response_409

    if response.status_code == 429:
        response_429 = PostApiV3WarehousesResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    Error
    | PostApiV3WarehousesResponse201
    | PostApiV3WarehousesResponse401
    | PostApiV3WarehousesResponse429
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
    body: PostApiV3WarehousesBody,
) -> Response[
    Error
    | PostApiV3WarehousesResponse201
    | PostApiV3WarehousesResponse401
    | PostApiV3WarehousesResponse429
]:
    r"""Sozdat' sklad prodavtsa

     Metod sozdaet sklad prodavtsa dlja raboty s [ostatkami tovarov](/openapi/work-with-
    products#tag/Ostatki-na-skladah-prodavca/paths/~1api~1v3~1stocks~1%7BwarehouseId%7D/post). Nuzhno
    privjazat' k skladu prodavtsa [sklad WB](/openapi/work-with-products#tag/Sklady-
    prodavca/paths/~1api~1v3~1offices/get) dlja raboty po modeli [FBS](/openapi/orders-fbs#tag/Zakazy-
    FBS) (Fulfillment by Seller).

    <div class=\"description_important\">
      Nel'zja privjazyvat' sklad WB, kotoryj uzhe ispol'zuetsja
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov <strong>skladov prodavtsa</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 300 zaprosov | 200 ms | 20 zaprosov |

    Odin zapros s kodom otveta <code>409</code> uchityvaetsja kak 10 zaprosov
    </div>

    Args:
        body (PostApiV3WarehousesBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | PostApiV3WarehousesResponse201 | PostApiV3WarehousesResponse401 | PostApiV3WarehousesResponse429]
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
    body: PostApiV3WarehousesBody,
) -> (
    Error
    | PostApiV3WarehousesResponse201
    | PostApiV3WarehousesResponse401
    | PostApiV3WarehousesResponse429
    | None
):
    r"""Sozdat' sklad prodavtsa

     Metod sozdaet sklad prodavtsa dlja raboty s [ostatkami tovarov](/openapi/work-with-
    products#tag/Ostatki-na-skladah-prodavca/paths/~1api~1v3~1stocks~1%7BwarehouseId%7D/post). Nuzhno
    privjazat' k skladu prodavtsa [sklad WB](/openapi/work-with-products#tag/Sklady-
    prodavca/paths/~1api~1v3~1offices/get) dlja raboty po modeli [FBS](/openapi/orders-fbs#tag/Zakazy-
    FBS) (Fulfillment by Seller).

    <div class=\"description_important\">
      Nel'zja privjazyvat' sklad WB, kotoryj uzhe ispol'zuetsja
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov <strong>skladov prodavtsa</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 300 zaprosov | 200 ms | 20 zaprosov |

    Odin zapros s kodom otveta <code>409</code> uchityvaetsja kak 10 zaprosov
    </div>

    Args:
        body (PostApiV3WarehousesBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | PostApiV3WarehousesResponse201 | PostApiV3WarehousesResponse401 | PostApiV3WarehousesResponse429
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PostApiV3WarehousesBody,
) -> Response[
    Error
    | PostApiV3WarehousesResponse201
    | PostApiV3WarehousesResponse401
    | PostApiV3WarehousesResponse429
]:
    r"""Sozdat' sklad prodavtsa

     Metod sozdaet sklad prodavtsa dlja raboty s [ostatkami tovarov](/openapi/work-with-
    products#tag/Ostatki-na-skladah-prodavca/paths/~1api~1v3~1stocks~1%7BwarehouseId%7D/post). Nuzhno
    privjazat' k skladu prodavtsa [sklad WB](/openapi/work-with-products#tag/Sklady-
    prodavca/paths/~1api~1v3~1offices/get) dlja raboty po modeli [FBS](/openapi/orders-fbs#tag/Zakazy-
    FBS) (Fulfillment by Seller).

    <div class=\"description_important\">
      Nel'zja privjazyvat' sklad WB, kotoryj uzhe ispol'zuetsja
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov <strong>skladov prodavtsa</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 300 zaprosov | 200 ms | 20 zaprosov |

    Odin zapros s kodom otveta <code>409</code> uchityvaetsja kak 10 zaprosov
    </div>

    Args:
        body (PostApiV3WarehousesBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | PostApiV3WarehousesResponse201 | PostApiV3WarehousesResponse401 | PostApiV3WarehousesResponse429]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: PostApiV3WarehousesBody,
) -> (
    Error
    | PostApiV3WarehousesResponse201
    | PostApiV3WarehousesResponse401
    | PostApiV3WarehousesResponse429
    | None
):
    r"""Sozdat' sklad prodavtsa

     Metod sozdaet sklad prodavtsa dlja raboty s [ostatkami tovarov](/openapi/work-with-
    products#tag/Ostatki-na-skladah-prodavca/paths/~1api~1v3~1stocks~1%7BwarehouseId%7D/post). Nuzhno
    privjazat' k skladu prodavtsa [sklad WB](/openapi/work-with-products#tag/Sklady-
    prodavca/paths/~1api~1v3~1offices/get) dlja raboty po modeli [FBS](/openapi/orders-fbs#tag/Zakazy-
    FBS) (Fulfillment by Seller).

    <div class=\"description_important\">
      Nel'zja privjazyvat' sklad WB, kotoryj uzhe ispol'zuetsja
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov <strong>skladov prodavtsa</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 300 zaprosov | 200 ms | 20 zaprosov |

    Odin zapros s kodom otveta <code>409</code> uchityvaetsja kak 10 zaprosov
    </div>

    Args:
        body (PostApiV3WarehousesBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | PostApiV3WarehousesResponse201 | PostApiV3WarehousesResponse401 | PostApiV3WarehousesResponse429
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
