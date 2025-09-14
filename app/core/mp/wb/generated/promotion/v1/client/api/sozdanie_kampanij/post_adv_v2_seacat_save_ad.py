from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_adv_v2_seacat_save_ad_body import PostAdvV2SeacatSaveAdBody
from ...models.post_adv_v2_seacat_save_ad_response_401 import (
    PostAdvV2SeacatSaveAdResponse401,
)
from ...models.post_adv_v2_seacat_save_ad_response_429 import (
    PostAdvV2SeacatSaveAdResponse429,
)
from ...types import Response


def _get_kwargs(
    *,
    body: PostAdvV2SeacatSaveAdBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/adv/v2/seacat/save-ad",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[PostAdvV2SeacatSaveAdResponse401, PostAdvV2SeacatSaveAdResponse429, int, str]
]:
    if response.status_code == 200:
        response_200 = cast(int, response.text)
        return response_200

    if response.status_code == 400:
        response_400 = response.text
        return response_400

    if response.status_code == 401:
        response_401 = PostAdvV2SeacatSaveAdResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = PostAdvV2SeacatSaveAdResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[
    Union[PostAdvV2SeacatSaveAdResponse401, PostAdvV2SeacatSaveAdResponse429, int, str]
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
    body: PostAdvV2SeacatSaveAdBody,
) -> Response[
    Union[PostAdvV2SeacatSaveAdResponse401, PostAdvV2SeacatSaveAdResponse429, int, str]
]:
    r"""Sozdat' kampaniju s ruchnoj stavkoj

     Metod sozdaet kampaniju [s ruchnoj
    stavkoj](/openapi/promotion#tag/Kampanii/paths/~1adv~1v0~1auction~1adverts/get) dlja prodvizhenija
    tovarov v rezul'tatah poiska WB.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 5 zaprosov | 12 sekund | 5 zaprosov |
    </div>

    Args:
        body (PostAdvV2SeacatSaveAdBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[PostAdvV2SeacatSaveAdResponse401, PostAdvV2SeacatSaveAdResponse429, int, str]]
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
    body: PostAdvV2SeacatSaveAdBody,
) -> Optional[
    Union[PostAdvV2SeacatSaveAdResponse401, PostAdvV2SeacatSaveAdResponse429, int, str]
]:
    r"""Sozdat' kampaniju s ruchnoj stavkoj

     Metod sozdaet kampaniju [s ruchnoj
    stavkoj](/openapi/promotion#tag/Kampanii/paths/~1adv~1v0~1auction~1adverts/get) dlja prodvizhenija
    tovarov v rezul'tatah poiska WB.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 5 zaprosov | 12 sekund | 5 zaprosov |
    </div>

    Args:
        body (PostAdvV2SeacatSaveAdBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[PostAdvV2SeacatSaveAdResponse401, PostAdvV2SeacatSaveAdResponse429, int, str]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PostAdvV2SeacatSaveAdBody,
) -> Response[
    Union[PostAdvV2SeacatSaveAdResponse401, PostAdvV2SeacatSaveAdResponse429, int, str]
]:
    r"""Sozdat' kampaniju s ruchnoj stavkoj

     Metod sozdaet kampaniju [s ruchnoj
    stavkoj](/openapi/promotion#tag/Kampanii/paths/~1adv~1v0~1auction~1adverts/get) dlja prodvizhenija
    tovarov v rezul'tatah poiska WB.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 5 zaprosov | 12 sekund | 5 zaprosov |
    </div>

    Args:
        body (PostAdvV2SeacatSaveAdBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[PostAdvV2SeacatSaveAdResponse401, PostAdvV2SeacatSaveAdResponse429, int, str]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: PostAdvV2SeacatSaveAdBody,
) -> Optional[
    Union[PostAdvV2SeacatSaveAdResponse401, PostAdvV2SeacatSaveAdResponse429, int, str]
]:
    r"""Sozdat' kampaniju s ruchnoj stavkoj

     Metod sozdaet kampaniju [s ruchnoj
    stavkoj](/openapi/promotion#tag/Kampanii/paths/~1adv~1v0~1auction~1adverts/get) dlja prodvizhenija
    tovarov v rezul'tatah poiska WB.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 5 zaprosov | 12 sekund | 5 zaprosov |
    </div>

    Args:
        body (PostAdvV2SeacatSaveAdBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[PostAdvV2SeacatSaveAdResponse401, PostAdvV2SeacatSaveAdResponse429, int, str]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
