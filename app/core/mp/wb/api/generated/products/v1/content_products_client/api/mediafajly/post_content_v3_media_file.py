from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.media_errors import MediaErrors
from ...models.post_content_v3_media_file_body import PostContentV3MediaFileBody
from ...models.post_content_v3_media_file_response_200 import (
    PostContentV3MediaFileResponse200,
)
from ...models.post_content_v3_media_file_response_401 import (
    PostContentV3MediaFileResponse401,
)
from ...models.post_content_v3_media_file_response_429 import (
    PostContentV3MediaFileResponse429,
)
from ...types import Response


def _get_kwargs(
    *,
    body: PostContentV3MediaFileBody,
    x_nm_id: str,
    x_photo_number: int,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    headers["X-Nm-Id"] = x_nm_id

    headers["X-Photo-Number"] = str(x_photo_number)

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/content/v3/media/file",
    }

    _kwargs["files"] = body.to_multipart()

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    MediaErrors
    | PostContentV3MediaFileResponse200
    | PostContentV3MediaFileResponse401
    | PostContentV3MediaFileResponse429
    | None
):
    if response.status_code == 200:
        response_200 = PostContentV3MediaFileResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = MediaErrors.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostContentV3MediaFileResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = MediaErrors.from_dict(response.json())

        return response_403

    if response.status_code == 429:
        response_429 = PostContentV3MediaFileResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    MediaErrors
    | PostContentV3MediaFileResponse200
    | PostContentV3MediaFileResponse401
    | PostContentV3MediaFileResponse429
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
    body: PostContentV3MediaFileBody,
    x_nm_id: str,
    x_photo_number: int,
) -> Response[
    MediaErrors
    | PostContentV3MediaFileResponse200
    | PostContentV3MediaFileResponse401
    | PostContentV3MediaFileResponse429
]:
    r"""Zagruzit' mediafajl

     Metod zagruzhaet i dobavljaet odin mediafajl k kartochke tovara.

    Trebovanija k izobrazhenijam:
      * maksimum izobrazhenij dlja odnoj kartochki tovara — 30
      * minimal'noe razreshenie — 700x900 px
      * maksimal'nyj razmer — 32 Mb
      * minimal'noe kachestvo — 65%
      * formaty — JPG, PNG, BMP, GIF (statichnye), WebP

    Trebovanija k video:
      * maksimum odno video dlja odnoj kartochki tovara
      * maksimal'nyj razmer — 50 Mb
      * formaty — MOV, MP4

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
        x_nm_id (str):  Example: 213864079.
        x_photo_number (int):  Example: 2.
        body (PostContentV3MediaFileBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[MediaErrors | PostContentV3MediaFileResponse200 | PostContentV3MediaFileResponse401 | PostContentV3MediaFileResponse429]
    """

    kwargs = _get_kwargs(
        body=body,
        x_nm_id=x_nm_id,
        x_photo_number=x_photo_number,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    body: PostContentV3MediaFileBody,
    x_nm_id: str,
    x_photo_number: int,
) -> (
    MediaErrors
    | PostContentV3MediaFileResponse200
    | PostContentV3MediaFileResponse401
    | PostContentV3MediaFileResponse429
    | None
):
    r"""Zagruzit' mediafajl

     Metod zagruzhaet i dobavljaet odin mediafajl k kartochke tovara.

    Trebovanija k izobrazhenijam:
      * maksimum izobrazhenij dlja odnoj kartochki tovara — 30
      * minimal'noe razreshenie — 700x900 px
      * maksimal'nyj razmer — 32 Mb
      * minimal'noe kachestvo — 65%
      * formaty — JPG, PNG, BMP, GIF (statichnye), WebP

    Trebovanija k video:
      * maksimum odno video dlja odnoj kartochki tovara
      * maksimal'nyj razmer — 50 Mb
      * formaty — MOV, MP4

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
        x_nm_id (str):  Example: 213864079.
        x_photo_number (int):  Example: 2.
        body (PostContentV3MediaFileBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        MediaErrors | PostContentV3MediaFileResponse200 | PostContentV3MediaFileResponse401 | PostContentV3MediaFileResponse429
    """

    return sync_detailed(
        client=client,
        body=body,
        x_nm_id=x_nm_id,
        x_photo_number=x_photo_number,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PostContentV3MediaFileBody,
    x_nm_id: str,
    x_photo_number: int,
) -> Response[
    MediaErrors
    | PostContentV3MediaFileResponse200
    | PostContentV3MediaFileResponse401
    | PostContentV3MediaFileResponse429
]:
    r"""Zagruzit' mediafajl

     Metod zagruzhaet i dobavljaet odin mediafajl k kartochke tovara.

    Trebovanija k izobrazhenijam:
      * maksimum izobrazhenij dlja odnoj kartochki tovara — 30
      * minimal'noe razreshenie — 700x900 px
      * maksimal'nyj razmer — 32 Mb
      * minimal'noe kachestvo — 65%
      * formaty — JPG, PNG, BMP, GIF (statichnye), WebP

    Trebovanija k video:
      * maksimum odno video dlja odnoj kartochki tovara
      * maksimal'nyj razmer — 50 Mb
      * formaty — MOV, MP4

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
        x_nm_id (str):  Example: 213864079.
        x_photo_number (int):  Example: 2.
        body (PostContentV3MediaFileBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[MediaErrors | PostContentV3MediaFileResponse200 | PostContentV3MediaFileResponse401 | PostContentV3MediaFileResponse429]
    """

    kwargs = _get_kwargs(
        body=body,
        x_nm_id=x_nm_id,
        x_photo_number=x_photo_number,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: PostContentV3MediaFileBody,
    x_nm_id: str,
    x_photo_number: int,
) -> (
    MediaErrors
    | PostContentV3MediaFileResponse200
    | PostContentV3MediaFileResponse401
    | PostContentV3MediaFileResponse429
    | None
):
    r"""Zagruzit' mediafajl

     Metod zagruzhaet i dobavljaet odin mediafajl k kartochke tovara.

    Trebovanija k izobrazhenijam:
      * maksimum izobrazhenij dlja odnoj kartochki tovara — 30
      * minimal'noe razreshenie — 700x900 px
      * maksimal'nyj razmer — 32 Mb
      * minimal'noe kachestvo — 65%
      * formaty — JPG, PNG, BMP, GIF (statichnye), WebP

    Trebovanija k video:
      * maksimum odno video dlja odnoj kartochki tovara
      * maksimal'nyj razmer — 50 Mb
      * formaty — MOV, MP4

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
        x_nm_id (str):  Example: 213864079.
        x_photo_number (int):  Example: 2.
        body (PostContentV3MediaFileBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        MediaErrors | PostContentV3MediaFileResponse200 | PostContentV3MediaFileResponse401 | PostContentV3MediaFileResponse429
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            x_nm_id=x_nm_id,
            x_photo_number=x_photo_number,
        )
    ).parsed
