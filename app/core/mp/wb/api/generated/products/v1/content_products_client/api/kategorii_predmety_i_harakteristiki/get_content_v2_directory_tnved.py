from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_content_v2_directory_tnved_response_200 import (
    GetContentV2DirectoryTnvedResponse200,
)
from ...models.get_content_v2_directory_tnved_response_401 import (
    GetContentV2DirectoryTnvedResponse401,
)
from ...models.get_content_v2_directory_tnved_response_429 import (
    GetContentV2DirectoryTnvedResponse429,
)
from ...models.response_body_content_error_400 import ResponseBodyContentError400
from ...models.response_body_content_error_403 import ResponseBodyContentError403
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    subject_id: int,
    search: int | Unset = UNSET,
    locale: str | Unset = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["subjectID"] = subject_id

    params["search"] = search

    params["locale"] = locale

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/content/v2/directory/tnved",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    GetContentV2DirectoryTnvedResponse200
    | GetContentV2DirectoryTnvedResponse401
    | GetContentV2DirectoryTnvedResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
    | None
):
    if response.status_code == 200:
        response_200 = GetContentV2DirectoryTnvedResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = ResponseBodyContentError400.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = GetContentV2DirectoryTnvedResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = ResponseBodyContentError403.from_dict(response.json())

        return response_403

    if response.status_code == 429:
        response_429 = GetContentV2DirectoryTnvedResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    GetContentV2DirectoryTnvedResponse200
    | GetContentV2DirectoryTnvedResponse401
    | GetContentV2DirectoryTnvedResponse429
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
    subject_id: int,
    search: int | Unset = UNSET,
    locale: str | Unset = UNSET,
) -> Response[
    GetContentV2DirectoryTnvedResponse200
    | GetContentV2DirectoryTnvedResponse401
    | GetContentV2DirectoryTnvedResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
]:
    r"""TNVED-kod

     Metod vozvraschaet spisok TNVED-kodov po ID [predmeta](/openapi/work-with-products#tag/Kategorii-
    predmety-i-harakteristiki/paths/~1content~1v2~1object~1all/get) i fragmentu TNVED-koda.

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
        subject_id (int):  Example: 105.
        search (int | Unset):  Example: 6106903000.
        locale (str | Unset):  Example: en.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetContentV2DirectoryTnvedResponse200 | GetContentV2DirectoryTnvedResponse401 | GetContentV2DirectoryTnvedResponse429 | ResponseBodyContentError400 | ResponseBodyContentError403]
    """

    kwargs = _get_kwargs(
        subject_id=subject_id,
        search=search,
        locale=locale,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    subject_id: int,
    search: int | Unset = UNSET,
    locale: str | Unset = UNSET,
) -> (
    GetContentV2DirectoryTnvedResponse200
    | GetContentV2DirectoryTnvedResponse401
    | GetContentV2DirectoryTnvedResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
    | None
):
    r"""TNVED-kod

     Metod vozvraschaet spisok TNVED-kodov po ID [predmeta](/openapi/work-with-products#tag/Kategorii-
    predmety-i-harakteristiki/paths/~1content~1v2~1object~1all/get) i fragmentu TNVED-koda.

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
        subject_id (int):  Example: 105.
        search (int | Unset):  Example: 6106903000.
        locale (str | Unset):  Example: en.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetContentV2DirectoryTnvedResponse200 | GetContentV2DirectoryTnvedResponse401 | GetContentV2DirectoryTnvedResponse429 | ResponseBodyContentError400 | ResponseBodyContentError403
    """

    return sync_detailed(
        client=client,
        subject_id=subject_id,
        search=search,
        locale=locale,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    subject_id: int,
    search: int | Unset = UNSET,
    locale: str | Unset = UNSET,
) -> Response[
    GetContentV2DirectoryTnvedResponse200
    | GetContentV2DirectoryTnvedResponse401
    | GetContentV2DirectoryTnvedResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
]:
    r"""TNVED-kod

     Metod vozvraschaet spisok TNVED-kodov po ID [predmeta](/openapi/work-with-products#tag/Kategorii-
    predmety-i-harakteristiki/paths/~1content~1v2~1object~1all/get) i fragmentu TNVED-koda.

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
        subject_id (int):  Example: 105.
        search (int | Unset):  Example: 6106903000.
        locale (str | Unset):  Example: en.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetContentV2DirectoryTnvedResponse200 | GetContentV2DirectoryTnvedResponse401 | GetContentV2DirectoryTnvedResponse429 | ResponseBodyContentError400 | ResponseBodyContentError403]
    """

    kwargs = _get_kwargs(
        subject_id=subject_id,
        search=search,
        locale=locale,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    subject_id: int,
    search: int | Unset = UNSET,
    locale: str | Unset = UNSET,
) -> (
    GetContentV2DirectoryTnvedResponse200
    | GetContentV2DirectoryTnvedResponse401
    | GetContentV2DirectoryTnvedResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
    | None
):
    r"""TNVED-kod

     Metod vozvraschaet spisok TNVED-kodov po ID [predmeta](/openapi/work-with-products#tag/Kategorii-
    predmety-i-harakteristiki/paths/~1content~1v2~1object~1all/get) i fragmentu TNVED-koda.

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
        subject_id (int):  Example: 105.
        search (int | Unset):  Example: 6106903000.
        locale (str | Unset):  Example: en.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetContentV2DirectoryTnvedResponse200 | GetContentV2DirectoryTnvedResponse401 | GetContentV2DirectoryTnvedResponse429 | ResponseBodyContentError400 | ResponseBodyContentError403
    """

    return (
        await asyncio_detailed(
            client=client,
            subject_id=subject_id,
            search=search,
            locale=locale,
        )
    ).parsed
