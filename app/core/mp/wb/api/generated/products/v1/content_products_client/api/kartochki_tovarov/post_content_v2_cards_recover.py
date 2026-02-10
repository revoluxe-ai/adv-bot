from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_content_v2_cards_recover_body import PostContentV2CardsRecoverBody
from ...models.post_content_v2_cards_recover_response_200 import (
    PostContentV2CardsRecoverResponse200,
)
from ...models.post_content_v2_cards_recover_response_401 import (
    PostContentV2CardsRecoverResponse401,
)
from ...models.post_content_v2_cards_recover_response_429 import (
    PostContentV2CardsRecoverResponse429,
)
from ...models.response_body_content_error_400 import ResponseBodyContentError400
from ...models.response_body_content_error_403 import ResponseBodyContentError403
from ...types import Response


def _get_kwargs(
    *,
    body: PostContentV2CardsRecoverBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/content/v2/cards/recover",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    PostContentV2CardsRecoverResponse200
    | PostContentV2CardsRecoverResponse401
    | PostContentV2CardsRecoverResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
    | None
):
    if response.status_code == 200:
        response_200 = PostContentV2CardsRecoverResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = ResponseBodyContentError400.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostContentV2CardsRecoverResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = ResponseBodyContentError403.from_dict(response.json())

        return response_403

    if response.status_code == 429:
        response_429 = PostContentV2CardsRecoverResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    PostContentV2CardsRecoverResponse200
    | PostContentV2CardsRecoverResponse401
    | PostContentV2CardsRecoverResponse429
    | ResponseBodyContentError400
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
    body: PostContentV2CardsRecoverBody,
) -> Response[
    PostContentV2CardsRecoverResponse200
    | PostContentV2CardsRecoverResponse401
    | PostContentV2CardsRecoverResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
]:
    r"""Vosstanovlenie kartochek tovarov iz korziny

     Metod vosstanavlivaet [kartochki tovarov iz korziny](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1trash/post).

    <div class=\"description_important\">
      Kartochka tovara sohranjaet tot zhe <code>imtID</code> — ID dlja <a
    href=\"https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-kartochek-
    tovarov\">ob'edinennyh</a> kartochek tovarov — chto byl prisvoen ej pri <a href=\"/openapi/work-
    with-products#tag/Kartochki-tovarov/paths/~1content~1v2~1cards~1delete~1trash/post\">peremeschenii v
    korzinu</a>
    </div>

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

    Args:
        body (PostContentV2CardsRecoverBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostContentV2CardsRecoverResponse200 | PostContentV2CardsRecoverResponse401 | PostContentV2CardsRecoverResponse429 | ResponseBodyContentError400 | ResponseBodyContentError403]
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
    body: PostContentV2CardsRecoverBody,
) -> (
    PostContentV2CardsRecoverResponse200
    | PostContentV2CardsRecoverResponse401
    | PostContentV2CardsRecoverResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
    | None
):
    r"""Vosstanovlenie kartochek tovarov iz korziny

     Metod vosstanavlivaet [kartochki tovarov iz korziny](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1trash/post).

    <div class=\"description_important\">
      Kartochka tovara sohranjaet tot zhe <code>imtID</code> — ID dlja <a
    href=\"https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-kartochek-
    tovarov\">ob'edinennyh</a> kartochek tovarov — chto byl prisvoen ej pri <a href=\"/openapi/work-
    with-products#tag/Kartochki-tovarov/paths/~1content~1v2~1cards~1delete~1trash/post\">peremeschenii v
    korzinu</a>
    </div>

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

    Args:
        body (PostContentV2CardsRecoverBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostContentV2CardsRecoverResponse200 | PostContentV2CardsRecoverResponse401 | PostContentV2CardsRecoverResponse429 | ResponseBodyContentError400 | ResponseBodyContentError403
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PostContentV2CardsRecoverBody,
) -> Response[
    PostContentV2CardsRecoverResponse200
    | PostContentV2CardsRecoverResponse401
    | PostContentV2CardsRecoverResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
]:
    r"""Vosstanovlenie kartochek tovarov iz korziny

     Metod vosstanavlivaet [kartochki tovarov iz korziny](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1trash/post).

    <div class=\"description_important\">
      Kartochka tovara sohranjaet tot zhe <code>imtID</code> — ID dlja <a
    href=\"https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-kartochek-
    tovarov\">ob'edinennyh</a> kartochek tovarov — chto byl prisvoen ej pri <a href=\"/openapi/work-
    with-products#tag/Kartochki-tovarov/paths/~1content~1v2~1cards~1delete~1trash/post\">peremeschenii v
    korzinu</a>
    </div>

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

    Args:
        body (PostContentV2CardsRecoverBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostContentV2CardsRecoverResponse200 | PostContentV2CardsRecoverResponse401 | PostContentV2CardsRecoverResponse429 | ResponseBodyContentError400 | ResponseBodyContentError403]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: PostContentV2CardsRecoverBody,
) -> (
    PostContentV2CardsRecoverResponse200
    | PostContentV2CardsRecoverResponse401
    | PostContentV2CardsRecoverResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
    | None
):
    r"""Vosstanovlenie kartochek tovarov iz korziny

     Metod vosstanavlivaet [kartochki tovarov iz korziny](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1trash/post).

    <div class=\"description_important\">
      Kartochka tovara sohranjaet tot zhe <code>imtID</code> — ID dlja <a
    href=\"https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-kartochek-
    tovarov\">ob'edinennyh</a> kartochek tovarov — chto byl prisvoen ej pri <a href=\"/openapi/work-
    with-products#tag/Kartochki-tovarov/paths/~1content~1v2~1cards~1delete~1trash/post\">peremeschenii v
    korzinu</a>
    </div>

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

    Args:
        body (PostContentV2CardsRecoverBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostContentV2CardsRecoverResponse200 | PostContentV2CardsRecoverResponse401 | PostContentV2CardsRecoverResponse429 | ResponseBodyContentError400 | ResponseBodyContentError403
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
