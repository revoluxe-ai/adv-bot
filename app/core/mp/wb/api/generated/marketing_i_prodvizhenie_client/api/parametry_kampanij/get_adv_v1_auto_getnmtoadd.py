from http import HTTPStatus
from typing import Any, Dict, List, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
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
        "url": "/adv/v1/auto/getnmtoadd",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, List[int], ResponseAdvError1]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = cast(List[int], response.json())

        return response_200
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
) -> Response[Union[Any, List[int], ResponseAdvError1]]:
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
) -> Response[Union[Any, List[int], ResponseAdvError1]]:
    r"""Spisok kartochek tovarov dlja kampanii s edinoj stavkoj

     Metod formiruet [spisok kartochek tovarov](/openapi/promotion#tag/Sozdanie-
    kampanij/paths/~1adv~1v2~1supplier~1nms/post), kotorye mozhno dobavit' v kampaniju s edinoj
    stavkoj.<br><br>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 1 zapros | 1 sekunda | 5 zaprosov |
    </div>

    Args:
        id (int):  Example: 1.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, List[int], ResponseAdvError1]]
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
) -> Optional[Union[Any, List[int], ResponseAdvError1]]:
    r"""Spisok kartochek tovarov dlja kampanii s edinoj stavkoj

     Metod formiruet [spisok kartochek tovarov](/openapi/promotion#tag/Sozdanie-
    kampanij/paths/~1adv~1v2~1supplier~1nms/post), kotorye mozhno dobavit' v kampaniju s edinoj
    stavkoj.<br><br>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 1 zapros | 1 sekunda | 5 zaprosov |
    </div>

    Args:
        id (int):  Example: 1.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, List[int], ResponseAdvError1]
    """

    return sync_detailed(
        client=client,
        id=id,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    id: int,
) -> Response[Union[Any, List[int], ResponseAdvError1]]:
    r"""Spisok kartochek tovarov dlja kampanii s edinoj stavkoj

     Metod formiruet [spisok kartochek tovarov](/openapi/promotion#tag/Sozdanie-
    kampanij/paths/~1adv~1v2~1supplier~1nms/post), kotorye mozhno dobavit' v kampaniju s edinoj
    stavkoj.<br><br>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 1 zapros | 1 sekunda | 5 zaprosov |
    </div>

    Args:
        id (int):  Example: 1.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, List[int], ResponseAdvError1]]
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
) -> Optional[Union[Any, List[int], ResponseAdvError1]]:
    r"""Spisok kartochek tovarov dlja kampanii s edinoj stavkoj

     Metod formiruet [spisok kartochek tovarov](/openapi/promotion#tag/Sozdanie-
    kampanij/paths/~1adv~1v2~1supplier~1nms/post), kotorye mozhno dobavit' v kampaniju s edinoj
    stavkoj.<br><br>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 1 zapros | 1 sekunda | 5 zaprosov |
    </div>

    Args:
        id (int):  Example: 1.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, List[int], ResponseAdvError1]
    """

    return (
        await asyncio_detailed(
            client=client,
            id=id,
        )
    ).parsed
