from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_content_v2_cards_limits_response_200 import (
    GetContentV2CardsLimitsResponse200,
)
from ...models.get_content_v2_cards_limits_response_401 import (
    GetContentV2CardsLimitsResponse401,
)
from ...models.get_content_v2_cards_limits_response_429 import (
    GetContentV2CardsLimitsResponse429,
)
from ...models.response_body_content_error_403 import ResponseBodyContentError403
from ...types import Response


def _get_kwargs() -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/content/v2/cards/limits",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    GetContentV2CardsLimitsResponse200
    | GetContentV2CardsLimitsResponse401
    | GetContentV2CardsLimitsResponse429
    | ResponseBodyContentError403
    | None
):
    if response.status_code == 200:
        response_200 = GetContentV2CardsLimitsResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = GetContentV2CardsLimitsResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = ResponseBodyContentError403.from_dict(response.json())

        return response_403

    if response.status_code == 429:
        response_429 = GetContentV2CardsLimitsResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    GetContentV2CardsLimitsResponse200
    | GetContentV2CardsLimitsResponse401
    | GetContentV2CardsLimitsResponse429
    | ResponseBodyContentError403
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
    GetContentV2CardsLimitsResponse200
    | GetContentV2CardsLimitsResponse401
    | GetContentV2CardsLimitsResponse429
    | ResponseBodyContentError403
]:
    r"""Limity kartochek tovarov

     Vozvraschaet besplatnye i platnye limity prodavtsa na [sozdanie kartochek tovarov](/openapi/work-
    with-products#tag/Sozdanie-kartochek-tovarov/paths/~1content~1v2~1cards~1upload/post).<br><br>

    Formula dlja poluchenija kolichestva kartochek, kotorye mozhno sozdat':

    > (`freeLimits` + `paidLimits`) - kolichestvo sozdannyh kartochek

    Sozdannymi schitajutsja kartochki, kotorye mozhno poluchit' cherez metody [spisok kartochek
    tovarov](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1list/post) i [spisok kartochek tovarov v
    korzine](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1trash/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Kontent</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 100 zaprosov | 600 ms | 5 zaprosov |

    Iskljuchenie — metody:

    <ul>
        <li><a href=\"/openapi/work-with-products#tag/Sozdanie-kartochek-
    tovarov/paths/~1content~1v2~1cards~1upload/post\">sozdanija kartochek tovarov</a></li>
        <li><a href=\"/openapi/work-with-products#tag/Sozdanie-kartochek-
    tovarov/paths/~1content~1v2~1cards~1upload~1add/post\">sozdanija kartochek tovarov s
    prisoedineniem</a></li>
        <li><a href=\"/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1update/post\">redaktirovanija kartochek tovarov</a></li>
        <li><a href=\"/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1error~1list/post\">poluchenija nesozdannyh kartochek tovarov s
    oshibkami</a></li>
    </ul>
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetContentV2CardsLimitsResponse200 | GetContentV2CardsLimitsResponse401 | GetContentV2CardsLimitsResponse429 | ResponseBodyContentError403]
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
    GetContentV2CardsLimitsResponse200
    | GetContentV2CardsLimitsResponse401
    | GetContentV2CardsLimitsResponse429
    | ResponseBodyContentError403
    | None
):
    r"""Limity kartochek tovarov

     Vozvraschaet besplatnye i platnye limity prodavtsa na [sozdanie kartochek tovarov](/openapi/work-
    with-products#tag/Sozdanie-kartochek-tovarov/paths/~1content~1v2~1cards~1upload/post).<br><br>

    Formula dlja poluchenija kolichestva kartochek, kotorye mozhno sozdat':

    > (`freeLimits` + `paidLimits`) - kolichestvo sozdannyh kartochek

    Sozdannymi schitajutsja kartochki, kotorye mozhno poluchit' cherez metody [spisok kartochek
    tovarov](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1list/post) i [spisok kartochek tovarov v
    korzine](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1trash/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Kontent</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 100 zaprosov | 600 ms | 5 zaprosov |

    Iskljuchenie — metody:

    <ul>
        <li><a href=\"/openapi/work-with-products#tag/Sozdanie-kartochek-
    tovarov/paths/~1content~1v2~1cards~1upload/post\">sozdanija kartochek tovarov</a></li>
        <li><a href=\"/openapi/work-with-products#tag/Sozdanie-kartochek-
    tovarov/paths/~1content~1v2~1cards~1upload~1add/post\">sozdanija kartochek tovarov s
    prisoedineniem</a></li>
        <li><a href=\"/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1update/post\">redaktirovanija kartochek tovarov</a></li>
        <li><a href=\"/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1error~1list/post\">poluchenija nesozdannyh kartochek tovarov s
    oshibkami</a></li>
    </ul>
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetContentV2CardsLimitsResponse200 | GetContentV2CardsLimitsResponse401 | GetContentV2CardsLimitsResponse429 | ResponseBodyContentError403
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
) -> Response[
    GetContentV2CardsLimitsResponse200
    | GetContentV2CardsLimitsResponse401
    | GetContentV2CardsLimitsResponse429
    | ResponseBodyContentError403
]:
    r"""Limity kartochek tovarov

     Vozvraschaet besplatnye i platnye limity prodavtsa na [sozdanie kartochek tovarov](/openapi/work-
    with-products#tag/Sozdanie-kartochek-tovarov/paths/~1content~1v2~1cards~1upload/post).<br><br>

    Formula dlja poluchenija kolichestva kartochek, kotorye mozhno sozdat':

    > (`freeLimits` + `paidLimits`) - kolichestvo sozdannyh kartochek

    Sozdannymi schitajutsja kartochki, kotorye mozhno poluchit' cherez metody [spisok kartochek
    tovarov](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1list/post) i [spisok kartochek tovarov v
    korzine](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1trash/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Kontent</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 100 zaprosov | 600 ms | 5 zaprosov |

    Iskljuchenie — metody:

    <ul>
        <li><a href=\"/openapi/work-with-products#tag/Sozdanie-kartochek-
    tovarov/paths/~1content~1v2~1cards~1upload/post\">sozdanija kartochek tovarov</a></li>
        <li><a href=\"/openapi/work-with-products#tag/Sozdanie-kartochek-
    tovarov/paths/~1content~1v2~1cards~1upload~1add/post\">sozdanija kartochek tovarov s
    prisoedineniem</a></li>
        <li><a href=\"/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1update/post\">redaktirovanija kartochek tovarov</a></li>
        <li><a href=\"/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1error~1list/post\">poluchenija nesozdannyh kartochek tovarov s
    oshibkami</a></li>
    </ul>
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetContentV2CardsLimitsResponse200 | GetContentV2CardsLimitsResponse401 | GetContentV2CardsLimitsResponse429 | ResponseBodyContentError403]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
) -> (
    GetContentV2CardsLimitsResponse200
    | GetContentV2CardsLimitsResponse401
    | GetContentV2CardsLimitsResponse429
    | ResponseBodyContentError403
    | None
):
    r"""Limity kartochek tovarov

     Vozvraschaet besplatnye i platnye limity prodavtsa na [sozdanie kartochek tovarov](/openapi/work-
    with-products#tag/Sozdanie-kartochek-tovarov/paths/~1content~1v2~1cards~1upload/post).<br><br>

    Formula dlja poluchenija kolichestva kartochek, kotorye mozhno sozdat':

    > (`freeLimits` + `paidLimits`) - kolichestvo sozdannyh kartochek

    Sozdannymi schitajutsja kartochki, kotorye mozhno poluchit' cherez metody [spisok kartochek
    tovarov](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1list/post) i [spisok kartochek tovarov v
    korzine](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1trash/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Kontent</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 100 zaprosov | 600 ms | 5 zaprosov |

    Iskljuchenie — metody:

    <ul>
        <li><a href=\"/openapi/work-with-products#tag/Sozdanie-kartochek-
    tovarov/paths/~1content~1v2~1cards~1upload/post\">sozdanija kartochek tovarov</a></li>
        <li><a href=\"/openapi/work-with-products#tag/Sozdanie-kartochek-
    tovarov/paths/~1content~1v2~1cards~1upload~1add/post\">sozdanija kartochek tovarov s
    prisoedineniem</a></li>
        <li><a href=\"/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1update/post\">redaktirovanija kartochek tovarov</a></li>
        <li><a href=\"/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1error~1list/post\">poluchenija nesozdannyh kartochek tovarov s
    oshibkami</a></li>
    </ul>
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetContentV2CardsLimitsResponse200 | GetContentV2CardsLimitsResponse401 | GetContentV2CardsLimitsResponse429 | ResponseBodyContentError403
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
