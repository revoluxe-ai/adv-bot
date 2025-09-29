from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_adv_v1_search_set_plus_body import PostAdvV1SearchSetPlusBody
from ...models.post_adv_v1_search_set_plus_response_401 import (
    PostAdvV1SearchSetPlusResponse401,
)
from ...models.post_adv_v1_search_set_plus_response_429 import (
    PostAdvV1SearchSetPlusResponse429,
)
from ...types import UNSET, Response


def _get_kwargs(
    *,
    body: PostAdvV1SearchSetPlusBody,
    id: int,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    params["id"] = id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/adv/v1/search/set-plus",
        "params": params,
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[
        PostAdvV1SearchSetPlusResponse401,
        PostAdvV1SearchSetPlusResponse429,
        list[str],
        str,
    ]
]:
    if response.status_code == 200:
        response_200 = cast(list[str], response.json())

        return response_200

    if response.status_code == 400:
        response_400 = response.text
        return response_400

    if response.status_code == 401:
        response_401 = PostAdvV1SearchSetPlusResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = PostAdvV1SearchSetPlusResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[
    Union[
        PostAdvV1SearchSetPlusResponse401,
        PostAdvV1SearchSetPlusResponse429,
        list[str],
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
    body: PostAdvV1SearchSetPlusBody,
    id: int,
) -> Response[
    Union[
        PostAdvV1SearchSetPlusResponse401,
        PostAdvV1SearchSetPlusResponse429,
        list[str],
        str,
    ]
]:
    r"""Ustanovka/udalenie fiksirovannyh fraz

     Metod ustanavlivaet i udaljaet fiksirovannye frazy v kampanijah [s ruchnoj
    stavkoj](/openapi/promotion#tag/Sozdanie-kampanij/paths/~1adv~1v2~1seacat~1save-ad/post).
    Fiksirovannye frazy mozhno vybrat' v spiske kljuchevyh fraz kampanii, kotoryj formiruetsja posle
    zapuska.<br><br>

    Otpravka pustogo massiva v metode udaljaet vse fiksirovannye frazy i otkljuchaet
    [aktivnost'](/openapi/promotion#tag/Parametry-kampanij/paths/~1adv~1v1~1search~1set-plus/get) vseh
    fiksirovannyh fraz kampanii.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 500 millisekund | 1 zapros | 500 millisekund | 5 zaprosov |
    </div>

    Args:
        id (int):  Example: 1234567.
        body (PostAdvV1SearchSetPlusBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[PostAdvV1SearchSetPlusResponse401, PostAdvV1SearchSetPlusResponse429, list[str], str]]
    """

    kwargs = _get_kwargs(
        body=body,
        id=id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    body: PostAdvV1SearchSetPlusBody,
    id: int,
) -> Optional[
    Union[
        PostAdvV1SearchSetPlusResponse401,
        PostAdvV1SearchSetPlusResponse429,
        list[str],
        str,
    ]
]:
    r"""Ustanovka/udalenie fiksirovannyh fraz

     Metod ustanavlivaet i udaljaet fiksirovannye frazy v kampanijah [s ruchnoj
    stavkoj](/openapi/promotion#tag/Sozdanie-kampanij/paths/~1adv~1v2~1seacat~1save-ad/post).
    Fiksirovannye frazy mozhno vybrat' v spiske kljuchevyh fraz kampanii, kotoryj formiruetsja posle
    zapuska.<br><br>

    Otpravka pustogo massiva v metode udaljaet vse fiksirovannye frazy i otkljuchaet
    [aktivnost'](/openapi/promotion#tag/Parametry-kampanij/paths/~1adv~1v1~1search~1set-plus/get) vseh
    fiksirovannyh fraz kampanii.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 500 millisekund | 1 zapros | 500 millisekund | 5 zaprosov |
    </div>

    Args:
        id (int):  Example: 1234567.
        body (PostAdvV1SearchSetPlusBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[PostAdvV1SearchSetPlusResponse401, PostAdvV1SearchSetPlusResponse429, list[str], str]
    """

    return sync_detailed(
        client=client,
        body=body,
        id=id,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PostAdvV1SearchSetPlusBody,
    id: int,
) -> Response[
    Union[
        PostAdvV1SearchSetPlusResponse401,
        PostAdvV1SearchSetPlusResponse429,
        list[str],
        str,
    ]
]:
    r"""Ustanovka/udalenie fiksirovannyh fraz

     Metod ustanavlivaet i udaljaet fiksirovannye frazy v kampanijah [s ruchnoj
    stavkoj](/openapi/promotion#tag/Sozdanie-kampanij/paths/~1adv~1v2~1seacat~1save-ad/post).
    Fiksirovannye frazy mozhno vybrat' v spiske kljuchevyh fraz kampanii, kotoryj formiruetsja posle
    zapuska.<br><br>

    Otpravka pustogo massiva v metode udaljaet vse fiksirovannye frazy i otkljuchaet
    [aktivnost'](/openapi/promotion#tag/Parametry-kampanij/paths/~1adv~1v1~1search~1set-plus/get) vseh
    fiksirovannyh fraz kampanii.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 500 millisekund | 1 zapros | 500 millisekund | 5 zaprosov |
    </div>

    Args:
        id (int):  Example: 1234567.
        body (PostAdvV1SearchSetPlusBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[PostAdvV1SearchSetPlusResponse401, PostAdvV1SearchSetPlusResponse429, list[str], str]]
    """

    kwargs = _get_kwargs(
        body=body,
        id=id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: PostAdvV1SearchSetPlusBody,
    id: int,
) -> Optional[
    Union[
        PostAdvV1SearchSetPlusResponse401,
        PostAdvV1SearchSetPlusResponse429,
        list[str],
        str,
    ]
]:
    r"""Ustanovka/udalenie fiksirovannyh fraz

     Metod ustanavlivaet i udaljaet fiksirovannye frazy v kampanijah [s ruchnoj
    stavkoj](/openapi/promotion#tag/Sozdanie-kampanij/paths/~1adv~1v2~1seacat~1save-ad/post).
    Fiksirovannye frazy mozhno vybrat' v spiske kljuchevyh fraz kampanii, kotoryj formiruetsja posle
    zapuska.<br><br>

    Otpravka pustogo massiva v metode udaljaet vse fiksirovannye frazy i otkljuchaet
    [aktivnost'](/openapi/promotion#tag/Parametry-kampanij/paths/~1adv~1v1~1search~1set-plus/get) vseh
    fiksirovannyh fraz kampanii.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 500 millisekund | 1 zapros | 500 millisekund | 5 zaprosov |
    </div>

    Args:
        id (int):  Example: 1234567.
        body (PostAdvV1SearchSetPlusBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[PostAdvV1SearchSetPlusResponse401, PostAdvV1SearchSetPlusResponse429, list[str], str]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            id=id,
        )
    ).parsed
