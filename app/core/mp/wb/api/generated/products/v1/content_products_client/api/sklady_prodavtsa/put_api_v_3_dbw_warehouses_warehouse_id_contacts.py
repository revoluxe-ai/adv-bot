from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.put_api_v3_dbw_warehouses_warehouse_id_contacts_response_401 import (
    PutApiV3DbwWarehousesWarehouseIdContactsResponse401,
)
from ...models.put_api_v3_dbw_warehouses_warehouse_id_contacts_response_429 import (
    PutApiV3DbwWarehousesWarehouseIdContactsResponse429,
)
from ...models.store_contact_request_body import StoreContactRequestBody
from ...types import Response


def _get_kwargs(
    warehouse_id: int,
    *,
    body: StoreContactRequestBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/api/v3/dbw/warehouses/{warehouse_id}/contacts".format(
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
    | PutApiV3DbwWarehousesWarehouseIdContactsResponse401
    | PutApiV3DbwWarehousesWarehouseIdContactsResponse429
    | None
):
    if response.status_code == 204:
        response_204 = cast(Any, None)
        return response_204

    if response.status_code == 400:
        response_400 = Error.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PutApiV3DbwWarehousesWarehouseIdContactsResponse401.from_dict(
            response.json()
        )

        return response_401

    if response.status_code == 403:
        response_403 = Error.from_dict(response.json())

        return response_403

    if response.status_code == 429:
        response_429 = PutApiV3DbwWarehousesWarehouseIdContactsResponse429.from_dict(
            response.json()
        )

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
    | PutApiV3DbwWarehousesWarehouseIdContactsResponse401
    | PutApiV3DbwWarehousesWarehouseIdContactsResponse429
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
    body: StoreContactRequestBody,
) -> Response[
    Any
    | Error
    | PutApiV3DbwWarehousesWarehouseIdContactsResponse401
    | PutApiV3DbwWarehousesWarehouseIdContactsResponse429
]:
    r"""Obnovit' spisok kontaktov

     Metod obnovljaet spisok kontaktov [sklada prodavtsa](/openapi/work-with-products#tag/Sklady-
    prodavca/paths/~1api~1v3~1warehouses/get).

    <div class=\"description_important\">
      Spisok kontaktov perezapisyvaetsja pri obnovlenii. Poetomu v zaprose nuzhno peredat'
    <strong>vse</strong> parametry spiska kontaktov, v tom chisle te, kotorye vy ne sobiraetes'
    obnovljat'.
    </div>

    Tol'ko dlja skladov s tipom dostavki `3` — kur'erom WB (DBW).
    <br><br>
    K skladu mozhno dobavit' maksimum 5 kontaktov. Chtoby udalit' kontakty, otprav'te pustoj massiv
    `contacts`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja sledujuschih metodov DBW:
    <ul>
        <li>poluchenie i obnovlenie spiska kontaktov</li>
        <li>poluchenie i udalenie metadannyh</li>
        <li>metody sborochnyh zadanij</li>
    </ul>

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 300 zaprosov | 200 ms | 20 zaprosov |

    </div>

    Args:
        warehouse_id (int):  Example: 1.
        body (StoreContactRequestBody): Kontakty sklada prodavtsa

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | Error | PutApiV3DbwWarehousesWarehouseIdContactsResponse401 | PutApiV3DbwWarehousesWarehouseIdContactsResponse429]
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
    body: StoreContactRequestBody,
) -> (
    Any
    | Error
    | PutApiV3DbwWarehousesWarehouseIdContactsResponse401
    | PutApiV3DbwWarehousesWarehouseIdContactsResponse429
    | None
):
    r"""Obnovit' spisok kontaktov

     Metod obnovljaet spisok kontaktov [sklada prodavtsa](/openapi/work-with-products#tag/Sklady-
    prodavca/paths/~1api~1v3~1warehouses/get).

    <div class=\"description_important\">
      Spisok kontaktov perezapisyvaetsja pri obnovlenii. Poetomu v zaprose nuzhno peredat'
    <strong>vse</strong> parametry spiska kontaktov, v tom chisle te, kotorye vy ne sobiraetes'
    obnovljat'.
    </div>

    Tol'ko dlja skladov s tipom dostavki `3` — kur'erom WB (DBW).
    <br><br>
    K skladu mozhno dobavit' maksimum 5 kontaktov. Chtoby udalit' kontakty, otprav'te pustoj massiv
    `contacts`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja sledujuschih metodov DBW:
    <ul>
        <li>poluchenie i obnovlenie spiska kontaktov</li>
        <li>poluchenie i udalenie metadannyh</li>
        <li>metody sborochnyh zadanij</li>
    </ul>

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 300 zaprosov | 200 ms | 20 zaprosov |

    </div>

    Args:
        warehouse_id (int):  Example: 1.
        body (StoreContactRequestBody): Kontakty sklada prodavtsa

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | Error | PutApiV3DbwWarehousesWarehouseIdContactsResponse401 | PutApiV3DbwWarehousesWarehouseIdContactsResponse429
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
    body: StoreContactRequestBody,
) -> Response[
    Any
    | Error
    | PutApiV3DbwWarehousesWarehouseIdContactsResponse401
    | PutApiV3DbwWarehousesWarehouseIdContactsResponse429
]:
    r"""Obnovit' spisok kontaktov

     Metod obnovljaet spisok kontaktov [sklada prodavtsa](/openapi/work-with-products#tag/Sklady-
    prodavca/paths/~1api~1v3~1warehouses/get).

    <div class=\"description_important\">
      Spisok kontaktov perezapisyvaetsja pri obnovlenii. Poetomu v zaprose nuzhno peredat'
    <strong>vse</strong> parametry spiska kontaktov, v tom chisle te, kotorye vy ne sobiraetes'
    obnovljat'.
    </div>

    Tol'ko dlja skladov s tipom dostavki `3` — kur'erom WB (DBW).
    <br><br>
    K skladu mozhno dobavit' maksimum 5 kontaktov. Chtoby udalit' kontakty, otprav'te pustoj massiv
    `contacts`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja sledujuschih metodov DBW:
    <ul>
        <li>poluchenie i obnovlenie spiska kontaktov</li>
        <li>poluchenie i udalenie metadannyh</li>
        <li>metody sborochnyh zadanij</li>
    </ul>

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 300 zaprosov | 200 ms | 20 zaprosov |

    </div>

    Args:
        warehouse_id (int):  Example: 1.
        body (StoreContactRequestBody): Kontakty sklada prodavtsa

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | Error | PutApiV3DbwWarehousesWarehouseIdContactsResponse401 | PutApiV3DbwWarehousesWarehouseIdContactsResponse429]
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
    body: StoreContactRequestBody,
) -> (
    Any
    | Error
    | PutApiV3DbwWarehousesWarehouseIdContactsResponse401
    | PutApiV3DbwWarehousesWarehouseIdContactsResponse429
    | None
):
    r"""Obnovit' spisok kontaktov

     Metod obnovljaet spisok kontaktov [sklada prodavtsa](/openapi/work-with-products#tag/Sklady-
    prodavca/paths/~1api~1v3~1warehouses/get).

    <div class=\"description_important\">
      Spisok kontaktov perezapisyvaetsja pri obnovlenii. Poetomu v zaprose nuzhno peredat'
    <strong>vse</strong> parametry spiska kontaktov, v tom chisle te, kotorye vy ne sobiraetes'
    obnovljat'.
    </div>

    Tol'ko dlja skladov s tipom dostavki `3` — kur'erom WB (DBW).
    <br><br>
    K skladu mozhno dobavit' maksimum 5 kontaktov. Chtoby udalit' kontakty, otprav'te pustoj massiv
    `contacts`.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja sledujuschih metodov DBW:
    <ul>
        <li>poluchenie i obnovlenie spiska kontaktov</li>
        <li>poluchenie i udalenie metadannyh</li>
        <li>metody sborochnyh zadanij</li>
    </ul>

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 300 zaprosov | 200 ms | 20 zaprosov |

    </div>

    Args:
        warehouse_id (int):  Example: 1.
        body (StoreContactRequestBody): Kontakty sklada prodavtsa

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | Error | PutApiV3DbwWarehousesWarehouseIdContactsResponse401 | PutApiV3DbwWarehousesWarehouseIdContactsResponse429
    """

    return (
        await asyncio_detailed(
            warehouse_id=warehouse_id,
            client=client,
            body=body,
        )
    ).parsed
