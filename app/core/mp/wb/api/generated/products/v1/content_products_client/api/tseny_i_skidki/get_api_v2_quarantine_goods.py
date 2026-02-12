from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_api_v2_quarantine_goods_response_200 import (
    GetApiV2QuarantineGoodsResponse200,
)
from ...models.get_api_v2_quarantine_goods_response_401 import (
    GetApiV2QuarantineGoodsResponse401,
)
from ...models.get_api_v2_quarantine_goods_response_429 import (
    GetApiV2QuarantineGoodsResponse429,
)
from ...models.response_error import ResponseError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    limit: int,
    offset: int | Unset = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["limit"] = limit

    params["offset"] = offset

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v2/quarantine/goods",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    GetApiV2QuarantineGoodsResponse200
    | GetApiV2QuarantineGoodsResponse401
    | GetApiV2QuarantineGoodsResponse429
    | ResponseError
    | None
):
    if response.status_code == 200:
        response_200 = GetApiV2QuarantineGoodsResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = ResponseError.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = GetApiV2QuarantineGoodsResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = ResponseError.from_dict(response.json())

        return response_403

    if response.status_code == 422:
        response_422 = ResponseError.from_dict(response.json())

        return response_422

    if response.status_code == 429:
        response_429 = GetApiV2QuarantineGoodsResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    GetApiV2QuarantineGoodsResponse200
    | GetApiV2QuarantineGoodsResponse401
    | GetApiV2QuarantineGoodsResponse429
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
) -> Response[
    GetApiV2QuarantineGoodsResponse200
    | GetApiV2QuarantineGoodsResponse401
    | GetApiV2QuarantineGoodsResponse429
    | ResponseError
]:
    r"""Poluchit' tovary v karantine

     Metod vozvraschaet informatsiju o tovarah v karantine.
    <br><br>
    Esli novaja tsena tovara so skidkoj budet minimum v 3 raza men'she staroj, tovar popadet
    v [karantin](https://seller.wildberries.ru/instructions/ru/ru/material/price-quarantine) i budet
    prodavat'sja po staroj tsene. Oshibka ob etom budet v otvetah metodov [sostojanij
    zagruzok](/openapi/work-with-products#tag/Ceny-i-skidki/paths/~1api~1v2~1history~1tasks/get).
    <br><br>
    Vy mozhete izmenit' tsenu ili skidku s pomosch'ju API libo vyvesti tovar iz karantina v [lichnom
    kabinete](https://seller.wildberries.ru/discount-and-prices/quarantine).
    <br><br>
    Dlja tovarov s [porazmernoj ustanovkoj tsen](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1upload~1task~1size/post) karantin ne primenjaetsja.

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

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetApiV2QuarantineGoodsResponse200 | GetApiV2QuarantineGoodsResponse401 | GetApiV2QuarantineGoodsResponse429 | ResponseError]
    """

    kwargs = _get_kwargs(
        limit=limit,
        offset=offset,
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
) -> (
    GetApiV2QuarantineGoodsResponse200
    | GetApiV2QuarantineGoodsResponse401
    | GetApiV2QuarantineGoodsResponse429
    | ResponseError
    | None
):
    r"""Poluchit' tovary v karantine

     Metod vozvraschaet informatsiju o tovarah v karantine.
    <br><br>
    Esli novaja tsena tovara so skidkoj budet minimum v 3 raza men'she staroj, tovar popadet
    v [karantin](https://seller.wildberries.ru/instructions/ru/ru/material/price-quarantine) i budet
    prodavat'sja po staroj tsene. Oshibka ob etom budet v otvetah metodov [sostojanij
    zagruzok](/openapi/work-with-products#tag/Ceny-i-skidki/paths/~1api~1v2~1history~1tasks/get).
    <br><br>
    Vy mozhete izmenit' tsenu ili skidku s pomosch'ju API libo vyvesti tovar iz karantina v [lichnom
    kabinete](https://seller.wildberries.ru/discount-and-prices/quarantine).
    <br><br>
    Dlja tovarov s [porazmernoj ustanovkoj tsen](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1upload~1task~1size/post) karantin ne primenjaetsja.

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

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetApiV2QuarantineGoodsResponse200 | GetApiV2QuarantineGoodsResponse401 | GetApiV2QuarantineGoodsResponse429 | ResponseError
    """

    return sync_detailed(
        client=client,
        limit=limit,
        offset=offset,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    limit: int,
    offset: int | Unset = UNSET,
) -> Response[
    GetApiV2QuarantineGoodsResponse200
    | GetApiV2QuarantineGoodsResponse401
    | GetApiV2QuarantineGoodsResponse429
    | ResponseError
]:
    r"""Poluchit' tovary v karantine

     Metod vozvraschaet informatsiju o tovarah v karantine.
    <br><br>
    Esli novaja tsena tovara so skidkoj budet minimum v 3 raza men'she staroj, tovar popadet
    v [karantin](https://seller.wildberries.ru/instructions/ru/ru/material/price-quarantine) i budet
    prodavat'sja po staroj tsene. Oshibka ob etom budet v otvetah metodov [sostojanij
    zagruzok](/openapi/work-with-products#tag/Ceny-i-skidki/paths/~1api~1v2~1history~1tasks/get).
    <br><br>
    Vy mozhete izmenit' tsenu ili skidku s pomosch'ju API libo vyvesti tovar iz karantina v [lichnom
    kabinete](https://seller.wildberries.ru/discount-and-prices/quarantine).
    <br><br>
    Dlja tovarov s [porazmernoj ustanovkoj tsen](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1upload~1task~1size/post) karantin ne primenjaetsja.

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

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetApiV2QuarantineGoodsResponse200 | GetApiV2QuarantineGoodsResponse401 | GetApiV2QuarantineGoodsResponse429 | ResponseError]
    """

    kwargs = _get_kwargs(
        limit=limit,
        offset=offset,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    limit: int,
    offset: int | Unset = UNSET,
) -> (
    GetApiV2QuarantineGoodsResponse200
    | GetApiV2QuarantineGoodsResponse401
    | GetApiV2QuarantineGoodsResponse429
    | ResponseError
    | None
):
    r"""Poluchit' tovary v karantine

     Metod vozvraschaet informatsiju o tovarah v karantine.
    <br><br>
    Esli novaja tsena tovara so skidkoj budet minimum v 3 raza men'she staroj, tovar popadet
    v [karantin](https://seller.wildberries.ru/instructions/ru/ru/material/price-quarantine) i budet
    prodavat'sja po staroj tsene. Oshibka ob etom budet v otvetah metodov [sostojanij
    zagruzok](/openapi/work-with-products#tag/Ceny-i-skidki/paths/~1api~1v2~1history~1tasks/get).
    <br><br>
    Vy mozhete izmenit' tsenu ili skidku s pomosch'ju API libo vyvesti tovar iz karantina v [lichnom
    kabinete](https://seller.wildberries.ru/discount-and-prices/quarantine).
    <br><br>
    Dlja tovarov s [porazmernoj ustanovkoj tsen](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1upload~1task~1size/post) karantin ne primenjaetsja.

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

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetApiV2QuarantineGoodsResponse200 | GetApiV2QuarantineGoodsResponse401 | GetApiV2QuarantineGoodsResponse429 | ResponseError
    """

    return (
        await asyncio_detailed(
            client=client,
            limit=limit,
            offset=offset,
        )
    ).parsed
