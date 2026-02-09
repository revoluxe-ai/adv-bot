from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_api_v2_history_tasks_response_200 import (
    GetApiV2HistoryTasksResponse200,
)
from ...models.get_api_v2_history_tasks_response_401 import (
    GetApiV2HistoryTasksResponse401,
)
from ...models.get_api_v2_history_tasks_response_429 import (
    GetApiV2HistoryTasksResponse429,
)
from ...models.response_error import ResponseError
from ...types import UNSET, Response


def _get_kwargs(
    *,
    upload_id: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["uploadID"] = upload_id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v2/history/tasks",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    GetApiV2HistoryTasksResponse200
    | GetApiV2HistoryTasksResponse401
    | GetApiV2HistoryTasksResponse429
    | ResponseError
    | None
):
    if response.status_code == 200:
        response_200 = GetApiV2HistoryTasksResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = ResponseError.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = GetApiV2HistoryTasksResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = ResponseError.from_dict(response.json())

        return response_403

    if response.status_code == 429:
        response_429 = GetApiV2HistoryTasksResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    GetApiV2HistoryTasksResponse200
    | GetApiV2HistoryTasksResponse401
    | GetApiV2HistoryTasksResponse429
    | ResponseError
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
    upload_id: int,
) -> Response[
    GetApiV2HistoryTasksResponse200
    | GetApiV2HistoryTasksResponse401
    | GetApiV2HistoryTasksResponse429
    | ResponseError
]:
    r"""Sostojanie obrabotannoj zagruzki

     Metod vozvraschaet informatsiju ob obrabotannoj zagruzke tsen i skidok.

    <div class=\"description_important\">
      Obrabotannaja zagruzka — eto zagruzka tsen i skidok dlja <a href=\"/openapi/work-with-
    products#tag/Ceny-i-skidki/paths/~1api~1v2~1upload~1task/post\">tovarov</a>, tsen dlja <a
    href=\"/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1upload~1task~1size/post\">razmerov tovarov</a> i skidok <a
    href=\"/openapi/work-with-products#tag/Ceny-i-skidki/paths/~1api~1v2~1upload~1task~1club-
    discount/post\">WB Kluba</a>.
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Tseny i skidki</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sek | 10 zaprosov | 600 ms | 5 zaprosov |

    </div>

    Args:
        upload_id (int):  Example: 146567.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetApiV2HistoryTasksResponse200 | GetApiV2HistoryTasksResponse401 | GetApiV2HistoryTasksResponse429 | ResponseError]
    """

    kwargs = _get_kwargs(
        upload_id=upload_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    upload_id: int,
) -> (
    GetApiV2HistoryTasksResponse200
    | GetApiV2HistoryTasksResponse401
    | GetApiV2HistoryTasksResponse429
    | ResponseError
    | None
):
    r"""Sostojanie obrabotannoj zagruzki

     Metod vozvraschaet informatsiju ob obrabotannoj zagruzke tsen i skidok.

    <div class=\"description_important\">
      Obrabotannaja zagruzka — eto zagruzka tsen i skidok dlja <a href=\"/openapi/work-with-
    products#tag/Ceny-i-skidki/paths/~1api~1v2~1upload~1task/post\">tovarov</a>, tsen dlja <a
    href=\"/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1upload~1task~1size/post\">razmerov tovarov</a> i skidok <a
    href=\"/openapi/work-with-products#tag/Ceny-i-skidki/paths/~1api~1v2~1upload~1task~1club-
    discount/post\">WB Kluba</a>.
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Tseny i skidki</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sek | 10 zaprosov | 600 ms | 5 zaprosov |

    </div>

    Args:
        upload_id (int):  Example: 146567.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetApiV2HistoryTasksResponse200 | GetApiV2HistoryTasksResponse401 | GetApiV2HistoryTasksResponse429 | ResponseError
    """

    return sync_detailed(
        client=client,
        upload_id=upload_id,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    upload_id: int,
) -> Response[
    GetApiV2HistoryTasksResponse200
    | GetApiV2HistoryTasksResponse401
    | GetApiV2HistoryTasksResponse429
    | ResponseError
]:
    r"""Sostojanie obrabotannoj zagruzki

     Metod vozvraschaet informatsiju ob obrabotannoj zagruzke tsen i skidok.

    <div class=\"description_important\">
      Obrabotannaja zagruzka — eto zagruzka tsen i skidok dlja <a href=\"/openapi/work-with-
    products#tag/Ceny-i-skidki/paths/~1api~1v2~1upload~1task/post\">tovarov</a>, tsen dlja <a
    href=\"/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1upload~1task~1size/post\">razmerov tovarov</a> i skidok <a
    href=\"/openapi/work-with-products#tag/Ceny-i-skidki/paths/~1api~1v2~1upload~1task~1club-
    discount/post\">WB Kluba</a>.
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Tseny i skidki</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sek | 10 zaprosov | 600 ms | 5 zaprosov |

    </div>

    Args:
        upload_id (int):  Example: 146567.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetApiV2HistoryTasksResponse200 | GetApiV2HistoryTasksResponse401 | GetApiV2HistoryTasksResponse429 | ResponseError]
    """

    kwargs = _get_kwargs(
        upload_id=upload_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    upload_id: int,
) -> (
    GetApiV2HistoryTasksResponse200
    | GetApiV2HistoryTasksResponse401
    | GetApiV2HistoryTasksResponse429
    | ResponseError
    | None
):
    r"""Sostojanie obrabotannoj zagruzki

     Metod vozvraschaet informatsiju ob obrabotannoj zagruzke tsen i skidok.

    <div class=\"description_important\">
      Obrabotannaja zagruzka — eto zagruzka tsen i skidok dlja <a href=\"/openapi/work-with-
    products#tag/Ceny-i-skidki/paths/~1api~1v2~1upload~1task/post\">tovarov</a>, tsen dlja <a
    href=\"/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1upload~1task~1size/post\">razmerov tovarov</a> i skidok <a
    href=\"/openapi/work-with-products#tag/Ceny-i-skidki/paths/~1api~1v2~1upload~1task~1club-
    discount/post\">WB Kluba</a>.
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Tseny i skidki</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sek | 10 zaprosov | 600 ms | 5 zaprosov |

    </div>

    Args:
        upload_id (int):  Example: 146567.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetApiV2HistoryTasksResponse200 | GetApiV2HistoryTasksResponse401 | GetApiV2HistoryTasksResponse429 | ResponseError
    """

    return (
        await asyncio_detailed(
            client=client,
            upload_id=upload_id,
        )
    ).parsed
