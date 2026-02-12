from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_content_v2_tag_nomenclature_link_body import (
    PostContentV2TagNomenclatureLinkBody,
)
from ...models.post_content_v2_tag_nomenclature_link_response_401 import (
    PostContentV2TagNomenclatureLinkResponse401,
)
from ...models.post_content_v2_tag_nomenclature_link_response_429 import (
    PostContentV2TagNomenclatureLinkResponse429,
)
from ...models.response_body_content_error_403 import ResponseBodyContentError403
from ...models.response_content_error import ResponseContentError
from ...types import Response


def _get_kwargs(
    *,
    body: PostContentV2TagNomenclatureLinkBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/content/v2/tag/nomenclature/link",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    PostContentV2TagNomenclatureLinkResponse401
    | PostContentV2TagNomenclatureLinkResponse429
    | ResponseBodyContentError403
    | ResponseContentError
    | None
):
    if response.status_code == 200:
        response_200 = ResponseContentError.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = ResponseContentError.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostContentV2TagNomenclatureLinkResponse401.from_dict(
            response.json()
        )

        return response_401

    if response.status_code == 403:
        response_403 = ResponseBodyContentError403.from_dict(response.json())

        return response_403

    if response.status_code == 429:
        response_429 = PostContentV2TagNomenclatureLinkResponse429.from_dict(
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
    PostContentV2TagNomenclatureLinkResponse401
    | PostContentV2TagNomenclatureLinkResponse429
    | ResponseBodyContentError403
    | ResponseContentError
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
    body: PostContentV2TagNomenclatureLinkBody,
) -> Response[
    PostContentV2TagNomenclatureLinkResponse401
    | PostContentV2TagNomenclatureLinkResponse429
    | ResponseBodyContentError403
    | ResponseContentError
]:
    r"""Upravlenie jarlykami v kartochke tovara

     Metod dobavljaet ili snimaet jarlyk s kartochki tovara. K kartochke mozhno dobavit' maksimum 15
    jarlykov.<br>
    Pri udalenii jarlyka iz kartochki tovara on ne udaljaetsja iz [spiska jarlykov](/openapi/work-with-
    products#tag/Yarlyki/paths/~1content~1v2~1tags/get) prodavtsa.

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
        body (PostContentV2TagNomenclatureLinkBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostContentV2TagNomenclatureLinkResponse401 | PostContentV2TagNomenclatureLinkResponse429 | ResponseBodyContentError403 | ResponseContentError]
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
    body: PostContentV2TagNomenclatureLinkBody,
) -> (
    PostContentV2TagNomenclatureLinkResponse401
    | PostContentV2TagNomenclatureLinkResponse429
    | ResponseBodyContentError403
    | ResponseContentError
    | None
):
    r"""Upravlenie jarlykami v kartochke tovara

     Metod dobavljaet ili snimaet jarlyk s kartochki tovara. K kartochke mozhno dobavit' maksimum 15
    jarlykov.<br>
    Pri udalenii jarlyka iz kartochki tovara on ne udaljaetsja iz [spiska jarlykov](/openapi/work-with-
    products#tag/Yarlyki/paths/~1content~1v2~1tags/get) prodavtsa.

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
        body (PostContentV2TagNomenclatureLinkBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostContentV2TagNomenclatureLinkResponse401 | PostContentV2TagNomenclatureLinkResponse429 | ResponseBodyContentError403 | ResponseContentError
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PostContentV2TagNomenclatureLinkBody,
) -> Response[
    PostContentV2TagNomenclatureLinkResponse401
    | PostContentV2TagNomenclatureLinkResponse429
    | ResponseBodyContentError403
    | ResponseContentError
]:
    r"""Upravlenie jarlykami v kartochke tovara

     Metod dobavljaet ili snimaet jarlyk s kartochki tovara. K kartochke mozhno dobavit' maksimum 15
    jarlykov.<br>
    Pri udalenii jarlyka iz kartochki tovara on ne udaljaetsja iz [spiska jarlykov](/openapi/work-with-
    products#tag/Yarlyki/paths/~1content~1v2~1tags/get) prodavtsa.

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
        body (PostContentV2TagNomenclatureLinkBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostContentV2TagNomenclatureLinkResponse401 | PostContentV2TagNomenclatureLinkResponse429 | ResponseBodyContentError403 | ResponseContentError]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: PostContentV2TagNomenclatureLinkBody,
) -> (
    PostContentV2TagNomenclatureLinkResponse401
    | PostContentV2TagNomenclatureLinkResponse429
    | ResponseBodyContentError403
    | ResponseContentError
    | None
):
    r"""Upravlenie jarlykami v kartochke tovara

     Metod dobavljaet ili snimaet jarlyk s kartochki tovara. K kartochke mozhno dobavit' maksimum 15
    jarlykov.<br>
    Pri udalenii jarlyka iz kartochki tovara on ne udaljaetsja iz [spiska jarlykov](/openapi/work-with-
    products#tag/Yarlyki/paths/~1content~1v2~1tags/get) prodavtsa.

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
        body (PostContentV2TagNomenclatureLinkBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostContentV2TagNomenclatureLinkResponse401 | PostContentV2TagNomenclatureLinkResponse429 | ResponseBodyContentError403 | ResponseContentError
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
