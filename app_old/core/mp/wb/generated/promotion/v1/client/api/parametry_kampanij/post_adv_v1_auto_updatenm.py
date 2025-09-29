from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_adv_v1_auto_updatenm_body import PostAdvV1AutoUpdatenmBody
from ...models.post_adv_v1_auto_updatenm_response_401 import (
    PostAdvV1AutoUpdatenmResponse401,
)
from ...models.post_adv_v1_auto_updatenm_response_429 import (
    PostAdvV1AutoUpdatenmResponse429,
)
from ...models.response_adv_error_1 import ResponseAdvError1
from ...types import UNSET, Response


def _get_kwargs(
    *,
    body: PostAdvV1AutoUpdatenmBody,
    id: int,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    params["id"] = id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/adv/v1/auto/updatenm",
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
        Any,
        PostAdvV1AutoUpdatenmResponse401,
        PostAdvV1AutoUpdatenmResponse429,
        ResponseAdvError1,
    ]
]:
    if response.status_code == 200:
        response_200 = cast(Any, None)
        return response_200

    if response.status_code == 400:
        response_400 = ResponseAdvError1.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostAdvV1AutoUpdatenmResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = PostAdvV1AutoUpdatenmResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[
    Union[
        Any,
        PostAdvV1AutoUpdatenmResponse401,
        PostAdvV1AutoUpdatenmResponse429,
        ResponseAdvError1,
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
    body: PostAdvV1AutoUpdatenmBody,
    id: int,
) -> Response[
    Union[
        Any,
        PostAdvV1AutoUpdatenmResponse401,
        PostAdvV1AutoUpdatenmResponse429,
        ResponseAdvError1,
    ]
]:
    r"""Izmenenie spiska kartochek tovarov v kampanii s edinoj stavkoj

     Metod dobavljaet i udaljaet kartochki tovarov v kampanii s edinoj stavkoj.<br><br>

    <div class=\"description_important\">
      Dobavit' mozhno tol'ko te kartochki tovarov, kotorye vernutsja v <a
    href=\"/openapi/promotion#tag/Parametry-avtomaticheskih-
    kampanij/paths/~1adv~1v1~1auto~1getnmtoadd/get\">spiske kartochek tovarov dlja kampanii s edinoj
    stavkoj</a>.<br>Udalit' edinstvennuju kartochku tovara iz kampanii nel'zja.
    </div>

    Proverki po parametru `delete` ne predusmotreno.

    Esli prishel otvet so status-kodom `200`, a izmenenij ne proizoshlo, prover'te, chtoby zapros
    sootvetstvoval dokumentatsii.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 60 zaprosov | 1 sekunda | 5 zaprosov |
    </div>

    Args:
        id (int):  Example: 1.
        body (PostAdvV1AutoUpdatenmBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, PostAdvV1AutoUpdatenmResponse401, PostAdvV1AutoUpdatenmResponse429, ResponseAdvError1]]
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
    body: PostAdvV1AutoUpdatenmBody,
    id: int,
) -> Optional[
    Union[
        Any,
        PostAdvV1AutoUpdatenmResponse401,
        PostAdvV1AutoUpdatenmResponse429,
        ResponseAdvError1,
    ]
]:
    r"""Izmenenie spiska kartochek tovarov v kampanii s edinoj stavkoj

     Metod dobavljaet i udaljaet kartochki tovarov v kampanii s edinoj stavkoj.<br><br>

    <div class=\"description_important\">
      Dobavit' mozhno tol'ko te kartochki tovarov, kotorye vernutsja v <a
    href=\"/openapi/promotion#tag/Parametry-avtomaticheskih-
    kampanij/paths/~1adv~1v1~1auto~1getnmtoadd/get\">spiske kartochek tovarov dlja kampanii s edinoj
    stavkoj</a>.<br>Udalit' edinstvennuju kartochku tovara iz kampanii nel'zja.
    </div>

    Proverki po parametru `delete` ne predusmotreno.

    Esli prishel otvet so status-kodom `200`, a izmenenij ne proizoshlo, prover'te, chtoby zapros
    sootvetstvoval dokumentatsii.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 60 zaprosov | 1 sekunda | 5 zaprosov |
    </div>

    Args:
        id (int):  Example: 1.
        body (PostAdvV1AutoUpdatenmBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, PostAdvV1AutoUpdatenmResponse401, PostAdvV1AutoUpdatenmResponse429, ResponseAdvError1]
    """

    return sync_detailed(
        client=client,
        body=body,
        id=id,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PostAdvV1AutoUpdatenmBody,
    id: int,
) -> Response[
    Union[
        Any,
        PostAdvV1AutoUpdatenmResponse401,
        PostAdvV1AutoUpdatenmResponse429,
        ResponseAdvError1,
    ]
]:
    r"""Izmenenie spiska kartochek tovarov v kampanii s edinoj stavkoj

     Metod dobavljaet i udaljaet kartochki tovarov v kampanii s edinoj stavkoj.<br><br>

    <div class=\"description_important\">
      Dobavit' mozhno tol'ko te kartochki tovarov, kotorye vernutsja v <a
    href=\"/openapi/promotion#tag/Parametry-avtomaticheskih-
    kampanij/paths/~1adv~1v1~1auto~1getnmtoadd/get\">spiske kartochek tovarov dlja kampanii s edinoj
    stavkoj</a>.<br>Udalit' edinstvennuju kartochku tovara iz kampanii nel'zja.
    </div>

    Proverki po parametru `delete` ne predusmotreno.

    Esli prishel otvet so status-kodom `200`, a izmenenij ne proizoshlo, prover'te, chtoby zapros
    sootvetstvoval dokumentatsii.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 60 zaprosov | 1 sekunda | 5 zaprosov |
    </div>

    Args:
        id (int):  Example: 1.
        body (PostAdvV1AutoUpdatenmBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, PostAdvV1AutoUpdatenmResponse401, PostAdvV1AutoUpdatenmResponse429, ResponseAdvError1]]
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
    body: PostAdvV1AutoUpdatenmBody,
    id: int,
) -> Optional[
    Union[
        Any,
        PostAdvV1AutoUpdatenmResponse401,
        PostAdvV1AutoUpdatenmResponse429,
        ResponseAdvError1,
    ]
]:
    r"""Izmenenie spiska kartochek tovarov v kampanii s edinoj stavkoj

     Metod dobavljaet i udaljaet kartochki tovarov v kampanii s edinoj stavkoj.<br><br>

    <div class=\"description_important\">
      Dobavit' mozhno tol'ko te kartochki tovarov, kotorye vernutsja v <a
    href=\"/openapi/promotion#tag/Parametry-avtomaticheskih-
    kampanij/paths/~1adv~1v1~1auto~1getnmtoadd/get\">spiske kartochek tovarov dlja kampanii s edinoj
    stavkoj</a>.<br>Udalit' edinstvennuju kartochku tovara iz kampanii nel'zja.
    </div>

    Proverki po parametru `delete` ne predusmotreno.

    Esli prishel otvet so status-kodom `200`, a izmenenij ne proizoshlo, prover'te, chtoby zapros
    sootvetstvoval dokumentatsii.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 60 zaprosov | 1 sekunda | 5 zaprosov |
    </div>

    Args:
        id (int):  Example: 1.
        body (PostAdvV1AutoUpdatenmBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, PostAdvV1AutoUpdatenmResponse401, PostAdvV1AutoUpdatenmResponse429, ResponseAdvError1]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            id=id,
        )
    ).parsed
