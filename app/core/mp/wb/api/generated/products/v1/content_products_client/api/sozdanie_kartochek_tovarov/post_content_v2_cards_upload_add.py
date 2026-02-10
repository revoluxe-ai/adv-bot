from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_content_v2_cards_upload_add_body import (
    PostContentV2CardsUploadAddBody,
)
from ...models.post_content_v2_cards_upload_add_response_401 import (
    PostContentV2CardsUploadAddResponse401,
)
from ...models.post_content_v2_cards_upload_add_response_413 import (
    PostContentV2CardsUploadAddResponse413,
)
from ...models.post_content_v2_cards_upload_add_response_429 import (
    PostContentV2CardsUploadAddResponse429,
)
from ...models.response_body_content_error_400 import ResponseBodyContentError400
from ...models.response_card_create import ResponseCardCreate
from ...types import Response


def _get_kwargs(
    *,
    body: PostContentV2CardsUploadAddBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/content/v2/cards/upload/add",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    PostContentV2CardsUploadAddResponse401
    | PostContentV2CardsUploadAddResponse413
    | PostContentV2CardsUploadAddResponse429
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
        response_401 = PostContentV2CardsUploadAddResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 413:
        response_413 = PostContentV2CardsUploadAddResponse413.from_dict(response.json())

        return response_413

    if response.status_code == 429:
        response_429 = PostContentV2CardsUploadAddResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    PostContentV2CardsUploadAddResponse401
    | PostContentV2CardsUploadAddResponse413
    | PostContentV2CardsUploadAddResponse429
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
    body: PostContentV2CardsUploadAddBody,
) -> Response[
    PostContentV2CardsUploadAddResponse401
    | PostContentV2CardsUploadAddResponse413
    | PostContentV2CardsUploadAddResponse429
    | ResponseBodyContentError400
    | ResponseCardCreate
]:
    r"""Sozdanie kartochek tovarov s prisoedineniem

     Metod sozdaet kartochki tovarov, prisoedinjaja ih k suschestvujuschim otdel'nym kartochkam i gruppam
    [ob'edinennyh](https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-kartochek-tovarov)
    kartochek. V odnoj gruppe ob'edinennyh kartochek tovarov mozhet byt' ne bolee 30 kartochek,
    sootvetstvenno, sozdat' s prisoedineniem mozhno ne bolee 29 kartochek tovarov za odin zapros.

    Gabarity tovarov mozhno ukazat' tol'ko v `santimetrah`, ves tovara s upakovkoj — v `kilogrammah`.
    <br><br>
    Esli otvet `Uspeshno` (`200`), no kakie-to kartochki ne sozdalis', prover'te [spisok nesozdannyh
    kartochek tovarov](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1error~1list/post).<br>
    Sozdanie kartochki tovara proishodit asinhronno. Sinhronizatsija novoj kartochki s servisami mozhet
    zanimat' do 30 minut. V techenie etogo vremeni nevozmozhno dobavit' ostatki na sklady i nastroit'
    tseny.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 10 zaprosov | 6 sek | 5 zaprosov |
    </div>

    Args:
        body (PostContentV2CardsUploadAddBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostContentV2CardsUploadAddResponse401 | PostContentV2CardsUploadAddResponse413 | PostContentV2CardsUploadAddResponse429 | ResponseBodyContentError400 | ResponseCardCreate]
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
    body: PostContentV2CardsUploadAddBody,
) -> (
    PostContentV2CardsUploadAddResponse401
    | PostContentV2CardsUploadAddResponse413
    | PostContentV2CardsUploadAddResponse429
    | ResponseBodyContentError400
    | ResponseCardCreate
    | None
):
    r"""Sozdanie kartochek tovarov s prisoedineniem

     Metod sozdaet kartochki tovarov, prisoedinjaja ih k suschestvujuschim otdel'nym kartochkam i gruppam
    [ob'edinennyh](https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-kartochek-tovarov)
    kartochek. V odnoj gruppe ob'edinennyh kartochek tovarov mozhet byt' ne bolee 30 kartochek,
    sootvetstvenno, sozdat' s prisoedineniem mozhno ne bolee 29 kartochek tovarov za odin zapros.

    Gabarity tovarov mozhno ukazat' tol'ko v `santimetrah`, ves tovara s upakovkoj — v `kilogrammah`.
    <br><br>
    Esli otvet `Uspeshno` (`200`), no kakie-to kartochki ne sozdalis', prover'te [spisok nesozdannyh
    kartochek tovarov](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1error~1list/post).<br>
    Sozdanie kartochki tovara proishodit asinhronno. Sinhronizatsija novoj kartochki s servisami mozhet
    zanimat' do 30 minut. V techenie etogo vremeni nevozmozhno dobavit' ostatki na sklady i nastroit'
    tseny.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 10 zaprosov | 6 sek | 5 zaprosov |
    </div>

    Args:
        body (PostContentV2CardsUploadAddBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostContentV2CardsUploadAddResponse401 | PostContentV2CardsUploadAddResponse413 | PostContentV2CardsUploadAddResponse429 | ResponseBodyContentError400 | ResponseCardCreate
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: PostContentV2CardsUploadAddBody,
) -> Response[
    PostContentV2CardsUploadAddResponse401
    | PostContentV2CardsUploadAddResponse413
    | PostContentV2CardsUploadAddResponse429
    | ResponseBodyContentError400
    | ResponseCardCreate
]:
    r"""Sozdanie kartochek tovarov s prisoedineniem

     Metod sozdaet kartochki tovarov, prisoedinjaja ih k suschestvujuschim otdel'nym kartochkam i gruppam
    [ob'edinennyh](https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-kartochek-tovarov)
    kartochek. V odnoj gruppe ob'edinennyh kartochek tovarov mozhet byt' ne bolee 30 kartochek,
    sootvetstvenno, sozdat' s prisoedineniem mozhno ne bolee 29 kartochek tovarov za odin zapros.

    Gabarity tovarov mozhno ukazat' tol'ko v `santimetrah`, ves tovara s upakovkoj — v `kilogrammah`.
    <br><br>
    Esli otvet `Uspeshno` (`200`), no kakie-to kartochki ne sozdalis', prover'te [spisok nesozdannyh
    kartochek tovarov](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1error~1list/post).<br>
    Sozdanie kartochki tovara proishodit asinhronno. Sinhronizatsija novoj kartochki s servisami mozhet
    zanimat' do 30 minut. V techenie etogo vremeni nevozmozhno dobavit' ostatki na sklady i nastroit'
    tseny.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 10 zaprosov | 6 sek | 5 zaprosov |
    </div>

    Args:
        body (PostContentV2CardsUploadAddBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostContentV2CardsUploadAddResponse401 | PostContentV2CardsUploadAddResponse413 | PostContentV2CardsUploadAddResponse429 | ResponseBodyContentError400 | ResponseCardCreate]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: PostContentV2CardsUploadAddBody,
) -> (
    PostContentV2CardsUploadAddResponse401
    | PostContentV2CardsUploadAddResponse413
    | PostContentV2CardsUploadAddResponse429
    | ResponseBodyContentError400
    | ResponseCardCreate
    | None
):
    r"""Sozdanie kartochek tovarov s prisoedineniem

     Metod sozdaet kartochki tovarov, prisoedinjaja ih k suschestvujuschim otdel'nym kartochkam i gruppam
    [ob'edinennyh](https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-kartochek-tovarov)
    kartochek. V odnoj gruppe ob'edinennyh kartochek tovarov mozhet byt' ne bolee 30 kartochek,
    sootvetstvenno, sozdat' s prisoedineniem mozhno ne bolee 29 kartochek tovarov za odin zapros.

    Gabarity tovarov mozhno ukazat' tol'ko v `santimetrah`, ves tovara s upakovkoj — v `kilogrammah`.
    <br><br>
    Esli otvet `Uspeshno` (`200`), no kakie-to kartochki ne sozdalis', prover'te [spisok nesozdannyh
    kartochek tovarov](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1error~1list/post).<br>
    Sozdanie kartochki tovara proishodit asinhronno. Sinhronizatsija novoj kartochki s servisami mozhet
    zanimat' do 30 minut. V techenie etogo vremeni nevozmozhno dobavit' ostatki na sklady i nastroit'
    tseny.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 10 zaprosov | 6 sek | 5 zaprosov |
    </div>

    Args:
        body (PostContentV2CardsUploadAddBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostContentV2CardsUploadAddResponse401 | PostContentV2CardsUploadAddResponse413 | PostContentV2CardsUploadAddResponse429 | ResponseBodyContentError400 | ResponseCardCreate
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
