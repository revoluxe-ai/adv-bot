from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_adv_v2_seacat_save_ad_body import PostAdvV2SeacatSaveAdBody
from ...types import Response


def _get_kwargs(
    *,
    body: PostAdvV2SeacatSaveAdBody,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": "/adv/v2/seacat/save-ad",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, int, str]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = cast(int, response.json())
        return response_200
    if response.status_code == HTTPStatus.BAD_REQUEST:
        response_400 = cast(str, response.json())
        return response_400
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        response_401 = cast(Any, None)
        return response_401
    if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
        response_429 = cast(Any, None)
        return response_429
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[Any, int, str]]:
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
) -> Response[Union[Any, int, str]]:
    r"""Sozdat' kampaniju

     Metod sozdaet kampaniju:
      - s ruchnoj stavkoj dlja prodvizhenija tovarov v poiske i/ili rekomendatsijah
      - s edinoj stavkoj dlja prodvizhenija tovarov odnovremenno v poiske i rekomendatsijah

    Tip vseh sozdannyh etim metodom kampanij — `9`.

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
        Response[Union[Any, int, str]]
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
) -> Optional[Union[Any, int, str]]:
    r"""Sozdat' kampaniju

     Metod sozdaet kampaniju:
      - s ruchnoj stavkoj dlja prodvizhenija tovarov v poiske i/ili rekomendatsijah
      - s edinoj stavkoj dlja prodvizhenija tovarov odnovremenno v poiske i rekomendatsijah

    Tip vseh sozdannyh etim metodom kampanij — `9`.

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
        Union[Any, int, str]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PostAdvV2SeacatSaveAdBody,
) -> Response[Union[Any, int, str]]:
    r"""Sozdat' kampaniju

     Metod sozdaet kampaniju:
      - s ruchnoj stavkoj dlja prodvizhenija tovarov v poiske i/ili rekomendatsijah
      - s edinoj stavkoj dlja prodvizhenija tovarov odnovremenno v poiske i rekomendatsijah

    Tip vseh sozdannyh etim metodom kampanij — `9`.

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
        Response[Union[Any, int, str]]
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
) -> Optional[Union[Any, int, str]]:
    r"""Sozdat' kampaniju

     Metod sozdaet kampaniju:
      - s ruchnoj stavkoj dlja prodvizhenija tovarov v poiske i/ili rekomendatsijah
      - s edinoj stavkoj dlja prodvizhenija tovarov odnovremenno v poiske i rekomendatsijah

    Tip vseh sozdannyh etim metodom kampanij — `9`.

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
        Union[Any, int, str]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
