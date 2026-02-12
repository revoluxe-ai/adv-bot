from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_api_v2_list_goods_filter_body import PostApiV2ListGoodsFilterBody
from ...models.post_api_v2_list_goods_filter_response_200 import (
    PostApiV2ListGoodsFilterResponse200,
)
from ...models.post_api_v2_list_goods_filter_response_401 import (
    PostApiV2ListGoodsFilterResponse401,
)
from ...models.post_api_v2_list_goods_filter_response_429 import (
    PostApiV2ListGoodsFilterResponse429,
)
from ...models.response_error import ResponseError
from ...types import Response


def _get_kwargs(
    *,
    body: PostApiV2ListGoodsFilterBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v2/list/goods/filter",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    PostApiV2ListGoodsFilterResponse200
    | PostApiV2ListGoodsFilterResponse401
    | PostApiV2ListGoodsFilterResponse429
    | ResponseError
    | None
):
    if response.status_code == 200:
        response_200 = PostApiV2ListGoodsFilterResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = ResponseError.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostApiV2ListGoodsFilterResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = ResponseError.from_dict(response.json())

        return response_403

    if response.status_code == 429:
        response_429 = PostApiV2ListGoodsFilterResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    PostApiV2ListGoodsFilterResponse200
    | PostApiV2ListGoodsFilterResponse401
    | PostApiV2ListGoodsFilterResponse429
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
    body: PostApiV2ListGoodsFilterBody,
) -> Response[
    PostApiV2ListGoodsFilterResponse200
    | PostApiV2ListGoodsFilterResponse401
    | PostApiV2ListGoodsFilterResponse429
    | ResponseError
]:
    r"""Poluchit' tovary s tsenami po artikulam

     Metod vozvraschaet informatsiju o tovarah po ih artikulam: tseny, valjutu, obschie skidki i skidki
    [WB Kluba](/openapi/work-with-products#tag/Ceny-i-skidki/paths/~1api~1v2~1upload~1task~1club-
    discount/post).
    <br><br>
    V odnom zaprose mozhno ukazat' bolee odnogo artikula.
    <br><br>
    Ispol'zujte otdel'nye metody, chtoby poluchit' informatsiju:
      - obo [vseh tovarah prodavtsa, ne ukazyvaja artikuly](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1list~1goods~1filter/get)
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
        body (PostApiV2ListGoodsFilterBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostApiV2ListGoodsFilterResponse200 | PostApiV2ListGoodsFilterResponse401 | PostApiV2ListGoodsFilterResponse429 | ResponseError]
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
    body: PostApiV2ListGoodsFilterBody,
) -> (
    PostApiV2ListGoodsFilterResponse200
    | PostApiV2ListGoodsFilterResponse401
    | PostApiV2ListGoodsFilterResponse429
    | ResponseError
    | None
):
    r"""Poluchit' tovary s tsenami po artikulam

     Metod vozvraschaet informatsiju o tovarah po ih artikulam: tseny, valjutu, obschie skidki i skidki
    [WB Kluba](/openapi/work-with-products#tag/Ceny-i-skidki/paths/~1api~1v2~1upload~1task~1club-
    discount/post).
    <br><br>
    V odnom zaprose mozhno ukazat' bolee odnogo artikula.
    <br><br>
    Ispol'zujte otdel'nye metody, chtoby poluchit' informatsiju:
      - obo [vseh tovarah prodavtsa, ne ukazyvaja artikuly](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1list~1goods~1filter/get)
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
        body (PostApiV2ListGoodsFilterBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostApiV2ListGoodsFilterResponse200 | PostApiV2ListGoodsFilterResponse401 | PostApiV2ListGoodsFilterResponse429 | ResponseError
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PostApiV2ListGoodsFilterBody,
) -> Response[
    PostApiV2ListGoodsFilterResponse200
    | PostApiV2ListGoodsFilterResponse401
    | PostApiV2ListGoodsFilterResponse429
    | ResponseError
]:
    r"""Poluchit' tovary s tsenami po artikulam

     Metod vozvraschaet informatsiju o tovarah po ih artikulam: tseny, valjutu, obschie skidki i skidki
    [WB Kluba](/openapi/work-with-products#tag/Ceny-i-skidki/paths/~1api~1v2~1upload~1task~1club-
    discount/post).
    <br><br>
    V odnom zaprose mozhno ukazat' bolee odnogo artikula.
    <br><br>
    Ispol'zujte otdel'nye metody, chtoby poluchit' informatsiju:
      - obo [vseh tovarah prodavtsa, ne ukazyvaja artikuly](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1list~1goods~1filter/get)
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
        body (PostApiV2ListGoodsFilterBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostApiV2ListGoodsFilterResponse200 | PostApiV2ListGoodsFilterResponse401 | PostApiV2ListGoodsFilterResponse429 | ResponseError]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: PostApiV2ListGoodsFilterBody,
) -> (
    PostApiV2ListGoodsFilterResponse200
    | PostApiV2ListGoodsFilterResponse401
    | PostApiV2ListGoodsFilterResponse429
    | ResponseError
    | None
):
    r"""Poluchit' tovary s tsenami po artikulam

     Metod vozvraschaet informatsiju o tovarah po ih artikulam: tseny, valjutu, obschie skidki i skidki
    [WB Kluba](/openapi/work-with-products#tag/Ceny-i-skidki/paths/~1api~1v2~1upload~1task~1club-
    discount/post).
    <br><br>
    V odnom zaprose mozhno ukazat' bolee odnogo artikula.
    <br><br>
    Ispol'zujte otdel'nye metody, chtoby poluchit' informatsiju:
      - obo [vseh tovarah prodavtsa, ne ukazyvaja artikuly](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1list~1goods~1filter/get)
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
        body (PostApiV2ListGoodsFilterBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostApiV2ListGoodsFilterResponse200 | PostApiV2ListGoodsFilterResponse401 | PostApiV2ListGoodsFilterResponse429 | ResponseError
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
