from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_content_v2_object_all_response_200 import (
    GetContentV2ObjectAllResponse200,
)
from ...models.get_content_v2_object_all_response_401 import (
    GetContentV2ObjectAllResponse401,
)
from ...models.get_content_v2_object_all_response_429 import (
    GetContentV2ObjectAllResponse429,
)
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    locale: str | Unset = UNSET,
    name: str | Unset = UNSET,
    limit: int | Unset = 30,
    offset: int | Unset = 0,
    parent_id: int | Unset = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["locale"] = locale

    params["name"] = name

    params["limit"] = limit

    params["offset"] = offset

    params["parentID"] = parent_id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/content/v2/object/all",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    GetContentV2ObjectAllResponse200
    | GetContentV2ObjectAllResponse401
    | GetContentV2ObjectAllResponse429
    | None
):
    if response.status_code == 200:
        response_200 = GetContentV2ObjectAllResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = GetContentV2ObjectAllResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = GetContentV2ObjectAllResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    GetContentV2ObjectAllResponse200
    | GetContentV2ObjectAllResponse401
    | GetContentV2ObjectAllResponse429
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
    locale: str | Unset = UNSET,
    name: str | Unset = UNSET,
    limit: int | Unset = 30,
    offset: int | Unset = 0,
    parent_id: int | Unset = UNSET,
) -> Response[
    GetContentV2ObjectAllResponse200
    | GetContentV2ObjectAllResponse401
    | GetContentV2ObjectAllResponse429
]:
    r"""Spisok predmetov

     Metod vozvraschaet spisok nazvanij [roditel'skih kategorij predmetov](/openapi/work-with-
    products#tag/Kategorii-predmety-i-harakteristiki/paths/~1content~1v2~1object~1parent~1all/get) i ih
    predmetov s ID. Naprimer, u kategorii `Igrushki` budut predmety `Kalejdoskopy`, `Kukly`, `Mjachiki`.

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
        locale (str | Unset):  Example: en.
        name (str | Unset):  Example: Noski.
        limit (int | Unset): Kolichestvo predmetov, maksimum 1000 Default: 30. Example: 1000.
        offset (int | Unset): Skol'ko elementov propustit'. Naprimer, dlja znachenija `10` otvet
            nachnetsja s 11 elementa Default: 0. Example: 5000.
        parent_id (int | Unset):  Example: 1000.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetContentV2ObjectAllResponse200 | GetContentV2ObjectAllResponse401 | GetContentV2ObjectAllResponse429]
    """

    kwargs = _get_kwargs(
        locale=locale,
        name=name,
        limit=limit,
        offset=offset,
        parent_id=parent_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    locale: str | Unset = UNSET,
    name: str | Unset = UNSET,
    limit: int | Unset = 30,
    offset: int | Unset = 0,
    parent_id: int | Unset = UNSET,
) -> (
    GetContentV2ObjectAllResponse200
    | GetContentV2ObjectAllResponse401
    | GetContentV2ObjectAllResponse429
    | None
):
    r"""Spisok predmetov

     Metod vozvraschaet spisok nazvanij [roditel'skih kategorij predmetov](/openapi/work-with-
    products#tag/Kategorii-predmety-i-harakteristiki/paths/~1content~1v2~1object~1parent~1all/get) i ih
    predmetov s ID. Naprimer, u kategorii `Igrushki` budut predmety `Kalejdoskopy`, `Kukly`, `Mjachiki`.

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
        locale (str | Unset):  Example: en.
        name (str | Unset):  Example: Noski.
        limit (int | Unset): Kolichestvo predmetov, maksimum 1000 Default: 30. Example: 1000.
        offset (int | Unset): Skol'ko elementov propustit'. Naprimer, dlja znachenija `10` otvet
            nachnetsja s 11 elementa Default: 0. Example: 5000.
        parent_id (int | Unset):  Example: 1000.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetContentV2ObjectAllResponse200 | GetContentV2ObjectAllResponse401 | GetContentV2ObjectAllResponse429
    """

    return sync_detailed(
        client=client,
        locale=locale,
        name=name,
        limit=limit,
        offset=offset,
        parent_id=parent_id,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    locale: str | Unset = UNSET,
    name: str | Unset = UNSET,
    limit: int | Unset = 30,
    offset: int | Unset = 0,
    parent_id: int | Unset = UNSET,
) -> Response[
    GetContentV2ObjectAllResponse200
    | GetContentV2ObjectAllResponse401
    | GetContentV2ObjectAllResponse429
]:
    r"""Spisok predmetov

     Metod vozvraschaet spisok nazvanij [roditel'skih kategorij predmetov](/openapi/work-with-
    products#tag/Kategorii-predmety-i-harakteristiki/paths/~1content~1v2~1object~1parent~1all/get) i ih
    predmetov s ID. Naprimer, u kategorii `Igrushki` budut predmety `Kalejdoskopy`, `Kukly`, `Mjachiki`.

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
        locale (str | Unset):  Example: en.
        name (str | Unset):  Example: Noski.
        limit (int | Unset): Kolichestvo predmetov, maksimum 1000 Default: 30. Example: 1000.
        offset (int | Unset): Skol'ko elementov propustit'. Naprimer, dlja znachenija `10` otvet
            nachnetsja s 11 elementa Default: 0. Example: 5000.
        parent_id (int | Unset):  Example: 1000.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetContentV2ObjectAllResponse200 | GetContentV2ObjectAllResponse401 | GetContentV2ObjectAllResponse429]
    """

    kwargs = _get_kwargs(
        locale=locale,
        name=name,
        limit=limit,
        offset=offset,
        parent_id=parent_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    locale: str | Unset = UNSET,
    name: str | Unset = UNSET,
    limit: int | Unset = 30,
    offset: int | Unset = 0,
    parent_id: int | Unset = UNSET,
) -> (
    GetContentV2ObjectAllResponse200
    | GetContentV2ObjectAllResponse401
    | GetContentV2ObjectAllResponse429
    | None
):
    r"""Spisok predmetov

     Metod vozvraschaet spisok nazvanij [roditel'skih kategorij predmetov](/openapi/work-with-
    products#tag/Kategorii-predmety-i-harakteristiki/paths/~1content~1v2~1object~1parent~1all/get) i ih
    predmetov s ID. Naprimer, u kategorii `Igrushki` budut predmety `Kalejdoskopy`, `Kukly`, `Mjachiki`.

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
        locale (str | Unset):  Example: en.
        name (str | Unset):  Example: Noski.
        limit (int | Unset): Kolichestvo predmetov, maksimum 1000 Default: 30. Example: 1000.
        offset (int | Unset): Skol'ko elementov propustit'. Naprimer, dlja znachenija `10` otvet
            nachnetsja s 11 elementa Default: 0. Example: 5000.
        parent_id (int | Unset):  Example: 1000.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetContentV2ObjectAllResponse200 | GetContentV2ObjectAllResponse401 | GetContentV2ObjectAllResponse429
    """

    return (
        await asyncio_detailed(
            client=client,
            locale=locale,
            name=name,
            limit=limit,
            offset=offset,
            parent_id=parent_id,
        )
    ).parsed
