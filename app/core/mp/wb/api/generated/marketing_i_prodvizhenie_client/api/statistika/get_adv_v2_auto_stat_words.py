from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_adv_v2_auto_stat_words_response_200 import GetAdvV2AutoStatWordsResponse200
from ...models.response_adv_error_1 import ResponseAdvError1
from ...types import UNSET, Response


def _get_kwargs(
    *,
    id: int,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    params["id"] = id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": "/adv/v2/auto/stat-words",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, GetAdvV2AutoStatWordsResponse200, ResponseAdvError1]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = GetAdvV2AutoStatWordsResponse200.from_dict(response.json())

        return response_200
    if response.status_code == HTTPStatus.NO_CONTENT:
        response_204 = cast(Any, None)
        return response_204
    if response.status_code == HTTPStatus.BAD_REQUEST:
        response_400 = ResponseAdvError1.from_dict(response.json())

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
) -> Response[Union[Any, GetAdvV2AutoStatWordsResponse200, ResponseAdvError1]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    id: int,
) -> Response[Union[Any, GetAdvV2AutoStatWordsResponse200, ResponseAdvError1]]:
    r"""Statistika kampanii s edinoj stavkoj po klasteram fraz

     Metod formiruet klastery kljuchevyh — to est', nabory pohozhih — fraz iz poiskovoj stroki, esli po
    nim hotja by odin raz byli pokazany tovary iz kampanii. V otvete metoda takzhe ukazano kolichestvo
    pokazov etih tovarov.
    <br><br>
    Informatsija obnovljaetsja kazhdye 15 minut.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 4 zaprosa | 250 millisekund | 4 zaprosa |
    </div>

    Args:
        id (int):  Example: 1234.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, GetAdvV2AutoStatWordsResponse200, ResponseAdvError1]]
    """

    kwargs = _get_kwargs(
        id=id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    id: int,
) -> Optional[Union[Any, GetAdvV2AutoStatWordsResponse200, ResponseAdvError1]]:
    r"""Statistika kampanii s edinoj stavkoj po klasteram fraz

     Metod formiruet klastery kljuchevyh — to est', nabory pohozhih — fraz iz poiskovoj stroki, esli po
    nim hotja by odin raz byli pokazany tovary iz kampanii. V otvete metoda takzhe ukazano kolichestvo
    pokazov etih tovarov.
    <br><br>
    Informatsija obnovljaetsja kazhdye 15 minut.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 4 zaprosa | 250 millisekund | 4 zaprosa |
    </div>

    Args:
        id (int):  Example: 1234.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, GetAdvV2AutoStatWordsResponse200, ResponseAdvError1]
    """

    return sync_detailed(
        client=client,
        id=id,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    id: int,
) -> Response[Union[Any, GetAdvV2AutoStatWordsResponse200, ResponseAdvError1]]:
    r"""Statistika kampanii s edinoj stavkoj po klasteram fraz

     Metod formiruet klastery kljuchevyh — to est', nabory pohozhih — fraz iz poiskovoj stroki, esli po
    nim hotja by odin raz byli pokazany tovary iz kampanii. V otvete metoda takzhe ukazano kolichestvo
    pokazov etih tovarov.
    <br><br>
    Informatsija obnovljaetsja kazhdye 15 minut.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 4 zaprosa | 250 millisekund | 4 zaprosa |
    </div>

    Args:
        id (int):  Example: 1234.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, GetAdvV2AutoStatWordsResponse200, ResponseAdvError1]]
    """

    kwargs = _get_kwargs(
        id=id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    id: int,
) -> Optional[Union[Any, GetAdvV2AutoStatWordsResponse200, ResponseAdvError1]]:
    r"""Statistika kampanii s edinoj stavkoj po klasteram fraz

     Metod formiruet klastery kljuchevyh — to est', nabory pohozhih — fraz iz poiskovoj stroki, esli po
    nim hotja by odin raz byli pokazany tovary iz kampanii. V otvete metoda takzhe ukazano kolichestvo
    pokazov etih tovarov.
    <br><br>
    Informatsija obnovljaetsja kazhdye 15 minut.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 4 zaprosa | 250 millisekund | 4 zaprosa |
    </div>

    Args:
        id (int):  Example: 1234.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, GetAdvV2AutoStatWordsResponse200, ResponseAdvError1]
    """

    return (
        await asyncio_detailed(
            client=client,
            id=id,
        )
    ).parsed
