from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_content_v2_cards_upload_body_item import (
    PostContentV2CardsUploadBodyItem,
)
from ...models.post_content_v2_cards_upload_response_401 import (
    PostContentV2CardsUploadResponse401,
)
from ...models.post_content_v2_cards_upload_response_413 import (
    PostContentV2CardsUploadResponse413,
)
from ...models.post_content_v2_cards_upload_response_429 import (
    PostContentV2CardsUploadResponse429,
)
from ...models.response_body_content_error_400 import ResponseBodyContentError400
from ...models.response_card_create import ResponseCardCreate
from ...types import Response


def _get_kwargs(
    *,
    body: list[PostContentV2CardsUploadBodyItem],
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/content/v2/cards/upload",
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
    PostContentV2CardsUploadResponse401
    | PostContentV2CardsUploadResponse413
    | PostContentV2CardsUploadResponse429
    | ResponseBodyContentError400
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
        response_401 = PostContentV2CardsUploadResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 413:
        response_413 = PostContentV2CardsUploadResponse413.from_dict(response.json())

        return response_413

    if response.status_code == 429:
        response_429 = PostContentV2CardsUploadResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    PostContentV2CardsUploadResponse401
    | PostContentV2CardsUploadResponse413
    | PostContentV2CardsUploadResponse429
    | ResponseBodyContentError400
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
    body: list[PostContentV2CardsUploadBodyItem],
) -> Response[
    PostContentV2CardsUploadResponse401
    | PostContentV2CardsUploadResponse413
    | PostContentV2CardsUploadResponse429
    | ResponseBodyContentError400
    | ResponseCardCreate
]:
    r"""Sozdanie kartochek tovarov

     Metod sozdaet kartochki tovarov c ukazaniem opisanij i harakteristik tovarov.<br>

    <div class=\"description_important\">
      Est' dve formy zaprosa: dlja sozdanija otdel'nyh i ob'edinennyh kartochek tovarov
    </div>

    Gabarity tovarov mozhno ukazat' tol'ko v `santimetrah`, ves tovara s upakovkoj — v `kilogrammah`.
    <br><br>
    Sozdanie kartochki tovara proishodit asinhronno. Sinhronizatsija novoj kartochki s servisami mozhet
    zanimat' do 30 minut. V techenie etogo vremeni nevozmozhno dobavit' ostatki na sklady i nastroit'
    tseny. <br>
    Odnim zaprosom mozhno sozdat' maksimum 100 otdel'nyh kartochek tovarov ili 100 grupp
    [ob'edinennyh](https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-kartochek-tovarov)
    kartochek tovarov po 30 kartochek v kazhdoj. Maksimal'nyj razmer zaprosa 10 Mb.<br>
    Esli otvet `Uspeshno` (`200`), no kakie-to kartochki ne sozdalis', prover'te [spisok nesozdannyh
    kartochek tovarov](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1error~1list/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 10 zaprosov | 6 sek | 5 zaprosov |
    </div>

    Args:
        body (list[PostContentV2CardsUploadBodyItem]): Otdel'nye kartochki tovarov ili gruppy
            ob'edinennyh kartochek tovarov

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostContentV2CardsUploadResponse401 | PostContentV2CardsUploadResponse413 | PostContentV2CardsUploadResponse429 | ResponseBodyContentError400 | ResponseCardCreate]
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
    body: list[PostContentV2CardsUploadBodyItem],
) -> (
    PostContentV2CardsUploadResponse401
    | PostContentV2CardsUploadResponse413
    | PostContentV2CardsUploadResponse429
    | ResponseBodyContentError400
    | ResponseCardCreate
    | None
):
    r"""Sozdanie kartochek tovarov

     Metod sozdaet kartochki tovarov c ukazaniem opisanij i harakteristik tovarov.<br>

    <div class=\"description_important\">
      Est' dve formy zaprosa: dlja sozdanija otdel'nyh i ob'edinennyh kartochek tovarov
    </div>

    Gabarity tovarov mozhno ukazat' tol'ko v `santimetrah`, ves tovara s upakovkoj — v `kilogrammah`.
    <br><br>
    Sozdanie kartochki tovara proishodit asinhronno. Sinhronizatsija novoj kartochki s servisami mozhet
    zanimat' do 30 minut. V techenie etogo vremeni nevozmozhno dobavit' ostatki na sklady i nastroit'
    tseny. <br>
    Odnim zaprosom mozhno sozdat' maksimum 100 otdel'nyh kartochek tovarov ili 100 grupp
    [ob'edinennyh](https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-kartochek-tovarov)
    kartochek tovarov po 30 kartochek v kazhdoj. Maksimal'nyj razmer zaprosa 10 Mb.<br>
    Esli otvet `Uspeshno` (`200`), no kakie-to kartochki ne sozdalis', prover'te [spisok nesozdannyh
    kartochek tovarov](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1error~1list/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 10 zaprosov | 6 sek | 5 zaprosov |
    </div>

    Args:
        body (list[PostContentV2CardsUploadBodyItem]): Otdel'nye kartochki tovarov ili gruppy
            ob'edinennyh kartochek tovarov

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostContentV2CardsUploadResponse401 | PostContentV2CardsUploadResponse413 | PostContentV2CardsUploadResponse429 | ResponseBodyContentError400 | ResponseCardCreate
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: list[PostContentV2CardsUploadBodyItem],
) -> Response[
    PostContentV2CardsUploadResponse401
    | PostContentV2CardsUploadResponse413
    | PostContentV2CardsUploadResponse429
    | ResponseBodyContentError400
    | ResponseCardCreate
]:
    r"""Sozdanie kartochek tovarov

     Metod sozdaet kartochki tovarov c ukazaniem opisanij i harakteristik tovarov.<br>

    <div class=\"description_important\">
      Est' dve formy zaprosa: dlja sozdanija otdel'nyh i ob'edinennyh kartochek tovarov
    </div>

    Gabarity tovarov mozhno ukazat' tol'ko v `santimetrah`, ves tovara s upakovkoj — v `kilogrammah`.
    <br><br>
    Sozdanie kartochki tovara proishodit asinhronno. Sinhronizatsija novoj kartochki s servisami mozhet
    zanimat' do 30 minut. V techenie etogo vremeni nevozmozhno dobavit' ostatki na sklady i nastroit'
    tseny. <br>
    Odnim zaprosom mozhno sozdat' maksimum 100 otdel'nyh kartochek tovarov ili 100 grupp
    [ob'edinennyh](https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-kartochek-tovarov)
    kartochek tovarov po 30 kartochek v kazhdoj. Maksimal'nyj razmer zaprosa 10 Mb.<br>
    Esli otvet `Uspeshno` (`200`), no kakie-to kartochki ne sozdalis', prover'te [spisok nesozdannyh
    kartochek tovarov](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1error~1list/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 10 zaprosov | 6 sek | 5 zaprosov |
    </div>

    Args:
        body (list[PostContentV2CardsUploadBodyItem]): Otdel'nye kartochki tovarov ili gruppy
            ob'edinennyh kartochek tovarov

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostContentV2CardsUploadResponse401 | PostContentV2CardsUploadResponse413 | PostContentV2CardsUploadResponse429 | ResponseBodyContentError400 | ResponseCardCreate]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: list[PostContentV2CardsUploadBodyItem],
) -> (
    PostContentV2CardsUploadResponse401
    | PostContentV2CardsUploadResponse413
    | PostContentV2CardsUploadResponse429
    | ResponseBodyContentError400
    | ResponseCardCreate
    | None
):
    r"""Sozdanie kartochek tovarov

     Metod sozdaet kartochki tovarov c ukazaniem opisanij i harakteristik tovarov.<br>

    <div class=\"description_important\">
      Est' dve formy zaprosa: dlja sozdanija otdel'nyh i ob'edinennyh kartochek tovarov
    </div>

    Gabarity tovarov mozhno ukazat' tol'ko v `santimetrah`, ves tovara s upakovkoj — v `kilogrammah`.
    <br><br>
    Sozdanie kartochki tovara proishodit asinhronno. Sinhronizatsija novoj kartochki s servisami mozhet
    zanimat' do 30 minut. V techenie etogo vremeni nevozmozhno dobavit' ostatki na sklady i nastroit'
    tseny. <br>
    Odnim zaprosom mozhno sozdat' maksimum 100 otdel'nyh kartochek tovarov ili 100 grupp
    [ob'edinennyh](https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-kartochek-tovarov)
    kartochek tovarov po 30 kartochek v kazhdoj. Maksimal'nyj razmer zaprosa 10 Mb.<br>
    Esli otvet `Uspeshno` (`200`), no kakie-to kartochki ne sozdalis', prover'te [spisok nesozdannyh
    kartochek tovarov](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1error~1list/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 10 zaprosov | 6 sek | 5 zaprosov |
    </div>

    Args:
        body (list[PostContentV2CardsUploadBodyItem]): Otdel'nye kartochki tovarov ili gruppy
            ob'edinennyh kartochek tovarov

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostContentV2CardsUploadResponse401 | PostContentV2CardsUploadResponse413 | PostContentV2CardsUploadResponse429 | ResponseBodyContentError400 | ResponseCardCreate
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
