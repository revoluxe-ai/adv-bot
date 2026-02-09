from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_content_v2_cards_update_body_item import (
    PostContentV2CardsUpdateBodyItem,
)
from ...models.post_content_v2_cards_update_response_401 import (
    PostContentV2CardsUpdateResponse401,
)
from ...models.post_content_v2_cards_update_response_413 import (
    PostContentV2CardsUpdateResponse413,
)
from ...models.post_content_v2_cards_update_response_429 import (
    PostContentV2CardsUpdateResponse429,
)
from ...models.response_body_content_error_400 import ResponseBodyContentError400
from ...models.response_body_content_error_403 import ResponseBodyContentError403
from ...models.response_card_create import ResponseCardCreate
from ...types import Response


def _get_kwargs(
    *,
    body: list[PostContentV2CardsUpdateBodyItem],
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/content/v2/cards/update",
    }

    _kwargs["json"] = []
    for body_item_data in body:
        body_item = body_item_data.to_dict()
        _kwargs["json"].append(body_item)

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    PostContentV2CardsUpdateResponse401
    | PostContentV2CardsUpdateResponse413
    | PostContentV2CardsUpdateResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
    | ResponseCardCreate
    | None
):
    if response.status_code == 200:
        response_200 = ResponseCardCreate.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = ResponseBodyContentError400.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostContentV2CardsUpdateResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = ResponseBodyContentError403.from_dict(response.json())

        return response_403

    if response.status_code == 413:
        response_413 = PostContentV2CardsUpdateResponse413.from_dict(response.json())

        return response_413

    if response.status_code == 429:
        response_429 = PostContentV2CardsUpdateResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    PostContentV2CardsUpdateResponse401
    | PostContentV2CardsUpdateResponse413
    | PostContentV2CardsUpdateResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
    | ResponseCardCreate
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
    body: list[PostContentV2CardsUpdateBodyItem],
) -> Response[
    PostContentV2CardsUpdateResponse401
    | PostContentV2CardsUpdateResponse413
    | PostContentV2CardsUpdateResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
    | ResponseCardCreate
]:
    r"""Redaktirovanie kartochek tovarov

     Metod obnovljaet dannye kartochek tovarov. Takzhe ispol'zujte ego, chtoby dobavljat' novye razmery.

    <div class=\"description_important\">
      Kartochka tovara perezapisyvaetsja pri obnovlenii. Poetomu v zaprose nuzhno peredat' v tom chisle
    te parametry kartochki, kotorye vy ne sobiraetes' obnovljat'. Ih znachenija mozhno poluchit' v <a
    href=\"/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1list/post\">spiske kartochek tovarov</a> i <a
    href=\"/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1trash/post\">spiske kartochek tovarov v korzine</a>.
    </div>

    S pomosch'ju etogo metoda nel'zja obnovljat' ili udaljat':
      - barkody razmerov tovara. Mozhno tol'ko dobavit' dopolnitel'nye barkody
      - parametry `photos`, `video` i `tags`
      - tseny tovarov. Tsenu mozhno zadat', tol'ko esli vy dobavljaete novye razmery

    Pri dobavlenii novogo razmera ukazhite ego tsenu cherez parametr `price`. Esli v zaprose ne ukazan
    `price`, tsena razmera budet `0` — v etom sluchae izmenit' ee mozhno budet s pomosch'ju metodov:
      - [Ustanovit' tseny i skidki](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1upload~1task/post), esli u [tovara](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1list~1goods~1filter/get) `\"editablePriceSize\":false`
      - [Ustanovit' tseny dlja razmerov](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1upload~1task~1size/post), esli u [tovara](/openapi/work-with-
    products#tag/Ceny-i-skidki/paths/~1api~1v2~1list~1goods~1filter/get) `\"editablePriceSize\":true`

    Gabarity tovarov mozhno ukazat' tol'ko v `santimetrah`, ves tovara s upakovkoj — v `kilogrammah`.
    <br><br>
    Odnim zaprosom mozhno otredaktirovat' maksimum 3000 kartochek tovarov (`nmID`). Maksimal'nyj razmer
    zaprosa 10 Mb.<br>
    Esli otvet `Uspeshno` (`200`), no kakie-to kartochki ne obnovilis', prover'te [spisok nesozdannyh
    kartochek tovarov](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1error~1list/post).<br>
    Sinhronizatsija dannyh s servisami mozhet zanimat' do 30 minut. V techenie etogo vremeni nevozmozhno
    dobavit' ostatki na sklady i nastroit' tseny. <br>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 10 zaprosov | 6 sek | 5 zaprosov |
    </div>

    Args:
        body (list[PostContentV2CardsUpdateBodyItem]):  Example: [{'nmID': 11111111, 'vendorCode':
            'wbiz72wmro', 'brand': '', 'title': 'Sviter zhenskij oversajz s gorlom', 'description':
            '12345', 'dimensions': {'length': 35, 'width': 40, 'height': 15, 'weightBrutto': 3},
            'characteristics': [{'id': 14177450, 'value': ['hlopok 50% akril 50%']}, {'id': 50,
            'value': ['svobodnyj kroj']}], 'sizes': [{'chrtID': 12345678, 'techSize': 'ONE SIZE',
            'wbSize': '78-90', 'skus': ['123487653460134']}]}].

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostContentV2CardsUpdateResponse401 | PostContentV2CardsUpdateResponse413 | PostContentV2CardsUpdateResponse429 | ResponseBodyContentError400 | ResponseBodyContentError403 | ResponseCardCreate]
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
    body: list[PostContentV2CardsUpdateBodyItem],
) -> (
    PostContentV2CardsUpdateResponse401
    | PostContentV2CardsUpdateResponse413
    | PostContentV2CardsUpdateResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
    | ResponseCardCreate
    | None
):
    r"""Redaktirovanie kartochek tovarov

     Metod obnovljaet dannye kartochek tovarov. Takzhe ispol'zujte ego, chtoby dobavljat' novye razmery.

    <div class=\"description_important\">
      Kartochka tovara perezapisyvaetsja pri obnovlenii. Poetomu v zaprose nuzhno peredat' v tom chisle
    te parametry kartochki, kotorye vy ne sobiraetes' obnovljat'. Ih znachenija mozhno poluchit' v <a
    href=\"/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1list/post\">spiske kartochek tovarov</a> i <a
    href=\"/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1trash/post\">spiske kartochek tovarov v korzine</a>.
    </div>

    S pomosch'ju etogo metoda nel'zja obnovljat' ili udaljat':
      - barkody razmerov tovara. Mozhno tol'ko dobavit' dopolnitel'nye barkody
      - parametry `photos`, `video` i `tags`
      - tseny tovarov. Tsenu mozhno zadat', tol'ko esli vy dobavljaete novye razmery

    Pri dobavlenii novogo razmera ukazhite ego tsenu cherez parametr `price`. Esli v zaprose ne ukazan
    `price`, tsena razmera budet `0` — v etom sluchae izmenit' ee mozhno budet s pomosch'ju metodov:
      - [Ustanovit' tseny i skidki](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1upload~1task/post), esli u [tovara](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1list~1goods~1filter/get) `\"editablePriceSize\":false`
      - [Ustanovit' tseny dlja razmerov](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1upload~1task~1size/post), esli u [tovara](/openapi/work-with-
    products#tag/Ceny-i-skidki/paths/~1api~1v2~1list~1goods~1filter/get) `\"editablePriceSize\":true`

    Gabarity tovarov mozhno ukazat' tol'ko v `santimetrah`, ves tovara s upakovkoj — v `kilogrammah`.
    <br><br>
    Odnim zaprosom mozhno otredaktirovat' maksimum 3000 kartochek tovarov (`nmID`). Maksimal'nyj razmer
    zaprosa 10 Mb.<br>
    Esli otvet `Uspeshno` (`200`), no kakie-to kartochki ne obnovilis', prover'te [spisok nesozdannyh
    kartochek tovarov](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1error~1list/post).<br>
    Sinhronizatsija dannyh s servisami mozhet zanimat' do 30 minut. V techenie etogo vremeni nevozmozhno
    dobavit' ostatki na sklady i nastroit' tseny. <br>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 10 zaprosov | 6 sek | 5 zaprosov |
    </div>

    Args:
        body (list[PostContentV2CardsUpdateBodyItem]):  Example: [{'nmID': 11111111, 'vendorCode':
            'wbiz72wmro', 'brand': '', 'title': 'Sviter zhenskij oversajz s gorlom', 'description':
            '12345', 'dimensions': {'length': 35, 'width': 40, 'height': 15, 'weightBrutto': 3},
            'characteristics': [{'id': 14177450, 'value': ['hlopok 50% akril 50%']}, {'id': 50,
            'value': ['svobodnyj kroj']}], 'sizes': [{'chrtID': 12345678, 'techSize': 'ONE SIZE',
            'wbSize': '78-90', 'skus': ['123487653460134']}]}].

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostContentV2CardsUpdateResponse401 | PostContentV2CardsUpdateResponse413 | PostContentV2CardsUpdateResponse429 | ResponseBodyContentError400 | ResponseBodyContentError403 | ResponseCardCreate
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: list[PostContentV2CardsUpdateBodyItem],
) -> Response[
    PostContentV2CardsUpdateResponse401
    | PostContentV2CardsUpdateResponse413
    | PostContentV2CardsUpdateResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
    | ResponseCardCreate
]:
    r"""Redaktirovanie kartochek tovarov

     Metod obnovljaet dannye kartochek tovarov. Takzhe ispol'zujte ego, chtoby dobavljat' novye razmery.

    <div class=\"description_important\">
      Kartochka tovara perezapisyvaetsja pri obnovlenii. Poetomu v zaprose nuzhno peredat' v tom chisle
    te parametry kartochki, kotorye vy ne sobiraetes' obnovljat'. Ih znachenija mozhno poluchit' v <a
    href=\"/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1list/post\">spiske kartochek tovarov</a> i <a
    href=\"/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1trash/post\">spiske kartochek tovarov v korzine</a>.
    </div>

    S pomosch'ju etogo metoda nel'zja obnovljat' ili udaljat':
      - barkody razmerov tovara. Mozhno tol'ko dobavit' dopolnitel'nye barkody
      - parametry `photos`, `video` i `tags`
      - tseny tovarov. Tsenu mozhno zadat', tol'ko esli vy dobavljaete novye razmery

    Pri dobavlenii novogo razmera ukazhite ego tsenu cherez parametr `price`. Esli v zaprose ne ukazan
    `price`, tsena razmera budet `0` — v etom sluchae izmenit' ee mozhno budet s pomosch'ju metodov:
      - [Ustanovit' tseny i skidki](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1upload~1task/post), esli u [tovara](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1list~1goods~1filter/get) `\"editablePriceSize\":false`
      - [Ustanovit' tseny dlja razmerov](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1upload~1task~1size/post), esli u [tovara](/openapi/work-with-
    products#tag/Ceny-i-skidki/paths/~1api~1v2~1list~1goods~1filter/get) `\"editablePriceSize\":true`

    Gabarity tovarov mozhno ukazat' tol'ko v `santimetrah`, ves tovara s upakovkoj — v `kilogrammah`.
    <br><br>
    Odnim zaprosom mozhno otredaktirovat' maksimum 3000 kartochek tovarov (`nmID`). Maksimal'nyj razmer
    zaprosa 10 Mb.<br>
    Esli otvet `Uspeshno` (`200`), no kakie-to kartochki ne obnovilis', prover'te [spisok nesozdannyh
    kartochek tovarov](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1error~1list/post).<br>
    Sinhronizatsija dannyh s servisami mozhet zanimat' do 30 minut. V techenie etogo vremeni nevozmozhno
    dobavit' ostatki na sklady i nastroit' tseny. <br>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 10 zaprosov | 6 sek | 5 zaprosov |
    </div>

    Args:
        body (list[PostContentV2CardsUpdateBodyItem]):  Example: [{'nmID': 11111111, 'vendorCode':
            'wbiz72wmro', 'brand': '', 'title': 'Sviter zhenskij oversajz s gorlom', 'description':
            '12345', 'dimensions': {'length': 35, 'width': 40, 'height': 15, 'weightBrutto': 3},
            'characteristics': [{'id': 14177450, 'value': ['hlopok 50% akril 50%']}, {'id': 50,
            'value': ['svobodnyj kroj']}], 'sizes': [{'chrtID': 12345678, 'techSize': 'ONE SIZE',
            'wbSize': '78-90', 'skus': ['123487653460134']}]}].

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostContentV2CardsUpdateResponse401 | PostContentV2CardsUpdateResponse413 | PostContentV2CardsUpdateResponse429 | ResponseBodyContentError400 | ResponseBodyContentError403 | ResponseCardCreate]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: list[PostContentV2CardsUpdateBodyItem],
) -> (
    PostContentV2CardsUpdateResponse401
    | PostContentV2CardsUpdateResponse413
    | PostContentV2CardsUpdateResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
    | ResponseCardCreate
    | None
):
    r"""Redaktirovanie kartochek tovarov

     Metod obnovljaet dannye kartochek tovarov. Takzhe ispol'zujte ego, chtoby dobavljat' novye razmery.

    <div class=\"description_important\">
      Kartochka tovara perezapisyvaetsja pri obnovlenii. Poetomu v zaprose nuzhno peredat' v tom chisle
    te parametry kartochki, kotorye vy ne sobiraetes' obnovljat'. Ih znachenija mozhno poluchit' v <a
    href=\"/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1list/post\">spiske kartochek tovarov</a> i <a
    href=\"/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1trash/post\">spiske kartochek tovarov v korzine</a>.
    </div>

    S pomosch'ju etogo metoda nel'zja obnovljat' ili udaljat':
      - barkody razmerov tovara. Mozhno tol'ko dobavit' dopolnitel'nye barkody
      - parametry `photos`, `video` i `tags`
      - tseny tovarov. Tsenu mozhno zadat', tol'ko esli vy dobavljaete novye razmery

    Pri dobavlenii novogo razmera ukazhite ego tsenu cherez parametr `price`. Esli v zaprose ne ukazan
    `price`, tsena razmera budet `0` — v etom sluchae izmenit' ee mozhno budet s pomosch'ju metodov:
      - [Ustanovit' tseny i skidki](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1upload~1task/post), esli u [tovara](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1list~1goods~1filter/get) `\"editablePriceSize\":false`
      - [Ustanovit' tseny dlja razmerov](/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1upload~1task~1size/post), esli u [tovara](/openapi/work-with-
    products#tag/Ceny-i-skidki/paths/~1api~1v2~1list~1goods~1filter/get) `\"editablePriceSize\":true`

    Gabarity tovarov mozhno ukazat' tol'ko v `santimetrah`, ves tovara s upakovkoj — v `kilogrammah`.
    <br><br>
    Odnim zaprosom mozhno otredaktirovat' maksimum 3000 kartochek tovarov (`nmID`). Maksimal'nyj razmer
    zaprosa 10 Mb.<br>
    Esli otvet `Uspeshno` (`200`), no kakie-to kartochki ne obnovilis', prover'te [spisok nesozdannyh
    kartochek tovarov](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1error~1list/post).<br>
    Sinhronizatsija dannyh s servisami mozhet zanimat' do 30 minut. V techenie etogo vremeni nevozmozhno
    dobavit' ostatki na sklady i nastroit' tseny. <br>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 10 zaprosov | 6 sek | 5 zaprosov |
    </div>

    Args:
        body (list[PostContentV2CardsUpdateBodyItem]):  Example: [{'nmID': 11111111, 'vendorCode':
            'wbiz72wmro', 'brand': '', 'title': 'Sviter zhenskij oversajz s gorlom', 'description':
            '12345', 'dimensions': {'length': 35, 'width': 40, 'height': 15, 'weightBrutto': 3},
            'characteristics': [{'id': 14177450, 'value': ['hlopok 50% akril 50%']}, {'id': 50,
            'value': ['svobodnyj kroj']}], 'sizes': [{'chrtID': 12345678, 'techSize': 'ONE SIZE',
            'wbSize': '78-90', 'skus': ['123487653460134']}]}].

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostContentV2CardsUpdateResponse401 | PostContentV2CardsUpdateResponse413 | PostContentV2CardsUpdateResponse429 | ResponseBodyContentError400 | ResponseBodyContentError403 | ResponseCardCreate
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
