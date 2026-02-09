from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_content_v2_cards_move_nm_response_401 import (
    PostContentV2CardsMoveNmResponse401,
)
from ...models.post_content_v2_cards_move_nm_response_429 import (
    PostContentV2CardsMoveNmResponse429,
)
from ...models.request_move_nms_imt_conn import RequestMoveNmsImtConn
from ...models.request_move_nms_imt_disconn import RequestMoveNmsImtDisconn
from ...models.response_card_create import ResponseCardCreate
from ...models.response_incorrect_date import ResponseIncorrectDate
from ...types import Response


def _get_kwargs(
    *,
    body: RequestMoveNmsImtConn | RequestMoveNmsImtDisconn,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/content/v2/cards/moveNm",
    }

    _kwargs["json"]: dict[str, Any]
    if isinstance(body, RequestMoveNmsImtConn):
        _kwargs["json"] = body.to_dict()
    else:
        _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    PostContentV2CardsMoveNmResponse401
    | PostContentV2CardsMoveNmResponse429
    | ResponseCardCreate
    | ResponseCardCreate
    | ResponseIncorrectDate
    | str
    | None
):
    if response.status_code == 200:
        response_200 = ResponseCardCreate.from_dict(response.json())

        return response_200

    if response.status_code == 400:

        def _parse_response_400(
            data: object,
        ) -> ResponseCardCreate | ResponseIncorrectDate:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_400_type_0 = ResponseCardCreate.from_dict(data)

                return response_400_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, dict):
                raise TypeError()
            response_400_type_1 = ResponseIncorrectDate.from_dict(data)

            return response_400_type_1

        response_400 = _parse_response_400(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostContentV2CardsMoveNmResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = ResponseCardCreate.from_dict(response.json())

        return response_403

    if response.status_code == 413:
        response_413 = cast(str, response.json())
        return response_413

    if response.status_code == 429:
        response_429 = PostContentV2CardsMoveNmResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    PostContentV2CardsMoveNmResponse401
    | PostContentV2CardsMoveNmResponse429
    | ResponseCardCreate
    | ResponseCardCreate
    | ResponseIncorrectDate
    | str
]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: RequestMoveNmsImtConn | RequestMoveNmsImtDisconn,
) -> Response[
    PostContentV2CardsMoveNmResponse401
    | PostContentV2CardsMoveNmResponse429
    | ResponseCardCreate
    | ResponseCardCreate
    | ResponseIncorrectDate
    | str
]:
    r"""Ob'edinenie i raz'edinenie kartochek tovarov

     Metod [ob'edinjaet i raz'edinjaet](https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-
    kartochek-tovarov) kartochki tovarov. Kartochki tovarov javljajutsja ob'edinennymi, esli u nih
    odinakovyj `imtID`.
    <br><br>
    Dlja ob'edinenija kartochek tovarov sdelajte zapros **s ukazaniem** `imtID`. Mozhno ob'edinjat' ne
    bolee 30 kartochek tovarov.<br>
    Dlja raz'edinenija kartochek tovarov sdelajte zapros **bez ukazanija** `imtID`. Dlja raz'edinennyh
    kartochek budut sgenerirovany novye `imtID`.
    <br><br>
    Esli vy raz'edinite odnovremenno neskol'ko kartochek tovarov, eti kartochki ob'edinjatsja v odnu i
    poluchat novyj `imtID`.<br>
    Chtoby prisvoit' kazhdoj kartochke tovara unikal'nyj `imtID`, neobhodimo peredavat' po odnoj
    kartochke tovara za zapros.<br>
    <br>
    Maksimal'nyj razmer zaprosa 10 Mb.

    <div class=\"description_important\">
      Ob'edinit' mozhno kartochki tovarov tol'ko v ramkah odnogo predmeta
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
        body (RequestMoveNmsImtConn | RequestMoveNmsImtDisconn):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostContentV2CardsMoveNmResponse401 | PostContentV2CardsMoveNmResponse429 | ResponseCardCreate | ResponseCardCreate | ResponseIncorrectDate | str]
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
    client: AuthenticatedClient | Client,
    body: RequestMoveNmsImtConn | RequestMoveNmsImtDisconn,
) -> (
    PostContentV2CardsMoveNmResponse401
    | PostContentV2CardsMoveNmResponse429
    | ResponseCardCreate
    | ResponseCardCreate
    | ResponseIncorrectDate
    | str
    | None
):
    r"""Ob'edinenie i raz'edinenie kartochek tovarov

     Metod [ob'edinjaet i raz'edinjaet](https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-
    kartochek-tovarov) kartochki tovarov. Kartochki tovarov javljajutsja ob'edinennymi, esli u nih
    odinakovyj `imtID`.
    <br><br>
    Dlja ob'edinenija kartochek tovarov sdelajte zapros **s ukazaniem** `imtID`. Mozhno ob'edinjat' ne
    bolee 30 kartochek tovarov.<br>
    Dlja raz'edinenija kartochek tovarov sdelajte zapros **bez ukazanija** `imtID`. Dlja raz'edinennyh
    kartochek budut sgenerirovany novye `imtID`.
    <br><br>
    Esli vy raz'edinite odnovremenno neskol'ko kartochek tovarov, eti kartochki ob'edinjatsja v odnu i
    poluchat novyj `imtID`.<br>
    Chtoby prisvoit' kazhdoj kartochke tovara unikal'nyj `imtID`, neobhodimo peredavat' po odnoj
    kartochke tovara za zapros.<br>
    <br>
    Maksimal'nyj razmer zaprosa 10 Mb.

    <div class=\"description_important\">
      Ob'edinit' mozhno kartochki tovarov tol'ko v ramkah odnogo predmeta
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
        body (RequestMoveNmsImtConn | RequestMoveNmsImtDisconn):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostContentV2CardsMoveNmResponse401 | PostContentV2CardsMoveNmResponse429 | ResponseCardCreate | ResponseCardCreate | ResponseIncorrectDate | str
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: RequestMoveNmsImtConn | RequestMoveNmsImtDisconn,
) -> Response[
    PostContentV2CardsMoveNmResponse401
    | PostContentV2CardsMoveNmResponse429
    | ResponseCardCreate
    | ResponseCardCreate
    | ResponseIncorrectDate
    | str
]:
    r"""Ob'edinenie i raz'edinenie kartochek tovarov

     Metod [ob'edinjaet i raz'edinjaet](https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-
    kartochek-tovarov) kartochki tovarov. Kartochki tovarov javljajutsja ob'edinennymi, esli u nih
    odinakovyj `imtID`.
    <br><br>
    Dlja ob'edinenija kartochek tovarov sdelajte zapros **s ukazaniem** `imtID`. Mozhno ob'edinjat' ne
    bolee 30 kartochek tovarov.<br>
    Dlja raz'edinenija kartochek tovarov sdelajte zapros **bez ukazanija** `imtID`. Dlja raz'edinennyh
    kartochek budut sgenerirovany novye `imtID`.
    <br><br>
    Esli vy raz'edinite odnovremenno neskol'ko kartochek tovarov, eti kartochki ob'edinjatsja v odnu i
    poluchat novyj `imtID`.<br>
    Chtoby prisvoit' kazhdoj kartochke tovara unikal'nyj `imtID`, neobhodimo peredavat' po odnoj
    kartochke tovara za zapros.<br>
    <br>
    Maksimal'nyj razmer zaprosa 10 Mb.

    <div class=\"description_important\">
      Ob'edinit' mozhno kartochki tovarov tol'ko v ramkah odnogo predmeta
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
        body (RequestMoveNmsImtConn | RequestMoveNmsImtDisconn):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostContentV2CardsMoveNmResponse401 | PostContentV2CardsMoveNmResponse429 | ResponseCardCreate | ResponseCardCreate | ResponseIncorrectDate | str]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: RequestMoveNmsImtConn | RequestMoveNmsImtDisconn,
) -> (
    PostContentV2CardsMoveNmResponse401
    | PostContentV2CardsMoveNmResponse429
    | ResponseCardCreate
    | ResponseCardCreate
    | ResponseIncorrectDate
    | str
    | None
):
    r"""Ob'edinenie i raz'edinenie kartochek tovarov

     Metod [ob'edinjaet i raz'edinjaet](https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-
    kartochek-tovarov) kartochki tovarov. Kartochki tovarov javljajutsja ob'edinennymi, esli u nih
    odinakovyj `imtID`.
    <br><br>
    Dlja ob'edinenija kartochek tovarov sdelajte zapros **s ukazaniem** `imtID`. Mozhno ob'edinjat' ne
    bolee 30 kartochek tovarov.<br>
    Dlja raz'edinenija kartochek tovarov sdelajte zapros **bez ukazanija** `imtID`. Dlja raz'edinennyh
    kartochek budut sgenerirovany novye `imtID`.
    <br><br>
    Esli vy raz'edinite odnovremenno neskol'ko kartochek tovarov, eti kartochki ob'edinjatsja v odnu i
    poluchat novyj `imtID`.<br>
    Chtoby prisvoit' kazhdoj kartochke tovara unikal'nyj `imtID`, neobhodimo peredavat' po odnoj
    kartochke tovara za zapros.<br>
    <br>
    Maksimal'nyj razmer zaprosa 10 Mb.

    <div class=\"description_important\">
      Ob'edinit' mozhno kartochki tovarov tol'ko v ramkah odnogo predmeta
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
        body (RequestMoveNmsImtConn | RequestMoveNmsImtDisconn):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostContentV2CardsMoveNmResponse401 | PostContentV2CardsMoveNmResponse429 | ResponseCardCreate | ResponseCardCreate | ResponseIncorrectDate | str
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
