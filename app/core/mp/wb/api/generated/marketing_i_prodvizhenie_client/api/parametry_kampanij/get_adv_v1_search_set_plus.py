from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    id: int,
    fixed: Union[Unset, bool] = UNSET,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    params["id"] = id

    params["fixed"] = fixed

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": "/adv/v1/search/set-plus",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, str]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = cast(Any, None)
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
) -> Response[Union[Any, str]]:
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
    fixed: Union[Unset, bool] = UNSET,
) -> Response[Union[Any, str]]:
    r"""Upravlenie aktivnost'ju fiksirovannyh fraz

     Metod delaet aktivnymi ili neaktivnymi fiksirovannye frazy v kampanijah [s ruchnoj
    stavkoj](/openapi/promotion#tag/Sozdanie-kampanij/paths/~1adv~1v2~1seacat~1save-ad/post).
    Fiksirovannye frazy nuzhny, chtoby tovar otobrazhalsja v poiske tol'ko po opredelennym poiskovym
    zaprosam.<br><br>

    Ustanovit' ili udalit' fiksirovannye frazy mozhno cherez [otdel'nyj
    metod](/openapi/promotion#tag/Parametry-kampanij/paths/~1adv~1v1~1search~1set-plus/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 500 millisekund | 1 zapros | 500 millisekund | 5 zaprosov |
    </div>

    Args:
        id (int):  Example: 1234567.
        fixed (Union[Unset, bool]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, str]]
    """

    kwargs = _get_kwargs(
        id=id,
        fixed=fixed,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    id: int,
    fixed: Union[Unset, bool] = UNSET,
) -> Optional[Union[Any, str]]:
    r"""Upravlenie aktivnost'ju fiksirovannyh fraz

     Metod delaet aktivnymi ili neaktivnymi fiksirovannye frazy v kampanijah [s ruchnoj
    stavkoj](/openapi/promotion#tag/Sozdanie-kampanij/paths/~1adv~1v2~1seacat~1save-ad/post).
    Fiksirovannye frazy nuzhny, chtoby tovar otobrazhalsja v poiske tol'ko po opredelennym poiskovym
    zaprosam.<br><br>

    Ustanovit' ili udalit' fiksirovannye frazy mozhno cherez [otdel'nyj
    metod](/openapi/promotion#tag/Parametry-kampanij/paths/~1adv~1v1~1search~1set-plus/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 500 millisekund | 1 zapros | 500 millisekund | 5 zaprosov |
    </div>

    Args:
        id (int):  Example: 1234567.
        fixed (Union[Unset, bool]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, str]
    """

    return sync_detailed(
        client=client,
        id=id,
        fixed=fixed,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    id: int,
    fixed: Union[Unset, bool] = UNSET,
) -> Response[Union[Any, str]]:
    r"""Upravlenie aktivnost'ju fiksirovannyh fraz

     Metod delaet aktivnymi ili neaktivnymi fiksirovannye frazy v kampanijah [s ruchnoj
    stavkoj](/openapi/promotion#tag/Sozdanie-kampanij/paths/~1adv~1v2~1seacat~1save-ad/post).
    Fiksirovannye frazy nuzhny, chtoby tovar otobrazhalsja v poiske tol'ko po opredelennym poiskovym
    zaprosam.<br><br>

    Ustanovit' ili udalit' fiksirovannye frazy mozhno cherez [otdel'nyj
    metod](/openapi/promotion#tag/Parametry-kampanij/paths/~1adv~1v1~1search~1set-plus/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 500 millisekund | 1 zapros | 500 millisekund | 5 zaprosov |
    </div>

    Args:
        id (int):  Example: 1234567.
        fixed (Union[Unset, bool]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, str]]
    """

    kwargs = _get_kwargs(
        id=id,
        fixed=fixed,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    id: int,
    fixed: Union[Unset, bool] = UNSET,
) -> Optional[Union[Any, str]]:
    r"""Upravlenie aktivnost'ju fiksirovannyh fraz

     Metod delaet aktivnymi ili neaktivnymi fiksirovannye frazy v kampanijah [s ruchnoj
    stavkoj](/openapi/promotion#tag/Sozdanie-kampanij/paths/~1adv~1v2~1seacat~1save-ad/post).
    Fiksirovannye frazy nuzhny, chtoby tovar otobrazhalsja v poiske tol'ko po opredelennym poiskovym
    zaprosam.<br><br>

    Ustanovit' ili udalit' fiksirovannye frazy mozhno cherez [otdel'nyj
    metod](/openapi/promotion#tag/Parametry-kampanij/paths/~1adv~1v1~1search~1set-plus/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 500 millisekund | 1 zapros | 500 millisekund | 5 zaprosov |
    </div>

    Args:
        id (int):  Example: 1234567.
        fixed (Union[Unset, bool]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, str]
    """

    return (
        await asyncio_detailed(
            client=client,
            id=id,
            fixed=fixed,
        )
    ).parsed
