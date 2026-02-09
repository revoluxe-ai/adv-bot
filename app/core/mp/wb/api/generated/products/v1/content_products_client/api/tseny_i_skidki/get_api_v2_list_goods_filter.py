from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_api_v2_list_goods_filter_response_200 import (
    GetApiV2ListGoodsFilterResponse200,
)
from ...models.get_api_v2_list_goods_filter_response_401 import (
    GetApiV2ListGoodsFilterResponse401,
)
from ...models.get_api_v2_list_goods_filter_response_429 import (
    GetApiV2ListGoodsFilterResponse429,
)
from ...models.response_error import ResponseError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    limit: int,
    offset: int | Unset = UNSET,
    filter_nm_id: int | Unset = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["limit"] = limit

    params["offset"] = offset

    params["filterNmID"] = filter_nm_id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v2/list/goods/filter",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    GetApiV2ListGoodsFilterResponse200
    | GetApiV2ListGoodsFilterResponse401
    | GetApiV2ListGoodsFilterResponse429
    | ResponseError
    | None
):
    if response.status_code == 200:
        response_200 = GetApiV2ListGoodsFilterResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = ResponseError.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = GetApiV2ListGoodsFilterResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = ResponseError.from_dict(response.json())

        return response_403

    if response.status_code == 429:
        response_429 = GetApiV2ListGoodsFilterResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    GetApiV2ListGoodsFilterResponse200
    | GetApiV2ListGoodsFilterResponse401
    | GetApiV2ListGoodsFilterResponse429
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
    filter_nm_id: int | Unset = UNSET,
) -> Response[
    GetApiV2ListGoodsFilterResponse200
    | GetApiV2ListGoodsFilterResponse401
    | GetApiV2ListGoodsFilterResponse429
    | ResponseError
]:
    r"""Poluchit' tovary s tsenami

     Metod vozvraschaet informatsiju o tovarah: tseny, valjutu, obschie skidki i skidki [WB
    Kluba](/openapi/work-with-products#tag/Ceny-i-skidki/paths/~1api~1v2~1upload~1task~1club-
    discount/post).
    <br><br>
    V odnom zaprose mozhno ukazat' tol'ko odin artikul.
    <br><br>
    Chtoby poluchit' informatsiju obo vseh tovarah prodavtsa, ne ukazyvaja artikuly, ustanovite
    `limit=1000`, v parametre `offset` ustanovite smeschenie po kolichestvu zapisej. Kolichestvo nuzhno
    rasschitat' po formule: `offset` pljus `limit` iz predyduschego zaprosa. Povtorjajte zapros, poka vy
    ne poluchite otvet s pustym massivom.<br><br>
    Ispol'zujte otdel'nye metody, chtoby poluchit' informatsiju:
      - o [neskol'kih tovarah po artikulam](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1list~1goods~1filter/post)
      - o [razmerah tovara](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1list~1goods~1size~1nm/get)

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
        filter_nm_id (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetApiV2ListGoodsFilterResponse200 | GetApiV2ListGoodsFilterResponse401 | GetApiV2ListGoodsFilterResponse429 | ResponseError]
    """

    kwargs = _get_kwargs(
        limit=limit,
        offset=offset,
        filter_nm_id=filter_nm_id,
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
    filter_nm_id: int | Unset = UNSET,
) -> (
    GetApiV2ListGoodsFilterResponse200
    | GetApiV2ListGoodsFilterResponse401
    | GetApiV2ListGoodsFilterResponse429
    | ResponseError
    | None
):
    r"""Poluchit' tovary s tsenami

     Metod vozvraschaet informatsiju o tovarah: tseny, valjutu, obschie skidki i skidki [WB
    Kluba](/openapi/work-with-products#tag/Ceny-i-skidki/paths/~1api~1v2~1upload~1task~1club-
    discount/post).
    <br><br>
    V odnom zaprose mozhno ukazat' tol'ko odin artikul.
    <br><br>
    Chtoby poluchit' informatsiju obo vseh tovarah prodavtsa, ne ukazyvaja artikuly, ustanovite
    `limit=1000`, v parametre `offset` ustanovite smeschenie po kolichestvu zapisej. Kolichestvo nuzhno
    rasschitat' po formule: `offset` pljus `limit` iz predyduschego zaprosa. Povtorjajte zapros, poka vy
    ne poluchite otvet s pustym massivom.<br><br>
    Ispol'zujte otdel'nye metody, chtoby poluchit' informatsiju:
      - o [neskol'kih tovarah po artikulam](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1list~1goods~1filter/post)
      - o [razmerah tovara](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1list~1goods~1size~1nm/get)

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
        filter_nm_id (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetApiV2ListGoodsFilterResponse200 | GetApiV2ListGoodsFilterResponse401 | GetApiV2ListGoodsFilterResponse429 | ResponseError
    """

    return sync_detailed(
        client=client,
        limit=limit,
        offset=offset,
        filter_nm_id=filter_nm_id,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    limit: int,
    offset: int | Unset = UNSET,
    filter_nm_id: int | Unset = UNSET,
) -> Response[
    GetApiV2ListGoodsFilterResponse200
    | GetApiV2ListGoodsFilterResponse401
    | GetApiV2ListGoodsFilterResponse429
    | ResponseError
]:
    r"""Poluchit' tovary s tsenami

     Metod vozvraschaet informatsiju o tovarah: tseny, valjutu, obschie skidki i skidki [WB
    Kluba](/openapi/work-with-products#tag/Ceny-i-skidki/paths/~1api~1v2~1upload~1task~1club-
    discount/post).
    <br><br>
    V odnom zaprose mozhno ukazat' tol'ko odin artikul.
    <br><br>
    Chtoby poluchit' informatsiju obo vseh tovarah prodavtsa, ne ukazyvaja artikuly, ustanovite
    `limit=1000`, v parametre `offset` ustanovite smeschenie po kolichestvu zapisej. Kolichestvo nuzhno
    rasschitat' po formule: `offset` pljus `limit` iz predyduschego zaprosa. Povtorjajte zapros, poka vy
    ne poluchite otvet s pustym massivom.<br><br>
    Ispol'zujte otdel'nye metody, chtoby poluchit' informatsiju:
      - o [neskol'kih tovarah po artikulam](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1list~1goods~1filter/post)
      - o [razmerah tovara](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1list~1goods~1size~1nm/get)

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
        filter_nm_id (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetApiV2ListGoodsFilterResponse200 | GetApiV2ListGoodsFilterResponse401 | GetApiV2ListGoodsFilterResponse429 | ResponseError]
    """

    kwargs = _get_kwargs(
        limit=limit,
        offset=offset,
        filter_nm_id=filter_nm_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    limit: int,
    offset: int | Unset = UNSET,
    filter_nm_id: int | Unset = UNSET,
) -> (
    GetApiV2ListGoodsFilterResponse200
    | GetApiV2ListGoodsFilterResponse401
    | GetApiV2ListGoodsFilterResponse429
    | ResponseError
    | None
):
    r"""Poluchit' tovary s tsenami

     Metod vozvraschaet informatsiju o tovarah: tseny, valjutu, obschie skidki i skidki [WB
    Kluba](/openapi/work-with-products#tag/Ceny-i-skidki/paths/~1api~1v2~1upload~1task~1club-
    discount/post).
    <br><br>
    V odnom zaprose mozhno ukazat' tol'ko odin artikul.
    <br><br>
    Chtoby poluchit' informatsiju obo vseh tovarah prodavtsa, ne ukazyvaja artikuly, ustanovite
    `limit=1000`, v parametre `offset` ustanovite smeschenie po kolichestvu zapisej. Kolichestvo nuzhno
    rasschitat' po formule: `offset` pljus `limit` iz predyduschego zaprosa. Povtorjajte zapros, poka vy
    ne poluchite otvet s pustym massivom.<br><br>
    Ispol'zujte otdel'nye metody, chtoby poluchit' informatsiju:
      - o [neskol'kih tovarah po artikulam](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1list~1goods~1filter/post)
      - o [razmerah tovara](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1list~1goods~1size~1nm/get)

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
        filter_nm_id (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetApiV2ListGoodsFilterResponse200 | GetApiV2ListGoodsFilterResponse401 | GetApiV2ListGoodsFilterResponse429 | ResponseError
    """

    return (
        await asyncio_detailed(
            client=client,
            limit=limit,
            offset=offset,
            filter_nm_id=filter_nm_id,
        )
    ).parsed
