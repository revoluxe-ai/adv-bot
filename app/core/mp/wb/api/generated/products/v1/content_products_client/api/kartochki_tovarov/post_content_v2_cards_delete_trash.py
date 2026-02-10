from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_content_v2_cards_delete_trash_body import (
    PostContentV2CardsDeleteTrashBody,
)
from ...models.post_content_v2_cards_delete_trash_response_200 import (
    PostContentV2CardsDeleteTrashResponse200,
)
from ...models.post_content_v2_cards_delete_trash_response_401 import (
    PostContentV2CardsDeleteTrashResponse401,
)
from ...models.post_content_v2_cards_delete_trash_response_429 import (
    PostContentV2CardsDeleteTrashResponse429,
)
from ...models.response_body_content_error_400 import ResponseBodyContentError400
from ...models.response_body_content_error_403 import ResponseBodyContentError403
from ...types import Response


def _get_kwargs(
    *,
    body: PostContentV2CardsDeleteTrashBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/content/v2/cards/delete/trash",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    PostContentV2CardsDeleteTrashResponse200
    | PostContentV2CardsDeleteTrashResponse401
    | PostContentV2CardsDeleteTrashResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
    | None
):
    if response.status_code == 200:
        response_200 = PostContentV2CardsDeleteTrashResponse200.from_dict(
            response.json()
        )

        return response_200

    if response.status_code == 400:
        response_400 = ResponseBodyContentError400.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostContentV2CardsDeleteTrashResponse401.from_dict(
            response.json()
        )

        return response_401

    if response.status_code == 403:
        response_403 = ResponseBodyContentError403.from_dict(response.json())

        return response_403

    if response.status_code == 429:
        response_429 = PostContentV2CardsDeleteTrashResponse429.from_dict(
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
    PostContentV2CardsDeleteTrashResponse200
    | PostContentV2CardsDeleteTrashResponse401
    | PostContentV2CardsDeleteTrashResponse429
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
    body: PostContentV2CardsDeleteTrashBody,
) -> Response[
    PostContentV2CardsDeleteTrashResponse200
    | PostContentV2CardsDeleteTrashResponse401
    | PostContentV2CardsDeleteTrashResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
]:
    r"""Perenos kartochek tovarov v korzinu

     Metod perenosit [kartochki tovarov v korzinu](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1trash/post). Pri etom kartochki tovarov ne udaljajutsja, ih
    mozhno [vosstanovit'](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1recover/post).

    <div class=\"description_important\">
      Posle perenosa v korzinu kartochke tovara prisvaivaetsja novyj <code>imtID</code> — ID dlja <a
    href=\"https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-kartochek-
    tovarov\">ob'edinennyh</a> kartochek tovarov
    </div>

    Kartochki tovarov udaljajutsja avtomaticheski, esli lezhat v korzine bol'she 30 dnej, i na nih net
    ostatkov. Ochistka korziny proishodit kazhduju noch' po moskovskomu vremeni.<br>
    Kartochki tovarov mozhno udalit' v ljuboe vremja v [lichnom
    kabinete](https://seller.wildberries.ru/new-goods/basket-cards).
    <br><br>
    Kartochka budet prodavat'sja, poka po nej est' ostatki na sklade, dazhe esli ee peremestili v
    korzinu. Chtoby polnost'ju snjat' kartochku s prodazhi, obnulite ostatki.

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
        body (PostContentV2CardsDeleteTrashBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostContentV2CardsDeleteTrashResponse200 | PostContentV2CardsDeleteTrashResponse401 | PostContentV2CardsDeleteTrashResponse429 | ResponseBodyContentError400 | ResponseBodyContentError403]
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
    body: PostContentV2CardsDeleteTrashBody,
) -> (
    PostContentV2CardsDeleteTrashResponse200
    | PostContentV2CardsDeleteTrashResponse401
    | PostContentV2CardsDeleteTrashResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
    | None
):
    r"""Perenos kartochek tovarov v korzinu

     Metod perenosit [kartochki tovarov v korzinu](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1trash/post). Pri etom kartochki tovarov ne udaljajutsja, ih
    mozhno [vosstanovit'](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1recover/post).

    <div class=\"description_important\">
      Posle perenosa v korzinu kartochke tovara prisvaivaetsja novyj <code>imtID</code> — ID dlja <a
    href=\"https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-kartochek-
    tovarov\">ob'edinennyh</a> kartochek tovarov
    </div>

    Kartochki tovarov udaljajutsja avtomaticheski, esli lezhat v korzine bol'she 30 dnej, i na nih net
    ostatkov. Ochistka korziny proishodit kazhduju noch' po moskovskomu vremeni.<br>
    Kartochki tovarov mozhno udalit' v ljuboe vremja v [lichnom
    kabinete](https://seller.wildberries.ru/new-goods/basket-cards).
    <br><br>
    Kartochka budet prodavat'sja, poka po nej est' ostatki na sklade, dazhe esli ee peremestili v
    korzinu. Chtoby polnost'ju snjat' kartochku s prodazhi, obnulite ostatki.

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
        body (PostContentV2CardsDeleteTrashBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostContentV2CardsDeleteTrashResponse200 | PostContentV2CardsDeleteTrashResponse401 | PostContentV2CardsDeleteTrashResponse429 | ResponseBodyContentError400 | ResponseBodyContentError403
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PostContentV2CardsDeleteTrashBody,
) -> Response[
    PostContentV2CardsDeleteTrashResponse200
    | PostContentV2CardsDeleteTrashResponse401
    | PostContentV2CardsDeleteTrashResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
]:
    r"""Perenos kartochek tovarov v korzinu

     Metod perenosit [kartochki tovarov v korzinu](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1trash/post). Pri etom kartochki tovarov ne udaljajutsja, ih
    mozhno [vosstanovit'](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1recover/post).

    <div class=\"description_important\">
      Posle perenosa v korzinu kartochke tovara prisvaivaetsja novyj <code>imtID</code> — ID dlja <a
    href=\"https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-kartochek-
    tovarov\">ob'edinennyh</a> kartochek tovarov
    </div>

    Kartochki tovarov udaljajutsja avtomaticheski, esli lezhat v korzine bol'she 30 dnej, i na nih net
    ostatkov. Ochistka korziny proishodit kazhduju noch' po moskovskomu vremeni.<br>
    Kartochki tovarov mozhno udalit' v ljuboe vremja v [lichnom
    kabinete](https://seller.wildberries.ru/new-goods/basket-cards).
    <br><br>
    Kartochka budet prodavat'sja, poka po nej est' ostatki na sklade, dazhe esli ee peremestili v
    korzinu. Chtoby polnost'ju snjat' kartochku s prodazhi, obnulite ostatki.

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
        body (PostContentV2CardsDeleteTrashBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostContentV2CardsDeleteTrashResponse200 | PostContentV2CardsDeleteTrashResponse401 | PostContentV2CardsDeleteTrashResponse429 | ResponseBodyContentError400 | ResponseBodyContentError403]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: PostContentV2CardsDeleteTrashBody,
) -> (
    PostContentV2CardsDeleteTrashResponse200
    | PostContentV2CardsDeleteTrashResponse401
    | PostContentV2CardsDeleteTrashResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
    | None
):
    r"""Perenos kartochek tovarov v korzinu

     Metod perenosit [kartochki tovarov v korzinu](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1trash/post). Pri etom kartochki tovarov ne udaljajutsja, ih
    mozhno [vosstanovit'](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1recover/post).

    <div class=\"description_important\">
      Posle perenosa v korzinu kartochke tovara prisvaivaetsja novyj <code>imtID</code> — ID dlja <a
    href=\"https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-kartochek-
    tovarov\">ob'edinennyh</a> kartochek tovarov
    </div>

    Kartochki tovarov udaljajutsja avtomaticheski, esli lezhat v korzine bol'she 30 dnej, i na nih net
    ostatkov. Ochistka korziny proishodit kazhduju noch' po moskovskomu vremeni.<br>
    Kartochki tovarov mozhno udalit' v ljuboe vremja v [lichnom
    kabinete](https://seller.wildberries.ru/new-goods/basket-cards).
    <br><br>
    Kartochka budet prodavat'sja, poka po nej est' ostatki na sklade, dazhe esli ee peremestili v
    korzinu. Chtoby polnost'ju snjat' kartochku s prodazhi, obnulite ostatki.

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
        body (PostContentV2CardsDeleteTrashBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostContentV2CardsDeleteTrashResponse200 | PostContentV2CardsDeleteTrashResponse401 | PostContentV2CardsDeleteTrashResponse429 | ResponseBodyContentError400 | ResponseBodyContentError403
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
