from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_api_v2_buffer_goods_task_response_200 import (
    GetApiV2BufferGoodsTaskResponse200,
)
from ...models.get_api_v2_buffer_goods_task_response_401 import (
    GetApiV2BufferGoodsTaskResponse401,
)
from ...models.get_api_v2_buffer_goods_task_response_429 import (
    GetApiV2BufferGoodsTaskResponse429,
)
from ...models.response_error import ResponseError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    limit: int,
    offset: int | Unset = UNSET,
    upload_id: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["limit"] = limit

    params["offset"] = offset

    params["uploadID"] = upload_id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v2/buffer/goods/task",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    GetApiV2BufferGoodsTaskResponse200
    | GetApiV2BufferGoodsTaskResponse401
    | GetApiV2BufferGoodsTaskResponse429
    | ResponseError
    | None
):
    if response.status_code == 200:
        response_200 = GetApiV2BufferGoodsTaskResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = ResponseError.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = GetApiV2BufferGoodsTaskResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = ResponseError.from_dict(response.json())

        return response_403

    if response.status_code == 429:
        response_429 = GetApiV2BufferGoodsTaskResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    GetApiV2BufferGoodsTaskResponse200
    | GetApiV2BufferGoodsTaskResponse401
    | GetApiV2BufferGoodsTaskResponse429
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
    limit: int,
    offset: int | Unset = UNSET,
    upload_id: int,
) -> Response[
    GetApiV2BufferGoodsTaskResponse200
    | GetApiV2BufferGoodsTaskResponse401
    | GetApiV2BufferGoodsTaskResponse429
    | ResponseError
]:
    r"""Detalizatsija neobrabotannoj zagruzki

     Metod vozvraschaet informatsiju o tovarah i oshibkah v tovarah iz zagruzki v obrabotke.

    <div class=\"description_important\">
      Neobrabotannaja zagruzka — eto zagruzka skidok v <a href=\"/openapi/promotion#tag/Kalendar-
    akcij\">kalendare aktsij</a>. Takie skidki primenjatsja k tovaram tol'ko v moment starta aktsii.
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Tseny i skidki</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sek | 10 zaprosov | 600 ms | 5 zaprosov |

    </div>

    Args:
        limit (int):  Example: 10.
        offset (int | Unset):
        upload_id (int):  Example: 146567.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetApiV2BufferGoodsTaskResponse200 | GetApiV2BufferGoodsTaskResponse401 | GetApiV2BufferGoodsTaskResponse429 | ResponseError]
    """

    kwargs = _get_kwargs(
        limit=limit,
        offset=offset,
        upload_id=upload_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    limit: int,
    offset: int | Unset = UNSET,
    upload_id: int,
) -> (
    GetApiV2BufferGoodsTaskResponse200
    | GetApiV2BufferGoodsTaskResponse401
    | GetApiV2BufferGoodsTaskResponse429
    | ResponseError
    | None
):
    r"""Detalizatsija neobrabotannoj zagruzki

     Metod vozvraschaet informatsiju o tovarah i oshibkah v tovarah iz zagruzki v obrabotke.

    <div class=\"description_important\">
      Neobrabotannaja zagruzka — eto zagruzka skidok v <a href=\"/openapi/promotion#tag/Kalendar-
    akcij\">kalendare aktsij</a>. Takie skidki primenjatsja k tovaram tol'ko v moment starta aktsii.
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Tseny i skidki</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sek | 10 zaprosov | 600 ms | 5 zaprosov |

    </div>

    Args:
        limit (int):  Example: 10.
        offset (int | Unset):
        upload_id (int):  Example: 146567.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetApiV2BufferGoodsTaskResponse200 | GetApiV2BufferGoodsTaskResponse401 | GetApiV2BufferGoodsTaskResponse429 | ResponseError
    """

    return sync_detailed(
        client=client,
        limit=limit,
        offset=offset,
        upload_id=upload_id,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    limit: int,
    offset: int | Unset = UNSET,
    upload_id: int,
) -> Response[
    GetApiV2BufferGoodsTaskResponse200
    | GetApiV2BufferGoodsTaskResponse401
    | GetApiV2BufferGoodsTaskResponse429
    | ResponseError
]:
    r"""Detalizatsija neobrabotannoj zagruzki

     Metod vozvraschaet informatsiju o tovarah i oshibkah v tovarah iz zagruzki v obrabotke.

    <div class=\"description_important\">
      Neobrabotannaja zagruzka — eto zagruzka skidok v <a href=\"/openapi/promotion#tag/Kalendar-
    akcij\">kalendare aktsij</a>. Takie skidki primenjatsja k tovaram tol'ko v moment starta aktsii.
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Tseny i skidki</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sek | 10 zaprosov | 600 ms | 5 zaprosov |

    </div>

    Args:
        limit (int):  Example: 10.
        offset (int | Unset):
        upload_id (int):  Example: 146567.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetApiV2BufferGoodsTaskResponse200 | GetApiV2BufferGoodsTaskResponse401 | GetApiV2BufferGoodsTaskResponse429 | ResponseError]
    """

    kwargs = _get_kwargs(
        limit=limit,
        offset=offset,
        upload_id=upload_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    limit: int,
    offset: int | Unset = UNSET,
    upload_id: int,
) -> (
    GetApiV2BufferGoodsTaskResponse200
    | GetApiV2BufferGoodsTaskResponse401
    | GetApiV2BufferGoodsTaskResponse429
    | ResponseError
    | None
):
    r"""Detalizatsija neobrabotannoj zagruzki

     Metod vozvraschaet informatsiju o tovarah i oshibkah v tovarah iz zagruzki v obrabotke.

    <div class=\"description_important\">
      Neobrabotannaja zagruzka — eto zagruzka skidok v <a href=\"/openapi/promotion#tag/Kalendar-
    akcij\">kalendare aktsij</a>. Takie skidki primenjatsja k tovaram tol'ko v moment starta aktsii.
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Tseny i skidki</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sek | 10 zaprosov | 600 ms | 5 zaprosov |

    </div>

    Args:
        limit (int):  Example: 10.
        offset (int | Unset):
        upload_id (int):  Example: 146567.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetApiV2BufferGoodsTaskResponse200 | GetApiV2BufferGoodsTaskResponse401 | GetApiV2BufferGoodsTaskResponse429 | ResponseError
    """

    return (
        await asyncio_detailed(
            client=client,
            limit=limit,
            offset=offset,
            upload_id=upload_id,
        )
    ).parsed
