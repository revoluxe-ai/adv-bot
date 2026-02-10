from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_content_v2_get_cards_list_body import PostContentV2GetCardsListBody
from ...models.post_content_v2_get_cards_list_response_200 import (
    PostContentV2GetCardsListResponse200,
)
from ...models.post_content_v2_get_cards_list_response_401 import (
    PostContentV2GetCardsListResponse401,
)
from ...models.post_content_v2_get_cards_list_response_429 import (
    PostContentV2GetCardsListResponse429,
)
from ...models.response_body_content_error_400 import ResponseBodyContentError400
from ...models.response_body_content_error_403 import ResponseBodyContentError403
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    body: PostContentV2GetCardsListBody,
    locale: str | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    params["locale"] = locale

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/content/v2/get/cards/list",
        "params": params,
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    PostContentV2GetCardsListResponse200
    | PostContentV2GetCardsListResponse401
    | PostContentV2GetCardsListResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
    | None
):
    if response.status_code == 200:
        response_200 = PostContentV2GetCardsListResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = ResponseBodyContentError400.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostContentV2GetCardsListResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = ResponseBodyContentError403.from_dict(response.json())

        return response_403

    if response.status_code == 429:
        response_429 = PostContentV2GetCardsListResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    PostContentV2GetCardsListResponse200
    | PostContentV2GetCardsListResponse401
    | PostContentV2GetCardsListResponse429
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
    body: PostContentV2GetCardsListBody,
    locale: str | Unset = UNSET,
) -> Response[
    PostContentV2GetCardsListResponse200
    | PostContentV2GetCardsListResponse401
    | PostContentV2GetCardsListResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
]:
    r"""Spisok kartochek tovarov

     <div class=\"description_auth\">
      Metod dostupen po <a href=\"/openapi/api-information#tag/Avtorizaciya/Kak-sozdat-personalnyj-
    bazovyj-ili-testovyj-token\">tokenu</a> s kategoriej <strong>Kontent</strong> ili
    <strong>Prodvizhenie</strong>
    </div>

    Metod vozvraschaet spisok sozdannyh kartochek tovarov.

    <div class=\"description_important\">
      V otvete metoda ne budet kartochek, nahodjaschihsja v korzine. Poluchit' takie kartochki mozhno
    cherez <a href=\"/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1trash/post\">otdel'nyj metod</a>
    </div>

    Chtoby poluchit' **bol'she 100** kartochek tovarov, ispol'zujte paginatsiju:
      1. Sdelajte pervyj zapros: <br>
          <pre style=\"background-color: rgb(38 50 56 / 5%); color: #e53935\">
            {
              \"settings\": {
                \"sort\": {
                  \"ascending\": true
                },
                \"cursor\": {
                  \"limit\": 100
                },
                \"filter\": {
                  \"withPhoto\": -1
                }
              }
            }</pre>
         Chtoby posle vygruzki poluchat' tol'ko novye ili obnovlennye kartochki tovarov, ispol'zujte
    sortirovku po vozrastaniju: `\"sort\":{\"ascending\":true}`.
      2. Skopirujte `\"updatedAt\":\"***\",\"nmID\":\"***\"` iz `cursor` otveta i vstav'te v `cursor`
    zaprosa.
      3. Povtorite zapros.
      4. Povtorjajte punkty 2 i 3, poka znachenie `total` v otvete ne stanet men'she, chem znachenie
    `limit` v zaprose. Eto budet oznachat', chto vy poluchili vse kartochki.

    Chtoby poluchat' tol'ko kartochki tovarov, kotorye byli sozdany ili obnovleny posle predyduschej
    vygruzki dannyh:
      1. Sohranite polja `\"cursor\":{\"updatedAt\":\"***\",\"nmID\":\"***\"}` iz poslednego otveta
    predyduschej vygruzki. Pri vygruzke ispol'zujte sortirovku po vozrastaniju:
    `\"sort\":{\"ascending\":true}`.
      2. Ukazhite v pervom zaprose sohranennye polja
    `\"cursor\":{\"updatedAt\":\"***\",\"nmID\":\"***\"}`. Prodolzhajte ispol'zovat' sortirovku po
    vozrastaniju.
      3. Sohranite polja `\"cursor\":{\"updatedAt\":\"***\",\"nmID\":\"***\"}` iz poslednego otveta
    tekuschej vygruzki.

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
        locale (str | Unset):  Example: ru.
        body (PostContentV2GetCardsListBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostContentV2GetCardsListResponse200 | PostContentV2GetCardsListResponse401 | PostContentV2GetCardsListResponse429 | ResponseBodyContentError400 | ResponseBodyContentError403]
    """

    kwargs = _get_kwargs(
        body=body,
        locale=locale,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    body: PostContentV2GetCardsListBody,
    locale: str | Unset = UNSET,
) -> (
    PostContentV2GetCardsListResponse200
    | PostContentV2GetCardsListResponse401
    | PostContentV2GetCardsListResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
    | None
):
    r"""Spisok kartochek tovarov

     <div class=\"description_auth\">
      Metod dostupen po <a href=\"/openapi/api-information#tag/Avtorizaciya/Kak-sozdat-personalnyj-
    bazovyj-ili-testovyj-token\">tokenu</a> s kategoriej <strong>Kontent</strong> ili
    <strong>Prodvizhenie</strong>
    </div>

    Metod vozvraschaet spisok sozdannyh kartochek tovarov.

    <div class=\"description_important\">
      V otvete metoda ne budet kartochek, nahodjaschihsja v korzine. Poluchit' takie kartochki mozhno
    cherez <a href=\"/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1trash/post\">otdel'nyj metod</a>
    </div>

    Chtoby poluchit' **bol'she 100** kartochek tovarov, ispol'zujte paginatsiju:
      1. Sdelajte pervyj zapros: <br>
          <pre style=\"background-color: rgb(38 50 56 / 5%); color: #e53935\">
            {
              \"settings\": {
                \"sort\": {
                  \"ascending\": true
                },
                \"cursor\": {
                  \"limit\": 100
                },
                \"filter\": {
                  \"withPhoto\": -1
                }
              }
            }</pre>
         Chtoby posle vygruzki poluchat' tol'ko novye ili obnovlennye kartochki tovarov, ispol'zujte
    sortirovku po vozrastaniju: `\"sort\":{\"ascending\":true}`.
      2. Skopirujte `\"updatedAt\":\"***\",\"nmID\":\"***\"` iz `cursor` otveta i vstav'te v `cursor`
    zaprosa.
      3. Povtorite zapros.
      4. Povtorjajte punkty 2 i 3, poka znachenie `total` v otvete ne stanet men'she, chem znachenie
    `limit` v zaprose. Eto budet oznachat', chto vy poluchili vse kartochki.

    Chtoby poluchat' tol'ko kartochki tovarov, kotorye byli sozdany ili obnovleny posle predyduschej
    vygruzki dannyh:
      1. Sohranite polja `\"cursor\":{\"updatedAt\":\"***\",\"nmID\":\"***\"}` iz poslednego otveta
    predyduschej vygruzki. Pri vygruzke ispol'zujte sortirovku po vozrastaniju:
    `\"sort\":{\"ascending\":true}`.
      2. Ukazhite v pervom zaprose sohranennye polja
    `\"cursor\":{\"updatedAt\":\"***\",\"nmID\":\"***\"}`. Prodolzhajte ispol'zovat' sortirovku po
    vozrastaniju.
      3. Sohranite polja `\"cursor\":{\"updatedAt\":\"***\",\"nmID\":\"***\"}` iz poslednego otveta
    tekuschej vygruzki.

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
        locale (str | Unset):  Example: ru.
        body (PostContentV2GetCardsListBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostContentV2GetCardsListResponse200 | PostContentV2GetCardsListResponse401 | PostContentV2GetCardsListResponse429 | ResponseBodyContentError400 | ResponseBodyContentError403
    """

    return sync_detailed(
        client=client,
        body=body,
        locale=locale,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PostContentV2GetCardsListBody,
    locale: str | Unset = UNSET,
) -> Response[
    PostContentV2GetCardsListResponse200
    | PostContentV2GetCardsListResponse401
    | PostContentV2GetCardsListResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
]:
    r"""Spisok kartochek tovarov

     <div class=\"description_auth\">
      Metod dostupen po <a href=\"/openapi/api-information#tag/Avtorizaciya/Kak-sozdat-personalnyj-
    bazovyj-ili-testovyj-token\">tokenu</a> s kategoriej <strong>Kontent</strong> ili
    <strong>Prodvizhenie</strong>
    </div>

    Metod vozvraschaet spisok sozdannyh kartochek tovarov.

    <div class=\"description_important\">
      V otvete metoda ne budet kartochek, nahodjaschihsja v korzine. Poluchit' takie kartochki mozhno
    cherez <a href=\"/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1trash/post\">otdel'nyj metod</a>
    </div>

    Chtoby poluchit' **bol'she 100** kartochek tovarov, ispol'zujte paginatsiju:
      1. Sdelajte pervyj zapros: <br>
          <pre style=\"background-color: rgb(38 50 56 / 5%); color: #e53935\">
            {
              \"settings\": {
                \"sort\": {
                  \"ascending\": true
                },
                \"cursor\": {
                  \"limit\": 100
                },
                \"filter\": {
                  \"withPhoto\": -1
                }
              }
            }</pre>
         Chtoby posle vygruzki poluchat' tol'ko novye ili obnovlennye kartochki tovarov, ispol'zujte
    sortirovku po vozrastaniju: `\"sort\":{\"ascending\":true}`.
      2. Skopirujte `\"updatedAt\":\"***\",\"nmID\":\"***\"` iz `cursor` otveta i vstav'te v `cursor`
    zaprosa.
      3. Povtorite zapros.
      4. Povtorjajte punkty 2 i 3, poka znachenie `total` v otvete ne stanet men'she, chem znachenie
    `limit` v zaprose. Eto budet oznachat', chto vy poluchili vse kartochki.

    Chtoby poluchat' tol'ko kartochki tovarov, kotorye byli sozdany ili obnovleny posle predyduschej
    vygruzki dannyh:
      1. Sohranite polja `\"cursor\":{\"updatedAt\":\"***\",\"nmID\":\"***\"}` iz poslednego otveta
    predyduschej vygruzki. Pri vygruzke ispol'zujte sortirovku po vozrastaniju:
    `\"sort\":{\"ascending\":true}`.
      2. Ukazhite v pervom zaprose sohranennye polja
    `\"cursor\":{\"updatedAt\":\"***\",\"nmID\":\"***\"}`. Prodolzhajte ispol'zovat' sortirovku po
    vozrastaniju.
      3. Sohranite polja `\"cursor\":{\"updatedAt\":\"***\",\"nmID\":\"***\"}` iz poslednego otveta
    tekuschej vygruzki.

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
        locale (str | Unset):  Example: ru.
        body (PostContentV2GetCardsListBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostContentV2GetCardsListResponse200 | PostContentV2GetCardsListResponse401 | PostContentV2GetCardsListResponse429 | ResponseBodyContentError400 | ResponseBodyContentError403]
    """

    kwargs = _get_kwargs(
        body=body,
        locale=locale,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: PostContentV2GetCardsListBody,
    locale: str | Unset = UNSET,
) -> (
    PostContentV2GetCardsListResponse200
    | PostContentV2GetCardsListResponse401
    | PostContentV2GetCardsListResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
    | None
):
    r"""Spisok kartochek tovarov

     <div class=\"description_auth\">
      Metod dostupen po <a href=\"/openapi/api-information#tag/Avtorizaciya/Kak-sozdat-personalnyj-
    bazovyj-ili-testovyj-token\">tokenu</a> s kategoriej <strong>Kontent</strong> ili
    <strong>Prodvizhenie</strong>
    </div>

    Metod vozvraschaet spisok sozdannyh kartochek tovarov.

    <div class=\"description_important\">
      V otvete metoda ne budet kartochek, nahodjaschihsja v korzine. Poluchit' takie kartochki mozhno
    cherez <a href=\"/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1trash/post\">otdel'nyj metod</a>
    </div>

    Chtoby poluchit' **bol'she 100** kartochek tovarov, ispol'zujte paginatsiju:
      1. Sdelajte pervyj zapros: <br>
          <pre style=\"background-color: rgb(38 50 56 / 5%); color: #e53935\">
            {
              \"settings\": {
                \"sort\": {
                  \"ascending\": true
                },
                \"cursor\": {
                  \"limit\": 100
                },
                \"filter\": {
                  \"withPhoto\": -1
                }
              }
            }</pre>
         Chtoby posle vygruzki poluchat' tol'ko novye ili obnovlennye kartochki tovarov, ispol'zujte
    sortirovku po vozrastaniju: `\"sort\":{\"ascending\":true}`.
      2. Skopirujte `\"updatedAt\":\"***\",\"nmID\":\"***\"` iz `cursor` otveta i vstav'te v `cursor`
    zaprosa.
      3. Povtorite zapros.
      4. Povtorjajte punkty 2 i 3, poka znachenie `total` v otvete ne stanet men'she, chem znachenie
    `limit` v zaprose. Eto budet oznachat', chto vy poluchili vse kartochki.

    Chtoby poluchat' tol'ko kartochki tovarov, kotorye byli sozdany ili obnovleny posle predyduschej
    vygruzki dannyh:
      1. Sohranite polja `\"cursor\":{\"updatedAt\":\"***\",\"nmID\":\"***\"}` iz poslednego otveta
    predyduschej vygruzki. Pri vygruzke ispol'zujte sortirovku po vozrastaniju:
    `\"sort\":{\"ascending\":true}`.
      2. Ukazhite v pervom zaprose sohranennye polja
    `\"cursor\":{\"updatedAt\":\"***\",\"nmID\":\"***\"}`. Prodolzhajte ispol'zovat' sortirovku po
    vozrastaniju.
      3. Sohranite polja `\"cursor\":{\"updatedAt\":\"***\",\"nmID\":\"***\"}` iz poslednego otveta
    tekuschej vygruzki.

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
        locale (str | Unset):  Example: ru.
        body (PostContentV2GetCardsListBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostContentV2GetCardsListResponse200 | PostContentV2GetCardsListResponse401 | PostContentV2GetCardsListResponse429 | ResponseBodyContentError400 | ResponseBodyContentError403
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            locale=locale,
        )
    ).parsed
