from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_adv_v1_save_ad_body import PostAdvV1SaveAdBody
from ...models.post_adv_v1_save_ad_response_400 import PostAdvV1SaveAdResponse400
from ...models.post_adv_v1_save_ad_response_401 import PostAdvV1SaveAdResponse401
from ...models.post_adv_v1_save_ad_response_422 import PostAdvV1SaveAdResponse422
from ...models.post_adv_v1_save_ad_response_429 import PostAdvV1SaveAdResponse429
from ...types import Response


def _get_kwargs(
    *,
    body: PostAdvV1SaveAdBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/adv/v1/save-ad",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[
        PostAdvV1SaveAdResponse400,
        PostAdvV1SaveAdResponse401,
        PostAdvV1SaveAdResponse422,
        PostAdvV1SaveAdResponse429,
        str,
    ]
]:
    if response.status_code == 200:
        response_200 = cast(str, response.json())
        return response_200

    if response.status_code == 400:
        response_400 = PostAdvV1SaveAdResponse400.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostAdvV1SaveAdResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 422:
        response_422 = PostAdvV1SaveAdResponse422.from_dict(response.json())

        return response_422

    if response.status_code == 429:
        response_429 = PostAdvV1SaveAdResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[
    Union[
        PostAdvV1SaveAdResponse400,
        PostAdvV1SaveAdResponse401,
        PostAdvV1SaveAdResponse422,
        PostAdvV1SaveAdResponse429,
        str,
    ]
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
    body: PostAdvV1SaveAdBody,
) -> Response[
    Union[
        PostAdvV1SaveAdResponse400,
        PostAdvV1SaveAdResponse401,
        PostAdvV1SaveAdResponse422,
        PostAdvV1SaveAdResponse429,
        str,
    ]
]:
    r"""Sozdat' kampaniju s edinoj stavkoj

     Metod sozdaet kampaniju [s edinoj
    stavkoj](/openapi/promotion#tag/Kampanii/paths/~1adv~1v1~1promotion~1adverts/post) dlja
    prodvizhenija tovarov v:
      - kataloge
      - poiske
      - kartochkah tovarov
      - rekomendatsijah na glavnoj stranitse WB

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 20 sekund | 1 zapros | 20 sekund | 5 zaprosov |
    </div>

    Args:
        body (PostAdvV1SaveAdBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[PostAdvV1SaveAdResponse400, PostAdvV1SaveAdResponse401, PostAdvV1SaveAdResponse422, PostAdvV1SaveAdResponse429, str]]
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
    body: PostAdvV1SaveAdBody,
) -> Optional[
    Union[
        PostAdvV1SaveAdResponse400,
        PostAdvV1SaveAdResponse401,
        PostAdvV1SaveAdResponse422,
        PostAdvV1SaveAdResponse429,
        str,
    ]
]:
    r"""Sozdat' kampaniju s edinoj stavkoj

     Metod sozdaet kampaniju [s edinoj
    stavkoj](/openapi/promotion#tag/Kampanii/paths/~1adv~1v1~1promotion~1adverts/post) dlja
    prodvizhenija tovarov v:
      - kataloge
      - poiske
      - kartochkah tovarov
      - rekomendatsijah na glavnoj stranitse WB

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 20 sekund | 1 zapros | 20 sekund | 5 zaprosov |
    </div>

    Args:
        body (PostAdvV1SaveAdBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[PostAdvV1SaveAdResponse400, PostAdvV1SaveAdResponse401, PostAdvV1SaveAdResponse422, PostAdvV1SaveAdResponse429, str]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PostAdvV1SaveAdBody,
) -> Response[
    Union[
        PostAdvV1SaveAdResponse400,
        PostAdvV1SaveAdResponse401,
        PostAdvV1SaveAdResponse422,
        PostAdvV1SaveAdResponse429,
        str,
    ]
]:
    r"""Sozdat' kampaniju s edinoj stavkoj

     Metod sozdaet kampaniju [s edinoj
    stavkoj](/openapi/promotion#tag/Kampanii/paths/~1adv~1v1~1promotion~1adverts/post) dlja
    prodvizhenija tovarov v:
      - kataloge
      - poiske
      - kartochkah tovarov
      - rekomendatsijah na glavnoj stranitse WB

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 20 sekund | 1 zapros | 20 sekund | 5 zaprosov |
    </div>

    Args:
        body (PostAdvV1SaveAdBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[PostAdvV1SaveAdResponse400, PostAdvV1SaveAdResponse401, PostAdvV1SaveAdResponse422, PostAdvV1SaveAdResponse429, str]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: PostAdvV1SaveAdBody,
) -> Optional[
    Union[
        PostAdvV1SaveAdResponse400,
        PostAdvV1SaveAdResponse401,
        PostAdvV1SaveAdResponse422,
        PostAdvV1SaveAdResponse429,
        str,
    ]
]:
    r"""Sozdat' kampaniju s edinoj stavkoj

     Metod sozdaet kampaniju [s edinoj
    stavkoj](/openapi/promotion#tag/Kampanii/paths/~1adv~1v1~1promotion~1adverts/post) dlja
    prodvizhenija tovarov v:
      - kataloge
      - poiske
      - kartochkah tovarov
      - rekomendatsijah na glavnoj stranitse WB

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 20 sekund | 1 zapros | 20 sekund | 5 zaprosov |
    </div>

    Args:
        body (PostAdvV1SaveAdBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[PostAdvV1SaveAdResponse400, PostAdvV1SaveAdResponse401, PostAdvV1SaveAdResponse422, PostAdvV1SaveAdResponse429, str]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
