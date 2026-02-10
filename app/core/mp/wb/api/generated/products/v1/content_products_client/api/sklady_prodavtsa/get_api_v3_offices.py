from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.get_api_v3_offices_response_401 import GetApiV3OfficesResponse401
from ...models.get_api_v3_offices_response_429 import GetApiV3OfficesResponse429
from ...models.office import Office
from ...types import Response


def _get_kwargs() -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v3/offices",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    Error
    | GetApiV3OfficesResponse401
    | GetApiV3OfficesResponse429
    | list[Office]
    | None
):
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = Office.from_dict(response_200_item_data)

            response_200.append(response_200_item)

        return response_200

    if response.status_code == 401:
        response_401 = GetApiV3OfficesResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = Error.from_dict(response.json())

        return response_403

    if response.status_code == 429:
        response_429 = GetApiV3OfficesResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    Error | GetApiV3OfficesResponse401 | GetApiV3OfficesResponse429 | list[Office]
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
) -> Response[
    Error | GetApiV3OfficesResponse401 | GetApiV3OfficesResponse429 | list[Office]
]:
    r"""Poluchit' spisok skladov WB

     Metod vozvraschaet spisok vseh skladov WB dlja privjazki k skladam prodavtsa. Prednaznachen dlja
    opredelenija skladov WB, chtoby sdavat' gotovye zakazy po modeli [FBS](/openapi/orders-
    fbs#tag/Zakazy-FBS) (Fulfillment by Seller).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov <strong>skladov prodavtsa</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 300 zaprosov | 200 ms | 20 zaprosov |

    Odin zapros s kodom otveta <code>409</code> uchityvaetsja kak 10 zaprosov
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetApiV3OfficesResponse401 | GetApiV3OfficesResponse429 | list[Office]]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
) -> (
    Error
    | GetApiV3OfficesResponse401
    | GetApiV3OfficesResponse429
    | list[Office]
    | None
):
    r"""Poluchit' spisok skladov WB

     Metod vozvraschaet spisok vseh skladov WB dlja privjazki k skladam prodavtsa. Prednaznachen dlja
    opredelenija skladov WB, chtoby sdavat' gotovye zakazy po modeli [FBS](/openapi/orders-
    fbs#tag/Zakazy-FBS) (Fulfillment by Seller).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov <strong>skladov prodavtsa</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 300 zaprosov | 200 ms | 20 zaprosov |

    Odin zapros s kodom otveta <code>409</code> uchityvaetsja kak 10 zaprosov
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetApiV3OfficesResponse401 | GetApiV3OfficesResponse429 | list[Office]
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
) -> Response[
    Error | GetApiV3OfficesResponse401 | GetApiV3OfficesResponse429 | list[Office]
]:
    r"""Poluchit' spisok skladov WB

     Metod vozvraschaet spisok vseh skladov WB dlja privjazki k skladam prodavtsa. Prednaznachen dlja
    opredelenija skladov WB, chtoby sdavat' gotovye zakazy po modeli [FBS](/openapi/orders-
    fbs#tag/Zakazy-FBS) (Fulfillment by Seller).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov <strong>skladov prodavtsa</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 300 zaprosov | 200 ms | 20 zaprosov |

    Odin zapros s kodom otveta <code>409</code> uchityvaetsja kak 10 zaprosov
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetApiV3OfficesResponse401 | GetApiV3OfficesResponse429 | list[Office]]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
) -> (
    Error
    | GetApiV3OfficesResponse401
    | GetApiV3OfficesResponse429
    | list[Office]
    | None
):
    r"""Poluchit' spisok skladov WB

     Metod vozvraschaet spisok vseh skladov WB dlja privjazki k skladam prodavtsa. Prednaznachen dlja
    opredelenija skladov WB, chtoby sdavat' gotovye zakazy po modeli [FBS](/openapi/orders-
    fbs#tag/Zakazy-FBS) (Fulfillment by Seller).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov <strong>skladov prodavtsa</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 300 zaprosov | 200 ms | 20 zaprosov |

    Odin zapros s kodom otveta <code>409</code> uchityvaetsja kak 10 zaprosov
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetApiV3OfficesResponse401 | GetApiV3OfficesResponse429 | list[Office]
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
