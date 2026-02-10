from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.media_errors import MediaErrors
from ...models.post_content_v3_media_save_body import PostContentV3MediaSaveBody
from ...models.post_content_v3_media_save_response_200 import (
    PostContentV3MediaSaveResponse200,
)
from ...models.post_content_v3_media_save_response_401 import (
    PostContentV3MediaSaveResponse401,
)
from ...models.post_content_v3_media_save_response_429 import (
    PostContentV3MediaSaveResponse429,
)
from ...types import Response


def _get_kwargs(
    *,
    body: PostContentV3MediaSaveBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/content/v3/media/save",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    MediaErrors
    | PostContentV3MediaSaveResponse200
    | PostContentV3MediaSaveResponse401
    | PostContentV3MediaSaveResponse429
    | None
):
    if response.status_code == 200:
        response_200 = PostContentV3MediaSaveResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = MediaErrors.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostContentV3MediaSaveResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = MediaErrors.from_dict(response.json())

        return response_403

    if response.status_code == 409:
        response_409 = MediaErrors.from_dict(response.json())

        return response_409

    if response.status_code == 422:
        response_422 = MediaErrors.from_dict(response.json())

        return response_422

    if response.status_code == 429:
        response_429 = PostContentV3MediaSaveResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    MediaErrors
    | PostContentV3MediaSaveResponse200
    | PostContentV3MediaSaveResponse401
    | PostContentV3MediaSaveResponse429
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
    body: PostContentV3MediaSaveBody,
) -> Response[
    MediaErrors
    | PostContentV3MediaSaveResponse200
    | PostContentV3MediaSaveResponse401
    | PostContentV3MediaSaveResponse429
]:
    r"""Zagruzit' mediafajly po ssylkam

     Metod zagruzhaet nabor mediafajlov v kartochku tovara cherez ukazanie ssylok v zaprose.

    <div class=\"description_important\">
      Novye mediafajly polnost'ju zamenjajut starye. Chtoby dobavit' novye mediafajly, ukazhite v
    zaprose ssylki odnovremenno na novye i starye mediafajly.
    </div>

    Trebovanija k ssylkam:
      * ssylka dolzhna vesti prjamo na fajl. Ubedites', chto ssylka ne vedet na stranitsu predprosmotra
    ili avtorizatsii, naprimer. Esli po ssylke otkryvaetsja tekstovaja stranitsa TXT ili HTML, ssylka
    schitaetsja nekorrektnoj
      * dlja dostupa k fajlu po ssylke ne nuzhna avtorizatsija

    Trebovanija k izobrazhenijam:
      * maksimum izobrazhenij dlja odnoj kartochki tovara — 30
      * minimal'noe razreshenie — 700×900 px
      * maksimal'nyj razmer — 32 Mb
      * minimal'noe kachestvo — 65%
      * formaty — JPG, PNG, BMP, GIF (statichnye), WebP

    Trebovanija k video:
      * maksimum odno video dlja odnoj kartochki tovara
      * maksimal'nyj razmer — 50 Mb
      * formaty — MOV, MP4

    Esli video ili hotja by odno izobrazhenie v zaprose ne sootvetstvuet trebovanijam, to dazhe pri
    uspeshnom otvete (`200`) ni odno izobrazhenie/video ne zagruzitsja.

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
        body (PostContentV3MediaSaveBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[MediaErrors | PostContentV3MediaSaveResponse200 | PostContentV3MediaSaveResponse401 | PostContentV3MediaSaveResponse429]
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
    body: PostContentV3MediaSaveBody,
) -> (
    MediaErrors
    | PostContentV3MediaSaveResponse200
    | PostContentV3MediaSaveResponse401
    | PostContentV3MediaSaveResponse429
    | None
):
    r"""Zagruzit' mediafajly po ssylkam

     Metod zagruzhaet nabor mediafajlov v kartochku tovara cherez ukazanie ssylok v zaprose.

    <div class=\"description_important\">
      Novye mediafajly polnost'ju zamenjajut starye. Chtoby dobavit' novye mediafajly, ukazhite v
    zaprose ssylki odnovremenno na novye i starye mediafajly.
    </div>

    Trebovanija k ssylkam:
      * ssylka dolzhna vesti prjamo na fajl. Ubedites', chto ssylka ne vedet na stranitsu predprosmotra
    ili avtorizatsii, naprimer. Esli po ssylke otkryvaetsja tekstovaja stranitsa TXT ili HTML, ssylka
    schitaetsja nekorrektnoj
      * dlja dostupa k fajlu po ssylke ne nuzhna avtorizatsija

    Trebovanija k izobrazhenijam:
      * maksimum izobrazhenij dlja odnoj kartochki tovara — 30
      * minimal'noe razreshenie — 700×900 px
      * maksimal'nyj razmer — 32 Mb
      * minimal'noe kachestvo — 65%
      * formaty — JPG, PNG, BMP, GIF (statichnye), WebP

    Trebovanija k video:
      * maksimum odno video dlja odnoj kartochki tovara
      * maksimal'nyj razmer — 50 Mb
      * formaty — MOV, MP4

    Esli video ili hotja by odno izobrazhenie v zaprose ne sootvetstvuet trebovanijam, to dazhe pri
    uspeshnom otvete (`200`) ni odno izobrazhenie/video ne zagruzitsja.

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
        body (PostContentV3MediaSaveBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        MediaErrors | PostContentV3MediaSaveResponse200 | PostContentV3MediaSaveResponse401 | PostContentV3MediaSaveResponse429
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PostContentV3MediaSaveBody,
) -> Response[
    MediaErrors
    | PostContentV3MediaSaveResponse200
    | PostContentV3MediaSaveResponse401
    | PostContentV3MediaSaveResponse429
]:
    r"""Zagruzit' mediafajly po ssylkam

     Metod zagruzhaet nabor mediafajlov v kartochku tovara cherez ukazanie ssylok v zaprose.

    <div class=\"description_important\">
      Novye mediafajly polnost'ju zamenjajut starye. Chtoby dobavit' novye mediafajly, ukazhite v
    zaprose ssylki odnovremenno na novye i starye mediafajly.
    </div>

    Trebovanija k ssylkam:
      * ssylka dolzhna vesti prjamo na fajl. Ubedites', chto ssylka ne vedet na stranitsu predprosmotra
    ili avtorizatsii, naprimer. Esli po ssylke otkryvaetsja tekstovaja stranitsa TXT ili HTML, ssylka
    schitaetsja nekorrektnoj
      * dlja dostupa k fajlu po ssylke ne nuzhna avtorizatsija

    Trebovanija k izobrazhenijam:
      * maksimum izobrazhenij dlja odnoj kartochki tovara — 30
      * minimal'noe razreshenie — 700×900 px
      * maksimal'nyj razmer — 32 Mb
      * minimal'noe kachestvo — 65%
      * formaty — JPG, PNG, BMP, GIF (statichnye), WebP

    Trebovanija k video:
      * maksimum odno video dlja odnoj kartochki tovara
      * maksimal'nyj razmer — 50 Mb
      * formaty — MOV, MP4

    Esli video ili hotja by odno izobrazhenie v zaprose ne sootvetstvuet trebovanijam, to dazhe pri
    uspeshnom otvete (`200`) ni odno izobrazhenie/video ne zagruzitsja.

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
        body (PostContentV3MediaSaveBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[MediaErrors | PostContentV3MediaSaveResponse200 | PostContentV3MediaSaveResponse401 | PostContentV3MediaSaveResponse429]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: PostContentV3MediaSaveBody,
) -> (
    MediaErrors
    | PostContentV3MediaSaveResponse200
    | PostContentV3MediaSaveResponse401
    | PostContentV3MediaSaveResponse429
    | None
):
    r"""Zagruzit' mediafajly po ssylkam

     Metod zagruzhaet nabor mediafajlov v kartochku tovara cherez ukazanie ssylok v zaprose.

    <div class=\"description_important\">
      Novye mediafajly polnost'ju zamenjajut starye. Chtoby dobavit' novye mediafajly, ukazhite v
    zaprose ssylki odnovremenno na novye i starye mediafajly.
    </div>

    Trebovanija k ssylkam:
      * ssylka dolzhna vesti prjamo na fajl. Ubedites', chto ssylka ne vedet na stranitsu predprosmotra
    ili avtorizatsii, naprimer. Esli po ssylke otkryvaetsja tekstovaja stranitsa TXT ili HTML, ssylka
    schitaetsja nekorrektnoj
      * dlja dostupa k fajlu po ssylke ne nuzhna avtorizatsija

    Trebovanija k izobrazhenijam:
      * maksimum izobrazhenij dlja odnoj kartochki tovara — 30
      * minimal'noe razreshenie — 700×900 px
      * maksimal'nyj razmer — 32 Mb
      * minimal'noe kachestvo — 65%
      * formaty — JPG, PNG, BMP, GIF (statichnye), WebP

    Trebovanija k video:
      * maksimum odno video dlja odnoj kartochki tovara
      * maksimal'nyj razmer — 50 Mb
      * formaty — MOV, MP4

    Esli video ili hotja by odno izobrazhenie v zaprose ne sootvetstvuet trebovanijam, to dazhe pri
    uspeshnom otvete (`200`) ni odno izobrazhenie/video ne zagruzitsja.

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
        body (PostContentV3MediaSaveBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        MediaErrors | PostContentV3MediaSaveResponse200 | PostContentV3MediaSaveResponse401 | PostContentV3MediaSaveResponse429
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
